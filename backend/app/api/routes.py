"""HTTP routes. Thin: validate input, call a service, shape output."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.models.db import (
    Activity, Order, Product, Proposal, ProposalStatus, Store, get_session, log_activity, utcnow,
)
from app.schemas.agent import BusinessBrief, MessageIn, StorePatch, SuggestIn
from app.schemas.store import ProductIn, StoreConfigIn
from app.services.agent import StoreAgent, get_agent
from app.services.cart import CartError, CartLineRequest
from app.services.checkout import CheckoutError, cancel_checkout, capture_checkout, create_checkout
from app.services.launch_checks import run_launch_checks
from app.services.paypal import PayPalClient
from app.services.proposals import (
    ProposalError, accept, actor_for, create_store_from_config, proposal_out, reject,
)
from app.services.render_check import RenderChecker, make_http_render_checker

router = APIRouter(prefix="/api")

_paypal: PayPalClient | None = None


def get_paypal(settings: Annotated[Settings, Depends(get_settings)]) -> PayPalClient:
    global _paypal
    if _paypal is None:
        _paypal = PayPalClient(settings)
    return _paypal


def get_store_agent(settings: Annotated[Settings, Depends(get_settings)]) -> StoreAgent:
    return get_agent(settings)


def get_render_checker(settings: Annotated[Settings, Depends(get_settings)]) -> RenderChecker:
    return make_http_render_checker(settings)


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
PayPalDep = Annotated[PayPalClient, Depends(get_paypal)]
AgentDep = Annotated[StoreAgent, Depends(get_store_agent)]
RenderDep = Annotated[RenderChecker, Depends(get_render_checker)]


# --- serializers -----------------------------------------------------------------
def product_out(p: Product) -> dict:
    return {"id": p.id, "slug": p.slug, "name": p.name, "description": p.description,
            "price": p.price, "currency": p.currency, "image_url": p.image_url,
            "image_alt": p.image_alt, "available": p.available, "inventory": p.inventory}


def _products(session: Session, store_id: str) -> list[Product]:
    return list(session.exec(
        select(Product).where(Product.store_id == store_id).order_by(Product.position)))


def store_out(session: Session, s: Store) -> dict:
    return {"id": s.id, "name": s.name, "niche": s.niche, "audience": s.audience,
            "market": s.market, "currency": s.currency, "brand": s.brand,
            "updated_at": s.updated_at.isoformat(),
            "products": [product_out(p) for p in _products(session, s.id)]}


def order_out(o: Order) -> dict:
    return {"id": o.id, "status": o.status.value, "currency": o.currency, "total": o.total,
            "items": o.items, "paypal_order_id": o.paypal_order_id,
            "paypal_capture_id": o.paypal_capture_id, "captured_amount": o.captured_amount,
            "failure_reason": o.failure_reason, "sandbox": o.sandbox}


def report_out(report) -> dict:
    return {"id": report.id, "ready": report.ready, "results": report.results,
            "created_at": report.created_at.isoformat()}


def _store_or_404(session: Session, store_id: str) -> Store:
    store = session.get(Store, store_id)
    if store is None:
        raise HTTPException(404, "Store not found.")
    return store


# --- meta --------------------------------------------------------------------------
@router.get("/health")
def health(settings: SettingsDep, agent: AgentDep) -> dict:
    return {"ok": True, "paypal_env": "sandbox",
            "paypal_configured": settings.paypal_configured,
            # Reports what actually answers requests, not whether a key happens to be set.
            "ai_mode": agent.mode,
            "ai_key_present": settings.ai_configured}


@router.get("/config/public")
def public_config(settings: SettingsDep) -> dict:
    # The client ID is public by design (it's loaded by the PayPal JS SDK). The secret never leaves.
    return {"paypal_client_id": settings.paypal_client_id or None, "paypal_env": "sandbox"}


# --- stores & products -----------------------------------------------------------
@router.get("/stores")
def list_stores(session: SessionDep) -> list[dict]:
    stores = session.exec(select(Store).order_by(Store.updated_at.desc()).limit(10)).all()
    return [{"id": s.id, "name": s.name, "niche": s.niche,
             "updated_at": s.updated_at.isoformat()} for s in stores]


@router.post("/stores", status_code=201)
def create_store(body: StoreConfigIn, session: SessionDep) -> dict:
    store = create_store_from_config(session, body)
    log_activity(session, store.id, "you", "Created the store")
    session.commit()
    return store_out(session, store)


@router.get("/stores/{store_id}")
def get_store(store_id: str, session: SessionDep) -> dict:
    return store_out(session, _store_or_404(session, store_id))


@router.patch("/stores/{store_id}")
def patch_store(store_id: str, body: StorePatch, session: SessionDep) -> dict:
    store = _store_or_404(session, store_id)
    changed = []
    for field in ("name", "niche", "audience"):
        value = getattr(body, field)
        if value is not None and value != getattr(store, field):
            setattr(store, field, value)
            changed.append(field)
    if body.brand is not None and body.brand.model_dump() != store.brand:
        store.brand = body.brand.model_dump()
        changed.append("brand")
    if changed:
        store.updated_at = utcnow()
        log_activity(session, store.id, "you", "Updated the store details",
                     detail=", ".join(changed))
        session.commit()
    return store_out(session, store)


@router.post("/stores/{store_id}/products", status_code=201)
def add_product(store_id: str, body: ProductIn, session: SessionDep) -> dict:
    store = _store_or_404(session, store_id)
    if body.currency != store.currency:
        raise HTTPException(422, f"Product currency must be {store.currency}.")
    count = len(session.exec(select(Product.id).where(Product.store_id == store_id)).all())
    product = Product(store_id=store_id, position=count, **body.model_dump())
    session.add(product)
    store.updated_at = utcnow()
    log_activity(session, store_id, "you", f"Added “{body.name}”")
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, f"A product with the URL name '{body.slug}' already exists.") from None
    return product_out(product)


@router.put("/stores/{store_id}/products/{product_id}")
def update_product(store_id: str, product_id: str, body: ProductIn, session: SessionDep) -> dict:
    store = _store_or_404(session, store_id)
    product = session.get(Product, product_id)
    if product is None or product.store_id != store_id:
        raise HTTPException(404, "Product not found.")
    if body.currency != store.currency:
        raise HTTPException(422, f"Product currency must be {store.currency}.")
    changed = [k for k, v in body.model_dump().items() if getattr(product, k) != v]
    for k, v in body.model_dump().items():
        setattr(product, k, v)
    if changed:
        store.updated_at = utcnow()
        log_activity(session, store_id, "you", f"Edited “{body.name}”", detail=", ".join(changed))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, f"A product with the URL name '{body.slug}' already exists.") from None
    return product_out(product)


@router.delete("/stores/{store_id}/products/{product_id}", status_code=204)
def delete_product(store_id: str, product_id: str, session: SessionDep) -> None:
    product = session.get(Product, product_id)
    if product is None or product.store_id != store_id:
        raise HTTPException(404, "Product not found.")
    log_activity(session, store_id, "you", f"Removed “{product.name}”")
    session.delete(product)
    session.commit()


@router.get("/stores/{store_id}/activity")
def activity(store_id: str, session: SessionDep) -> list[dict]:
    _store_or_404(session, store_id)
    rows = session.exec(select(Activity).where(Activity.store_id == store_id)
                        .order_by(Activity.created_at.desc()).limit(50)).all()
    return [{"id": a.id, "actor": a.actor, "message": a.message, "detail": a.detail,
             "created_at": a.created_at.isoformat()} for a in rows]


# --- assistant & proposals ------------------------------------------------------------
@router.post("/agent/draft-store", status_code=201)
def draft_store(body: BusinessBrief, session: SessionDep, agent: AgentDep) -> dict:
    draft = agent.generate_store(body)
    proposal = Proposal(kind="generate_store", source=agent.mode, summary=draft.summary,
                        rationale="", payload={"config": draft.config.model_dump(mode="json"),
                                               "notes": [n.model_dump() for n in draft.notes],
                                               "brief": body.model_dump()})
    session.add(proposal)
    session.commit()
    return proposal_out(proposal)


@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str, session: SessionDep) -> dict:
    p = session.get(Proposal, proposal_id)
    if p is None:
        raise HTTPException(404, "Suggestion not found.")
    return proposal_out(p)


@router.get("/stores/{store_id}/proposals")
def pending_proposals(store_id: str, session: SessionDep) -> list[dict]:
    _store_or_404(session, store_id)
    rows = session.exec(select(Proposal).where(Proposal.store_id == store_id,
                                               Proposal.status == ProposalStatus.PENDING)
                        .order_by(Proposal.created_at.desc())).all()
    return [proposal_out(p) for p in rows]


@router.post("/proposals/{proposal_id}/accept")
def accept_proposal(proposal_id: str, session: SessionDep) -> dict:
    p = session.get(Proposal, proposal_id)
    if p is None:
        raise HTTPException(404, "Suggestion not found.")
    try:
        store = accept(session, p)
    except ProposalError as e:
        raise HTTPException(e.http_status, str(e)) from None
    return {"proposal": proposal_out(p), "store": store_out(session, store)}


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: str, session: SessionDep) -> dict:
    p = session.get(Proposal, proposal_id)
    if p is None:
        raise HTTPException(404, "Suggestion not found.")
    try:
        reject(session, p)
    except ProposalError as e:
        raise HTTPException(e.http_status, str(e)) from None
    return proposal_out(p)


def _run_action(action: str, store: Store, session: Session, agent: StoreAgent,
                settings: Settings, render: RenderChecker) -> dict:
    """Execute one of the assistant's approved tools. Returns what the panel should show."""
    if action == "run_launch_checks":
        report = run_launch_checks(session, settings, store.id, render_checker=render,
                                   actor=actor_for(agent.mode))
        return {"proposal": None, "report": report_out(report)}
    suggestion = agent.suggest(action, store, _products(session, store.id))  # type: ignore[arg-type]
    if suggestion is None:
        return {"proposal": None, "report": None,
                "note": "Nothing to suggest: every product already has these details."
                if action == "fill_missing_details"
                else "The sample range has no more products that aren't already in your store."}
    proposal = Proposal(store_id=store.id, kind="store_changes", source=agent.mode,
                        summary=suggestion.summary, rationale=suggestion.rationale,
                        payload={"changes": [c.model_dump(mode="json")
                                             for c in suggestion.changes]})
    session.add(proposal)
    log_activity(session, store.id, actor_for(agent.mode), f"Suggested: {suggestion.summary}",
                 detail="Waiting for your review")
    session.commit()
    return {"proposal": proposal_out(proposal), "report": None}


