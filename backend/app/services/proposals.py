"""Applying accepted proposals. This is the only path from assistant output to stored data.

Every change is re-validated with the same schemas the editor uses, and update
proposals carry a `before` snapshot: if the product was edited after the
proposal was made, the proposal is marked STALE instead of overwriting the edit.
"""
from __future__ import annotations

from pydantic import ValidationError
from sqlmodel import Session, select

from app.models.db import (
    Product, Proposal, ProposalStatus, Store, log_activity, utcnow,
)
from app.schemas.agent import AddProduct, StoreChanges, UpdateBrand, UpdateProduct
from app.schemas.store import Brand, StoreConfigIn
from app.services.agent.demo import _product_in


class ProposalError(Exception):
    def __init__(self, message: str, http_status: int = 400):
        super().__init__(message)
        self.http_status = http_status


def actor_for(source: str) -> str:
    return "assistant (demo)" if source == "demo" else "assistant"


def _ensure_pending(proposal: Proposal) -> None:
    if proposal.status != ProposalStatus.PENDING:
        raise ProposalError(f"This suggestion was already {proposal.status.value.lower()}.", 409)


def create_store_from_config(session: Session, config: StoreConfigIn) -> Store:
    store = Store(name=config.name, niche=config.niche, audience=config.audience,
                  market=config.market, currency=config.currency, brand=config.brand.model_dump())
    session.add(store)
    session.flush()
    for i, p in enumerate(config.products):
        session.add(Product(store_id=store.id, position=i, **p.model_dump()))
    return store


def accept(session: Session, proposal: Proposal) -> Store:
    _ensure_pending(proposal)
    if proposal.kind == "generate_store":
        try:
            config = StoreConfigIn.model_validate(proposal.payload["config"])
        except (ValidationError, KeyError):
            raise ProposalError("The draft no longer passes validation.", 422) from None
        store = create_store_from_config(session, config)
        proposal.store_id = store.id
        log_activity(session, store.id, actor_for(proposal.source),
                     f"Drafted the store from your brief: {proposal.summary}")
        log_activity(session, store.id, "you", "Accepted the draft and created the store")
    else:
        store = session.get(Store, proposal.store_id)
        if store is None:
            raise ProposalError("Store not found.", 404)
        changes = StoreChanges.model_validate(proposal.payload).changes
        _apply_changes(session, store, changes, proposal)
        log_activity(session, store.id, "you", f"Accepted: {proposal.summary}",
                     detail=f"{len(changes)} change{'s' if len(changes) != 1 else ''} applied")
    proposal.status = ProposalStatus.ACCEPTED
    proposal.resolved_at = utcnow()
    session.add(proposal)
    session.commit()
    return store


def _apply_changes(session: Session, store: Store, changes, proposal: Proposal) -> None:
    position = len(session.exec(select(Product.id).where(Product.store_id == store.id)).all())
    existing_slugs = set(session.exec(select(Product.slug).where(Product.store_id == store.id)))
    for change in changes:
        if isinstance(change, AddProduct):
            p = change.product
            if p.currency != store.currency:
                raise ProposalError("Suggested product uses a different currency.", 422)
            if p.slug in existing_slugs:
                _mark_stale(session, proposal, f"A product with slug '{p.slug}' already exists.")
            session.add(Product(store_id=store.id, position=position, **p.model_dump()))
            existing_slugs.add(p.slug)
            position += 1
        elif isinstance(change, UpdateProduct):
            product = session.get(Product, change.product_id)
            if product is None or product.store_id != store.id:
                _mark_stale(session, proposal, "A product in this suggestion no longer exists.")
            if _product_in(product) != change.before:
                _mark_stale(session, proposal,
                            f"“{product.name}” was edited after this suggestion was made.")
            for k, v in change.after.model_dump().items():
                setattr(product, k, v)
        elif isinstance(change, UpdateBrand):
            if Brand.model_validate(store.brand) != change.before:
                _mark_stale(session, proposal, "The brand was edited after this suggestion was made.")
            store.brand = change.after.model_dump()
    store.updated_at = utcnow()


def _mark_stale(session: Session, proposal: Proposal, reason: str):
    session.rollback()
    proposal = session.merge(proposal)
    proposal.status = ProposalStatus.STALE
    proposal.resolved_at = utcnow()
    session.add(proposal)
    session.commit()
    raise ProposalError(f"{reason} Ask for a fresh suggestion.", 409)


def reject(session: Session, proposal: Proposal) -> None:
    _ensure_pending(proposal)
    proposal.status = ProposalStatus.REJECTED
    proposal.resolved_at = utcnow()
    session.add(proposal)
    if proposal.store_id:
        log_activity(session, proposal.store_id, "you", f"Rejected: {proposal.summary}")
    session.commit()


def proposal_out(p: Proposal) -> dict:
    return {"id": p.id, "store_id": p.store_id, "kind": p.kind, "source": p.source,
            "summary": p.summary, "rationale": p.rationale, "payload": p.payload,
            "status": p.status.value, "created_at": p.created_at.isoformat()}
