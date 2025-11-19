"""
Rate limiter utility to prevent API throttling
Implements token bucket and sliding window algorithms
"""
import time
import threading
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 3600
    max_tokens_per_minute: Optional[int] = None
    burst_size: Optional[int] = None  # Allow bursts up to this size


class TokenBucket:
    """
    Token bucket rate limiter

    Allows bursts while maintaining average rate limit
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        initial_tokens: Optional[int] = None
    ):
        """
        Initialize token bucket

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
            initial_tokens: Initial token count (defaults to capacity)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Try to consume tokens

        Args:
            tokens: Number of tokens to consume
            blocking: If True, wait for tokens to become available
            timeout: Maximum wait time in seconds

        Returns:
            True if tokens were consumed, False otherwise
        """
        start_time = time.time()

        while True:
            with self.lock:
                # Refill tokens based on time elapsed
                now = time.time()
                elapsed = now - self.last_refill
                refill_amount = elapsed * self.refill_rate

                self.tokens = min(self.capacity, self.tokens + refill_amount)
                self.last_refill = now

                # Try to consume
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

            # If not blocking, return immediately
            if not blocking:
                return False

            # Check timeout
            if timeout is not None:
                if time.time() - start_time >= timeout:
                    return False

            # Wait a bit before retrying
            time.sleep(0.1)

    def get_available_tokens(self) -> float:
        """Get current number of available tokens"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            refill_amount = elapsed * self.refill_rate
            return min(self.capacity, self.tokens + refill_amount)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter

    Tracks requests in a sliding time window
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize sliding window limiter

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.Lock()

    def allow_request(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Check if request is allowed

        Args:
            blocking: If True, wait until request can be made
            timeout: Maximum wait time in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        start_time = time.time()

        while True:
            with self.lock:
                now = time.time()
                cutoff = now - self.window_seconds

                # Remove old requests outside window
                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()

                # Check if we can make a request
                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return True

            # If not blocking, return immediately
            if not blocking:
                return False

            # Check timeout
            if timeout is not None:
                if time.time() - start_time >= timeout:
                    return False

            # Wait until next slot opens
            if self.requests:
                wait_time = self.requests[0] + self.window_seconds - time.time()
                if wait_time > 0:
                    time.sleep(min(wait_time + 0.1, 1.0))
            else:
                time.sleep(0.1)

    def get_current_usage(self) -> int:
        """Get number of requests in current window"""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Remove old requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            return len(self.requests)

    def get_time_until_next_slot(self) -> float:
        """Get seconds until next request slot is available"""
        with self.lock:
            if len(self.requests) < self.max_requests:
                return 0.0

            now = time.time()
            cutoff = now - self.window_seconds

            if self.requests:
                return max(0.0, self.requests[0] + self.window_seconds - now)

            return 0.0


class LLMRateLimiter:
    """
    Comprehensive rate limiter for LLM APIs

    Combines multiple rate limiting strategies
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize LLM rate limiter

        Args:
            config: Rate limit configuration
        """
        self.config = config

        # Per-minute limiter (primary)
        self.minute_limiter = SlidingWindowRateLimiter(
            max_requests=config.max_requests_per_minute,
            window_seconds=60
        )

        # Per-hour limiter (secondary)
        self.hour_limiter = SlidingWindowRateLimiter(
            max_requests=config.max_requests_per_hour,
            window_seconds=3600
        )

        # Token bucket for burst handling
        burst_size = config.burst_size or config.max_requests_per_minute
        refill_rate = config.max_requests_per_minute / 60.0  # tokens per second

        self.token_bucket = TokenBucket(
            capacity=burst_size,
            refill_rate=refill_rate
        )

        # Token consumption tracking (if configured)
        if config.max_tokens_per_minute:
            self.token_limiter = TokenBucket(
                capacity=config.max_tokens_per_minute,
                refill_rate=config.max_tokens_per_minute / 60.0
            )
        else:
            self.token_limiter = None

    def acquire(
        self,
        tokens: Optional[int] = None,
        blocking: bool = True,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Acquire permission to make API call

        Args:
            tokens: Expected token usage (optional)
            blocking: If True, wait for permission
            timeout: Maximum wait time in seconds

        Returns:
            True if permission granted, False otherwise
        """
        # Check token bucket (allows bursts)
        if not self.token_bucket.consume(1, blocking=blocking, timeout=timeout):
            return False

        # Check per-minute limit
        if not self.minute_limiter.allow_request(blocking=blocking, timeout=timeout):
            return False

        # Check per-hour limit
        if not self.hour_limiter.allow_request(blocking=blocking, timeout=timeout):
            return False

        # Check token consumption limit if configured
        if tokens and self.token_limiter:
            if not self.token_limiter.consume(tokens, blocking=blocking, timeout=timeout):
                return False

        return True

    def get_status(self) -> Dict[str, any]:
        """Get current rate limiter status"""
        return {
            "requests_this_minute": self.minute_limiter.get_current_usage(),
            "requests_this_hour": self.hour_limiter.get_current_usage(),
            "max_per_minute": self.config.max_requests_per_minute,
            "max_per_hour": self.config.max_requests_per_hour,
            "available_burst_tokens": self.token_bucket.get_available_tokens(),
            "time_until_next_minute_slot": self.minute_limiter.get_time_until_next_slot(),
            "time_until_next_hour_slot": self.hour_limiter.get_time_until_next_slot(),
        }


# Preset configurations for common LLM providers
OPENAI_RATE_LIMITS = RateLimitConfig(
    max_requests_per_minute=60,
    max_requests_per_hour=3600,
    max_tokens_per_minute=90000,
    burst_size=10
)

ANTHROPIC_RATE_LIMITS = RateLimitConfig(
    max_requests_per_minute=50,
    max_requests_per_hour=3000,
    max_tokens_per_minute=100000,
    burst_size=5
)

GEMINI_RATE_LIMITS = RateLimitConfig(
    max_requests_per_minute=60,
    max_requests_per_hour=1500,
    burst_size=15
)

OPENROUTER_RATE_LIMITS = RateLimitConfig(
    max_requests_per_minute=100,  # More generous, depends on plan
    max_requests_per_hour=6000,
    burst_size=20
)