@router.post("/stores/{store_id}/agent/suggest")
def suggest(store_id: str, body: SuggestIn, session: SessionDep, agent: AgentDep,
            settings: SettingsDep, render: RenderDep) -> dict:
    store = _store_or_404(session, store_id)
    return {"mode": agent.mode, **_run_action(body.action, store, session, agent, settings, render)}


@router.post("/stores/{store_id}/agent/message")
def message(store_id: str, body: MessageIn, session: SessionDep, agent: AgentDep,
            settings: SettingsDep, render: RenderDep) -> dict:
    store = _store_or_404(session, store_id)
    intent = agent.interpret_message(body.text, store, _products(session, store_id))
    result = {"proposal": None, "report": None}
    if intent.action:
        result = _run_action(intent.action, store, session, agent, settings, render)
    return {"mode": agent.mode, "reply": intent.reply, "action": intent.action, **result}


# --- checkout ----------------------------------------------------------------------
class CartLineBody(BaseModel):
    product_id: Annotated[str, Field(min_length=1, max_length=64)]
    quantity: Annotated[int, Field(ge=1, le=99, strict=True)]


class CheckoutBody(BaseModel):
    # Note: no price or total fields. The server computes them.
    items: Annotated[list[CartLineBody], Field(min_length=1, max_length=50)]


