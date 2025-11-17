"""
Configuration settings for trading agents system.
Reads from environment variables - never stores secrets in code.
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class APIConfig:
    """API credentials and endpoints"""
    # Trading
    trading_212_api_key: str

    # AI/LLM
    gemini_api_key: str
    openrouter_api_key: str

    # Data sources
    exa_api_key: str
    firecrawl_api_key: str
    news_api_key: str
    perplexity_api_key: str

    # Databases
    neon_api_key: str
    pinecone_api_key: str

    # Notifications
    telegram_bot_token: str

    # Optional fields (must come last)
    anthropic_api_key: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    composio_api_key: Optional[str] = None

@dataclass
class AgentConfig:
    """Agent behavior configuration"""
    # Model selections
    portfolio_model: str = "gpt-4o-mini"  # Via OpenRouter
    market_model: str = "gemini-2.5-flash"  # Via Gemini (free with credits)
    orchestrator_model: str = "claude-3-5-sonnet"  # Via OpenRouter

    # Timeouts
    agent_timeout_seconds: int = 30
    max_retries: int = 3

    # Cost limits
    daily_budget_usd: float = 0.50
    monthly_budget_usd: float = 30.00

def load_config() -> tuple[APIConfig, AgentConfig]:
    """Load configuration from environment variables"""

    api_config = APIConfig(
        trading_212_api_key=os.getenv('212_TRADING_API_KEY', ''),
        gemini_api_key=os.getenv('GEMINI_API_KEY', ''),
        openrouter_api_key=os.getenv('OPENROUTER_API_KEY', ''),
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
        exa_api_key=os.getenv('EXA_SEARCH_API_KEY', ''),
        firecrawl_api_key=os.getenv('FIRECRAWL_API_KEY', ''),
        news_api_key=os.getenv('NEWS_API_KEY', ''),
        perplexity_api_key=os.getenv('PERPLEXITY_API_KEY', ''),
        neon_api_key=os.getenv('NEON_API_KEY', ''),
        pinecone_api_key=os.getenv('PINECONE_API_KEY', ''),
        telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
        telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID'),
        composio_api_key=os.getenv('COMPOSIO_API_KEY')
    )

    agent_config = AgentConfig()

    # Validate critical keys
    if not api_config.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    if not api_config.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment")

    return api_config, agent_config

# Load on import (but don't fail if running tests)
try:
    API_CONFIG, AGENT_CONFIG = load_config()
except ValueError as e:
    print(f"⚠️  Warning: {e}")
    API_CONFIG, AGENT_CONFIG = None, None
