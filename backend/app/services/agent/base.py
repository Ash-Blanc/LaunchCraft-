"""The assistant interface. Phase 4 adds a live-model implementation of the same protocol.

Implementations only *propose*. They never write to the database; accepted
proposals are applied by app.services.proposals with full validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.models.db import Product, Store
from app.schemas.agent import AgentAction, BusinessBrief, GeneratedDraft, SuggestedChanges

AgentMode = Literal["demo", "live"]


@dataclass(frozen=True)
class MessageIntent:
    """What the assistant decided to do with a free-text message."""
    reply: str
    action: AgentAction | None


class StoreAgent(Protocol):
    @property
    def mode(self) -> AgentMode:
        """Which assistant produced the LAST response — "live" downgrades to "demo"
        for a call that fell back to the deterministic rules."""
        ...

    def generate_store(self, brief: BusinessBrief) -> GeneratedDraft: ...

    def suggest(self, action: AgentAction, store: Store,
                products: list[Product]) -> SuggestedChanges | None: ...

    def interpret_message(self, text: str, store: Store,
                          products: list[Product]) -> MessageIntent: ...
