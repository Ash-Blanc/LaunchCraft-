"""Persistence models (SQLite via SQLModel)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, Session, SQLModel, create_engine

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class Store(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    niche: str = ""
    audience: str = ""
    market: str = ""
    currency: str = "USD"
    brand: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Product(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("store_id", "slug"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    store_id: str = Field(foreign_key="store.id", index=True)
    slug: str
    name: str
    description: str
    price: str  # canonical decimal string, validated by schemas.ProductIn
    currency: str
    image_url: str = ""
    image_alt: str = ""
    available: bool = True
    inventory: int | None = None
    position: int = 0


class OrderStatus(str, Enum):
    """Lifecycle of a checkout. Only the backend moves an order between states."""

    PAYPAL_CREATED = "PAYPAL_CREATED"   # PayPal order exists, waiting for buyer approval
    CAPTURING = "CAPTURING"             # capture in flight (lock against duplicates)
    COMPLETED = "COMPLETED"             # capture verified: status + amount + currency
    FAILED = "FAILED"                   # capture declined or verification mismatch
    CANCELLED = "CANCELLED"             # buyer cancelled before approval


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PAYPAL_CREATED: {OrderStatus.CAPTURING, OrderStatus.CANCELLED, OrderStatus.FAILED},
    OrderStatus.CAPTURING: {OrderStatus.COMPLETED, OrderStatus.FAILED, OrderStatus.PAYPAL_CREATED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.FAILED: set(),
    OrderStatus.CANCELLED: set(),
}


class Order(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    store_id: str = Field(foreign_key="store.id", index=True)
    status: OrderStatus = OrderStatus.PAYPAL_CREATED
    currency: str
    total: str
    items: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    paypal_order_id: str | None = Field(default=None, unique=True, index=True)
    paypal_capture_id: str | None = None
    captured_amount: str | None = None
    failure_reason: str | None = None
    sandbox: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class LaunchReport(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    store_id: str = Field(foreign_key="store.id", index=True)
    ready: bool
    results: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utcnow)


class ProposalStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    STALE = "STALE"  # the store changed after the proposal was made, so it can't apply cleanly


class Proposal(SQLModel, table=True):
    """A change suggested by the assistant. Nothing is applied until the user accepts it."""
    id: str = Field(default_factory=new_id, primary_key=True)
    store_id: str | None = Field(default=None, foreign_key="store.id", index=True)
    kind: str  # generate_store | store_changes
    source: str  # "demo" | "live" — which assistant produced it
    summary: str
    rationale: str = ""
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None


class Activity(SQLModel, table=True):
    """Timeline entry. actor: you | assistant | system."""
    id: str = Field(default_factory=new_id, primary_key=True)
    store_id: str = Field(foreign_key="store.id", index=True)
    actor: str
    message: str
    detail: str = ""
    created_at: datetime = Field(default_factory=utcnow)


def log_activity(session: Session, store_id: str, actor: str, message: str,
                 detail: str = "") -> None:
    """Adds to the session; the caller's commit persists it with the change it describes."""
    session.add(Activity(store_id=store_id, actor=actor, message=message, detail=detail))


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        _engine = create_engine(url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(_engine)
    return _engine


def set_engine(engine) -> None:
    """Used by tests to point the app at an in-memory database."""
    global _engine
    _engine = engine
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(get_engine()) as session:
        yield session