@router.post("/stores/{store_id}/checkout", status_code=201)
def start_checkout(store_id: str, body: CheckoutBody, session: SessionDep,
                   paypal: PayPalDep) -> dict:
    try:
        order = create_checkout(session, paypal, store_id,
                                [CartLineRequest(i.product_id, i.quantity) for i in body.items])
    except CartError as e:
        raise HTTPException(422, str(e)) from None
    except CheckoutError as e:
        raise HTTPException(e.http_status, str(e)) from None
    return order_out(order)


@router.post("/checkout/{paypal_order_id}/capture")
def capture(paypal_order_id: str, session: SessionDep, paypal: PayPalDep) -> dict:
    try:
        return order_out(capture_checkout(session, paypal, paypal_order_id))
    except CheckoutError as e:
        raise HTTPException(e.http_status, str(e)) from None


@router.post("/checkout/{paypal_order_id}/cancel")
def cancel(paypal_order_id: str, session: SessionDep) -> dict:
    try:
        return order_out(cancel_checkout(session, paypal_order_id))
    except CheckoutError as e:
        raise HTTPException(e.http_status, str(e)) from None


# --- launch readiness ---------------------------------------------------------------
@router.post("/stores/{store_id}/launch-checks")
def launch_checks(store_id: str, session: SessionDep, settings: SettingsDep,
                  render: RenderDep) -> dict:
    _store_or_404(session, store_id)
    return report_out(run_launch_checks(session, settings, store_id, render_checker=render))
