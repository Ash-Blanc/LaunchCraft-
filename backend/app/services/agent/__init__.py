from app.core.config import Settings
from app.services.agent.base import StoreAgent
from app.services.agent.demo import DemoAgent


def get_agent(settings: Settings) -> StoreAgent:
    # Phase 4 returns a live-model agent when settings.ai_configured is true.
    # Until then every response is from the deterministic demo agent and is labelled as such.
    return DemoAgent()
