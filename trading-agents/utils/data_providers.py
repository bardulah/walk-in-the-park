"""
Data Provider Integrations
Integrates with SEC filings, market data, and other sources
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from config.logging_config import get_logger


logger = get_logger("data_providers")


# Optional dependencies with graceful degradation
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    logger.warning("yfinance not available - install with: pip install yfinance")
    YFINANCE_AVAILABLE = False

try:
    from sec_api import QueryApi
    SEC_API_AVAILABLE = True
except ImportError:
    logger.warning("sec-api not available - install with: pip install sec-api")
    SEC_API_AVAILABLE = False


class YFinanceProvider:
    """
    Market data provider using yfinance

    Provides real-time stock data for guardrails validation

    Usage:
        provider = YFinanceProvider()
        price = provider.get_price('AAPL')
        info = provider.get_info('AAPL')
    """

    def __init__(self):
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance not installed. Install with: pip install yfinance")

        self.logger = logger
        self.logger.info("YFinanceProvider initialized")

    def get_price(self, ticker: str) -> Optional[float]:
        """Get current price"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
        except Exception as e:
            self.logger.error(f"Failed to get price for {ticker}: {e}")
            return None

    def get_market_cap(self, ticker: str) -> Optional[float]:
        """Get market capitalization"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get('marketCap')
        except Exception as e:
            self.logger.error(f"Failed to get market cap for {ticker}: {e}")
            return None

    def get_volume(self, ticker: str) -> Optional[float]:
        """Get trading volume"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get('volume') or stock.info.get('regularMarketVolume')
        except Exception as e:
            self.logger.error(f"Failed to get volume for {ticker}: {e}")
            return None

    def get_pe_ratio(self, ticker: str) -> Optional[float]:
        """Get P/E ratio"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get('trailingPE') or stock.info.get('forwardPE')
        except Exception as e:
            self.logger.error(f"Failed to get P/E ratio for {ticker}: {e}")
            return None

    def get_info(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive stock info"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info
        except Exception as e:
            self.logger.error(f"Failed to get info for {ticker}: {e}")
            return {}

    def get_historical_data(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> Any:
        """Get historical price data"""
        try:
            stock = yf.Ticker(ticker)
            return stock.history(period=period, interval=interval)
        except Exception as e:
            self.logger.error(f"Failed to get historical data for {ticker}: {e}")
            return None


class SECFilingsProvider:
    """
    SEC filings provider using sec-api

    Provides 10-K, 10-Q, and earnings transcripts for RAG

    Usage:
        provider = SECFilingsProvider(api_key='your_key')
        filing = provider.get_latest_10k('AAPL')
        rag.index_document(ticker='AAPL', content=filing, doc_type='10-K')
    """

    def __init__(self, api_key: str):
        """
        Initialize SEC filings provider

        Args:
            api_key: SEC API key from sec-api.io
        """
        if not SEC_API_AVAILABLE:
            raise ImportError(
                "sec-api not installed. Install with: pip install sec-api"
            )

        self.query_api = QueryApi(api_key=api_key)
        self.logger = logger
        self.logger.info("SECFilingsProvider initialized")

    def get_latest_10k(self, ticker: str) -> Optional[str]:
        """Get latest 10-K filing"""
        try:
            query = {
                "query": f"ticker:{ticker} AND formType:\"10-K\"",
                "from": "0",
                "size": "1",
                "sort": [{"filedAt": {"order": "desc"}}]
            }

            filings = self.query_api.get_filings(query)

            if filings['filings']:
                filing_url = filings['filings'][0]['linkToFilingDetails']
                # In production, fetch and parse the full filing
                self.logger.info(f"Found 10-K for {ticker}: {filing_url}")
                return filing_url
            else:
                self.logger.warning(f"No 10-K found for {ticker}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to get 10-K for {ticker}: {e}")
            return None

    def get_latest_10q(self, ticker: str) -> Optional[str]:
        """Get latest 10-Q filing"""
        try:
            query = {
                "query": f"ticker:{ticker} AND formType:\"10-Q\"",
                "from": "0",
                "size": "1",
                "sort": [{"filedAt": {"order": "desc"}}]
            }

            filings = self.query_api.get_filings(query)

            if filings['filings']:
                filing_url = filings['filings'][0]['linkToFilingDetails']
                self.logger.info(f"Found 10-Q for {ticker}: {filing_url}")
                return filing_url
            else:
                self.logger.warning(f"No 10-Q found for {ticker}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to get 10-Q for {ticker}: {e}")
            return None

    def search_filings(
        self,
        ticker: str,
        form_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search filings by type"""
        try:
            query = {
                "query": f"ticker:{ticker} AND formType:\"{form_type}\"",
                "from": "0",
                "size": str(limit),
                "sort": [{"filedAt": {"order": "desc"}}]
            }

            filings = self.query_api.get_filings(query)
            return filings.get('filings', [])

        except Exception as e:
            self.logger.error(f"Failed to search filings for {ticker}: {e}")
            return []


class MockDataProvider:
    """
    Mock data provider for testing

    Provides fake data when real APIs not available
    """

    def __init__(self):
        self.logger = logger
        self.logger.info("MockDataProvider initialized (using fake data)")

    def get_price(self, ticker: str) -> float:
        """Return mock price"""
        # Simple hash-based fake price
        return 100.0 + (hash(ticker) % 100)

    def get_market_cap(self, ticker: str) -> float:
        """Return mock market cap"""
        return 1_000_000_000_000.0  # $1T

    def get_volume(self, ticker: str) -> float:
        """Return mock volume"""
        return 50_000_000

    def get_pe_ratio(self, ticker: str) -> float:
        """Return mock P/E ratio"""
        return 25.0

    def get_info(self, ticker: str) -> Dict[str, Any]:
        """Return mock info"""
        return {
            'ticker': ticker,
            'currentPrice': self.get_price(ticker),
            'marketCap': self.get_market_cap(ticker),
            'volume': self.get_volume(ticker),
            'trailingPE': self.get_pe_ratio(ticker)
        }


def get_data_provider(provider_type: str = 'yfinance', **kwargs):
    """
    Factory function to get data provider

    Args:
        provider_type: 'yfinance', 'mock', or 'sec'
        **kwargs: Provider-specific arguments

    Returns:
        Data provider instance
    """
    if provider_type == 'yfinance':
        if YFINANCE_AVAILABLE:
            return YFinanceProvider()
        else:
            logger.warning("yfinance not available - using mock provider")
            return MockDataProvider()

    elif provider_type == 'sec':
        if SEC_API_AVAILABLE:
            api_key = kwargs.get('api_key')
            if not api_key:
                raise ValueError("SEC API requires api_key")
            return SECFilingsProvider(api_key=api_key)
        else:
            raise ImportError("sec-api not available")

    elif provider_type == 'mock':
        return MockDataProvider()

    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
