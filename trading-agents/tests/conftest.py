"""
Pytest configuration and fixtures for trading agents tests
"""
import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any


@pytest.fixture
def mock_llm_router():
    """Create a mock LLM router for testing"""
    router = Mock()
    router.call = Mock(return_value='{"test": "response"}')
    router.get_total_cost = Mock(return_value=0.05)
    router.reset_cost = Mock()
    router.model = "test-model"
    return router


@pytest.fixture
def sample_portfolio_data() -> Dict[str, Any]:
    """Sample portfolio data for testing"""
    return {
        "positions": [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "avg_cost": 150.00,
                "current_price": 180.00,
                "market_value": 1800.00,
                "unrealized_pnl": 300.00,
                "unrealized_pnl_pct": 20.00,
            },
            {
                "ticker": "MSFT",
                "quantity": 5,
                "avg_cost": 300.00,
                "current_price": 350.00,
                "market_value": 1750.00,
                "unrealized_pnl": 250.00,
                "unrealized_pnl_pct": 16.67,
            },
        ],
        "total_value": 3550.00,
        "cash_balance": 450.00,
        "account_value": 4000.00,
        "timestamp": "2025-01-15T10:00:00Z",
    }


@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Sample market data for testing"""
    return {
        "indices": {
            "SP500": 4500.00,
            "NASDAQ": 14000.00,
            "DOW": 35000.00,
        },
        "vix_level": 18.5,
        "sentiment_signal": "BULLISH",
        "timestamp": "2025-01-15T10:00:00Z",
    }


@pytest.fixture
def sample_news_data() -> Dict[str, Any]:
    """Sample news data for testing"""
    return {
        "AAPL": [
            {
                "title": "Apple Reports Record Earnings",
                "summary": "Apple Inc. reported better than expected quarterly earnings.",
                "sentiment": "POSITIVE",
                "date": "2025-01-14",
            }
        ],
        "MSFT": [
            {
                "title": "Microsoft Cloud Growth Continues",
                "summary": "Microsoft Azure shows strong growth in cloud services.",
                "sentiment": "POSITIVE",
                "date": "2025-01-14",
            }
        ],
    }


@pytest.fixture
def valid_json_response() -> str:
    """Valid JSON response from LLM"""
    return """{
        "portfolio_health_score": 75,
        "concentration_risk": "MODERATE",
        "sector_distribution": {
            "Technology": 88.73,
            "Other": 11.27
        }
    }"""


@pytest.fixture
def malformed_json_response() -> str:
    """Malformed JSON response (common LLM issue)"""
    return """Here's the analysis:
    ```json
    {
        "portfolio_health_score": 75,
        "concentration_risk": "MODERATE",
    }
    ```
    """


@pytest.fixture
def markdown_wrapped_json() -> str:
    """JSON wrapped in markdown code block"""
    return """```json
    {
        "result": "success",
        "data": {"value": 42}
    }
    ```"""
