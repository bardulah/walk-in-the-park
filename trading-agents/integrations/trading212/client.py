"""
Trading 212 API Client
Wrapper for Trading 212 REST API with rate limiting and error handling
"""
import base64
import hashlib
import json
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from config.logging_config import get_logger
from utils.rate_limiter import RateLimitConfig, LLMRateLimiter
from .models import (
    OrderRequest, Order, Position, Account,
    OrderType, OrderAction, OrderStatus
)
from .exceptions import (
    Trading212Error, AuthenticationError, RateLimitError,
    DuplicateOrderError, InvalidOrderError, InsufficientFundsError,
    MarketClosedError
)


logger = get_logger("trading212")


# Trading 212 rate limit configuration
# Conservative limits based on documentation
TRADING212_RATE_LIMITS = RateLimitConfig(
    max_requests_per_minute=30,  # Conservative limit
    max_requests_per_hour=1000,
    burst_size=10
)


class RequestCache:
    """Cache to prevent duplicate requests"""

    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize request cache

        Args:
            ttl_seconds: Time-to-live for cache entries
        """
        self.cache = {}
        self.ttl = ttl_seconds
        self.logger = logger

    def get_request_id(self, ticker: str, quantity: float, order_type: str) -> str:
        """Generate unique request ID"""
        # Create hash of order parameters
        key = f"{ticker}:{quantity}:{order_type}:{int(time.time() / 10)}"  # 10-second windows
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def exists(self, request_id: str) -> bool:
        """Check if request was recently made"""
        self._cleanup_expired()

        if request_id in self.cache:
            self.logger.warning(f"Duplicate request detected: {request_id}")
            return True

        return False

    def add(self, request_id: str):
        """Add request to cache"""
        self.cache[request_id] = time.time()

    def _cleanup_expired(self):
        """Remove expired entries"""
        now = time.time()
        expired = [
            req_id for req_id, timestamp in self.cache.items()
            if now - timestamp > self.ttl
        ]

        for req_id in expired:
            del self.cache[req_id]


class Trading212Client:
    """
    Trading 212 API client

    Features:
    - Rate limiting to prevent throttling
    - Request deduplication to prevent duplicate orders
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Support for both demo and live environments

    Usage:
        client = Trading212Client(api_key, api_secret, environment='demo')

        # Place market order
        order = client.place_market_order('AAPL', 10, 'buy')

        # Get account info
        account = client.get_account()

        # Get positions
        positions = client.get_positions()
    """

    BASE_URLS = {
        'demo': 'https://demo.trading212.com/api/v0',
        'live': 'https://live.trading212.com/api/v0'
    }

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        environment: str = 'demo',
        enable_rate_limiting: bool = True,
        enable_deduplication: bool = True,
        max_retries: int = 3
    ):
        """
        Initialize Trading 212 client

        Args:
            api_key: API key from Trading 212 app
            api_secret: API secret from Trading 212 app
            environment: 'demo' or 'live'
            enable_rate_limiting: Enable rate limiting (recommended)
            enable_deduplication: Enable duplicate request detection (recommended)
            max_retries: Maximum retry attempts for failed requests
        """
        if environment not in self.BASE_URLS:
            raise ValueError(f"Invalid environment '{environment}'. Must be 'demo' or 'live'")

        self.api_key = api_key
        self.api_secret = api_secret
        self.environment = environment
        self.base_url = self.BASE_URLS[environment]
        self.max_retries = max_retries

        # Setup authentication header
        credentials = f"{api_key}:{api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded}"

        # Setup rate limiting
        self.enable_rate_limiting = enable_rate_limiting
        if enable_rate_limiting:
            self.rate_limiter = LLMRateLimiter(TRADING212_RATE_LIMITS)
            logger.info("Rate limiting enabled for Trading 212 API")
        else:
            self.rate_limiter = None
            logger.warning("Rate limiting disabled - risk of API throttling")

        # Setup request deduplication
        self.enable_deduplication = enable_deduplication
        if enable_deduplication:
            self.request_cache = RequestCache(ttl_seconds=60)
            logger.info("Request deduplication enabled")
        else:
            self.request_cache = None
            logger.warning("Request deduplication disabled - risk of duplicate orders")

        self.logger = logger
        self.logger.info(f"Trading212Client initialized | Environment: {environment}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Trading 212 API

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint (e.g., '/equity/orders')
            data: Request body data
            params: Query parameters

        Returns:
            API response as dict

        Raises:
            Trading212Error: For API errors
        """
        url = f"{self.base_url}{endpoint}"

        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json'
        }

        # Apply rate limiting
        if self.enable_rate_limiting and self.rate_limiter:
            if not self.rate_limiter.acquire(blocking=True, timeout=30):
                raise RateLimitError("Rate limit exceeded for Trading 212 API")

        # Execute with retry logic
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers, params=params)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, json=data)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Handle response
                return self._handle_response(response)

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                last_exception = e
                self.logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s
                    wait_time = 2 ** attempt
                    self.logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Max retries exceeded")
                    raise Trading212Error(f"Request failed after {self.max_retries} attempts: {e}")

        # Should not reach here, but just in case
        raise Trading212Error(f"Request failed: {last_exception}")

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response"""
        # Check rate limit headers
        if 'x-ratelimit-remaining' in response.headers:
            remaining = int(response.headers['x-ratelimit-remaining'])
            if remaining < 5:
                self.logger.warning(f"Rate limit nearly exceeded: {remaining} requests remaining")

        # Handle success
        if response.status_code == 200 or response.status_code == 201:
            try:
                return response.json()
            except json.JSONDecodeError:
                return {}

        # Handle errors
        if response.status_code == 401:
            raise AuthenticationError("Invalid API credentials")

        if response.status_code == 429:
            retry_after = response.headers.get('x-ratelimit-reset', 60)
            raise RateLimitError(
                "Rate limit exceeded",
                retry_after=int(retry_after)
            )

        if response.status_code == 400:
            error_msg = response.json().get('message', 'Invalid request')
            raise InvalidOrderError(error_msg)

        if response.status_code == 403:
            error_msg = response.json().get('message', 'Forbidden')
            if 'insufficient' in error_msg.lower():
                raise InsufficientFundsError(error_msg)
            raise Trading212Error(error_msg)

        # Generic error
        try:
            error_msg = response.json().get('message', f'HTTP {response.status_code}')
        except json.JSONDecodeError:
            error_msg = f'HTTP {response.status_code}'

        raise Trading212Error(f"API error: {error_msg}")

    def place_market_order(
        self,
        ticker: str,
        quantity: float,
        action: str
    ) -> Order:
        """
        Place market order

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            quantity: Number of shares
            action: 'buy' or 'sell'

        Returns:
            Order object

        Raises:
            DuplicateOrderError: If duplicate order detected
            InvalidOrderError: If order parameters invalid
            InsufficientFundsError: If insufficient funds
        """
        # Validate action
        try:
            order_action = OrderAction(action.lower())
        except ValueError:
            raise InvalidOrderError(f"Invalid action '{action}'. Must be 'buy' or 'sell'")

        # Check for duplicate
        if self.enable_deduplication and self.request_cache:
            request_id = self.request_cache.get_request_id(
                ticker, quantity, 'market'
            )

            if self.request_cache.exists(request_id):
                raise DuplicateOrderError(
                    f"Duplicate market order for {ticker} (quantity: {quantity})"
                )

            self.request_cache.add(request_id)

        # Create order request
        order_request = OrderRequest(
            ticker=ticker,
            action=order_action,
            quantity=quantity,
            order_type=OrderType.MARKET
        )

        self.logger.info(
            f"Placing market order: {action.upper()} {quantity} {ticker}"
        )

        # Execute order
        try:
            response = self._make_request(
                method='POST',
                endpoint='/equity/orders/market',
                data=order_request.to_api_params()
            )

            order = Order.from_api_response(response)
            self.logger.info(f"Order placed successfully: {order.order_id}")

            return order

        except Exception as e:
            self.logger.error(f"Order failed: {e}")
            raise

    def place_limit_order(
        self,
        ticker: str,
        quantity: float,
        action: str,
        limit_price: float
    ) -> Order:
        """
        Place limit order

        Note: Live environment currently only supports market orders.
        Limit orders work in demo environment.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            action: 'buy' or 'sell'
            limit_price: Limit price

        Returns:
            Order object
        """
        if self.environment == 'live':
            self.logger.warning(
                "Limit orders not supported in live environment during beta. "
                "Use market orders instead."
            )
            raise InvalidOrderError(
                "Live environment only supports market orders during beta"
            )

        order_action = OrderAction(action.lower())

        order_request = OrderRequest(
            ticker=ticker,
            action=order_action,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=limit_price
        )

        self.logger.info(
            f"Placing limit order: {action.upper()} {quantity} {ticker} @ ${limit_price}"
        )

        response = self._make_request(
            method='POST',
            endpoint='/equity/orders/limit',
            data=order_request.to_api_params()
        )

        return Order.from_api_response(response)

    def get_account(self) -> Account:
        """Get account information"""
        self.logger.debug("Fetching account information")

        response = self._make_request(
            method='GET',
            endpoint='/equity/account/cash'
        )

        return Account.from_api_response(response)

    def get_positions(self) -> List[Position]:
        """Get all open positions"""
        self.logger.debug("Fetching positions")

        response = self._make_request(
            method='GET',
            endpoint='/equity/portfolio'
        )

        if not isinstance(response, list):
            return []

        positions = [Position.from_api_response(p) for p in response]
        self.logger.debug(f"Found {len(positions)} positions")

        return positions

    def get_position(self, ticker: str) -> Optional[Position]:
        """Get position for specific ticker"""
        positions = self.get_positions()

        for position in positions:
            if position.ticker == ticker:
                return position

        return None

    def get_orders(self, ticker: Optional[str] = None) -> List[Order]:
        """
        Get order history

        Args:
            ticker: Optional ticker to filter by

        Returns:
            List of orders
        """
        self.logger.debug(f"Fetching orders{' for ' + ticker if ticker else ''}")

        params = {'ticker': ticker} if ticker else None

        response = self._make_request(
            method='GET',
            endpoint='/equity/history/orders',
            params=params
        )

        if not isinstance(response, list):
            return []

        orders = [Order.from_api_response(o) for o in response]
        self.logger.debug(f"Found {len(orders)} orders")

        return orders

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        self.logger.info(f"Cancelling order: {order_id}")

        try:
            self._make_request(
                method='DELETE',
                endpoint=f'/equity/orders/{order_id}'
            )

            self.logger.info(f"Order cancelled: {order_id}")
            return True

        except Trading212Error as e:
            self.logger.error(f"Failed to cancel order: {e}")
            return False

    def get_instruments(self) -> List[Dict[str, Any]]:
        """Get list of tradable instruments"""
        self.logger.debug("Fetching instruments")

        response = self._make_request(
            method='GET',
            endpoint='/equity/metadata/instruments'
        )

        return response if isinstance(response, list) else []

    def validate_ticker(self, ticker: str) -> bool:
        """
        Validate that ticker is tradable

        Args:
            ticker: Ticker symbol

        Returns:
            True if ticker is valid
        """
        instruments = self.get_instruments()

        for instrument in instruments:
            if instrument.get('ticker') == ticker:
                return True

        return False

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        if not self.enable_rate_limiting or not self.rate_limiter:
            return {'enabled': False}

        return {
            'enabled': True,
            'minute_remaining': self.rate_limiter.minute_limiter.get_remaining(),
            'hour_remaining': self.rate_limiter.hour_limiter.get_remaining(),
            'tokens_available': self.rate_limiter.token_bucket.tokens
        }

    def __repr__(self):
        return f"Trading212Client(environment={self.environment})"
