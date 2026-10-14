from app.core.config import Settings
from app.services.agent.base import StoreAgent
from app.services.agent.demo import DemoAgent
from app.services.agent.live import LiveAgent


def get_agent(settings: Settings) -> StoreAgent:
    # Phase 4: a configured AI_API_KEY selects the live-model agent. Every live call
    # still degrades to the deterministic demo rules on provider failure, labelled as such.
    if settings.ai_configured:
        return LiveAgent(settings)
    return DemoAgent()
