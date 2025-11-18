"""Trading 212 API exceptions"""


class Trading212Error(Exception):
    """Base exception for Trading 212 API errors"""
    pass


class AuthenticationError(Trading212Error):
    """Authentication failed"""
    pass


class RateLimitError(Trading212Error):
    """Rate limit exceeded"""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class DuplicateOrderError(Trading212Error):
    """Duplicate order detected"""
    pass


class InvalidOrderError(Trading212Error):
    """Invalid order parameters"""
    pass


class InsufficientFundsError(Trading212Error):
    """Insufficient funds for order"""
    pass


class MarketClosedError(Trading212Error):
    """Market is closed"""
    pass
