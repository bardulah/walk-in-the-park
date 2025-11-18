"""
Unified LLM Router supporting both Gemini (REST API) and OpenRouter
Optimized for cost efficiency using Google credits
"""
import json
import requests
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from config.logging_config import get_logger
from utils.rate_limiter import LLMRateLimiter, OPENROUTER_RATE_LIMITS, GEMINI_RATE_LIMITS


class UnifiedLLMRouter:
    """
    Routes LLM calls to appropriate providers:
    - Gemini via REST API for models covered by $200 credits
    - OpenRouter for other models (gpt-4o-mini, claude-3.5-sonnet)
    """

    def __init__(self, gemini_api_key: str, openrouter_api_key: str, enable_rate_limiting: bool = True):
        """
        Initialize unified router

        Args:
            gemini_api_key: Google Gemini API key
            openrouter_api_key: OpenRouter API key
            enable_rate_limiting: Enable rate limiting to prevent API throttling
        """
        self.gemini_api_key = gemini_api_key
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/models"

        # Configure OpenRouter
        self.openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key
        )

        self.total_cost = 0.0
        self.call_count = 0

        # Setup logger
        self.logger = get_logger("llm_router.unified")

        # Setup rate limiters
        self.enable_rate_limiting = enable_rate_limiting
        if enable_rate_limiting:
            self.openrouter_limiter = LLMRateLimiter(OPENROUTER_RATE_LIMITS)
            self.gemini_limiter = LLMRateLimiter(GEMINI_RATE_LIMITS)
            self.logger.info("Rate limiting enabled")
        else:
            self.openrouter_limiter = None
            self.gemini_limiter = None
            self.logger.warning("Rate limiting disabled - use with caution")

        # Model routing map
        self.gemini_models = {
            'gemini-2.5-flash': 'gemini-1.5-flash',  # Using 1.5 Flash (stable)
            'gemini-pro': 'gemini-1.5-pro',
            'gemini-flash': 'gemini-1.5-flash'
        }

        self.openrouter_models = {
            'gpt-4o-mini': 'openai/gpt-4o-mini',
            'claude-3-5-sonnet': 'anthropic/claude-3.5-sonnet',
            'claude-3-5-haiku': 'anthropic/claude-3.5-haiku',
            'gpt-4o': 'openai/gpt-4o',
            'gemini-flash-or': 'google/gemini-flash-1.5-8b',  # Gemini via OpenRouter
            'gemini-2.5-flash': 'google/gemini-flash-1.5-8b'  # Route through OpenRouter instead
        }

        # Cost per 1K tokens (input/output)
        self.costs = {
            'gemini-2.5-flash': (0.000075, 0.0003),  # Gemini via OpenRouter
            'gemini-flash-or': (0.000075, 0.0003),  # Gemini via OpenRouter
            'gpt-4o-mini': (0.00015, 0.0006),
            'claude-3-5-sonnet': (0.003, 0.015),
            'claude-3-5-haiku': (0.001, 0.005),
        }

    def call(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = True
    ) -> str:
        """
        Call appropriate LLM based on model name

        Args:
            model: Model identifier (e.g., 'gemini-2.5-flash', 'gpt-4o-mini')
            system_prompt: System instructions
            user_prompt: User message
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            json_mode: Force JSON output

        Returns:
            Model response as string (JSON if json_mode=True)
        """
        self.call_count += 1
        self.logger.debug(f"Call #{self.call_count} | Model: {model} | Temp: {temperature}")

        # Route to appropriate provider
        # For now, route all through OpenRouter (Gemini direct API has auth issues)
        if model in self.openrouter_models:
            return self._call_openrouter(
                model, system_prompt, user_prompt, temperature, max_tokens, json_mode
            )
        else:
            self.logger.error(f"Unknown model requested: {model}")
            raise ValueError(f"Unknown model: {model}")

    def _call_gemini(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> str:
        """Call Gemini REST API"""
        # Rate limiting
        if self.enable_rate_limiting and self.gemini_limiter:
            if not self.gemini_limiter.acquire(tokens=max_tokens, blocking=True, timeout=30):
                raise RuntimeError("Rate limit exceeded for Gemini API - request timed out")
            self.logger.debug(f"Rate limit check passed | Status: {self.gemini_limiter.get_status()}")

        gemini_model_name = self.gemini_models[model]

        url = f"{self.gemini_base_url}/{gemini_model_name}:generateContent"

        # Build request
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"System: {system_prompt}\n\nUser: {user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        # Make request
        response = requests.post(
            url,
            params={"key": self.gemini_api_key},
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()

        # Extract text from Gemini response
        # Expected format: {candidates: [{content: {parts: [{text: "..."}]}, finishReason: "STOP"}], usageMetadata: {...}}
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    response_text = parts[0]["text"]

                    # Track cost using actual token counts from usageMetadata
                    if "usageMetadata" in data:
                        usage = data["usageMetadata"]
                        prompt_tokens = usage.get("promptTokenCount", 0)
                        completion_tokens = usage.get("candidatesTokenCount", 0)

                        if model in self.costs:
                            input_cost, output_cost = self.costs[model]
                            cost = (prompt_tokens / 1000 * input_cost) + \
                                   (completion_tokens / 1000 * output_cost)
                            self.total_cost += cost

                            self.logger.debug(
                                f"Gemini cost tracked (actual) | Tokens: {prompt_tokens}+{completion_tokens} | "
                                f"Cost: ${cost:.4f} | Total: ${self.total_cost:.4f}"
                            )
                    else:
                        # Fallback to character-based estimation if no usage metadata
                        input_chars = len(system_prompt) + len(user_prompt)
                        output_chars = len(response_text)
                        prompt_tokens = input_chars // 4
                        completion_tokens = output_chars // 4

                        if model in self.costs:
                            input_cost, output_cost = self.costs[model]
                            cost = (prompt_tokens / 1000 * input_cost) + \
                                   (completion_tokens / 1000 * output_cost)
                            self.total_cost += cost

                            self.logger.debug(
                                f"Gemini cost tracked (estimated) | Chars: {input_chars}+{output_chars} | "
                                f"Est. tokens: {prompt_tokens}+{completion_tokens} | "
                                f"Cost: ${cost:.4f} | Total: ${self.total_cost:.4f}"
                            )

                    return response_text

        # If we get here, response format is unexpected
        raise ValueError(f"Unexpected Gemini response format. Got: {json.dumps(data, indent=2)[:500]}")

    def _call_openrouter(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> str:
        """Call OpenRouter API"""
        # Rate limiting
        if self.enable_rate_limiting and self.openrouter_limiter:
            if not self.openrouter_limiter.acquire(tokens=max_tokens, blocking=True, timeout=30):
                raise RuntimeError("Rate limit exceeded for OpenRouter API - request timed out")
            self.logger.debug(f"Rate limit check passed | Status: {self.openrouter_limiter.get_status()}")

        openrouter_model = self.openrouter_models[model]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        kwargs = {
            "model": openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.openrouter_client.chat.completions.create(**kwargs)

        # Track cost
        usage = response.usage
        if model in self.costs:
            input_cost, output_cost = self.costs[model]
            cost = (usage.prompt_tokens / 1000 * input_cost) + \
                   (usage.completion_tokens / 1000 * output_cost)
            self.total_cost += cost

            self.logger.debug(
                f"Cost tracked | Tokens: {usage.prompt_tokens}+{usage.completion_tokens} | "
                f"Cost: ${cost:.4f} | Total: ${self.total_cost:.4f}"
            )

        return response.choices[0].message.content

    def get_total_cost(self) -> float:
        """Get total cost for all calls"""
        return self.total_cost

    def reset_cost(self):
        """Reset cost counter"""
        self.total_cost = 0.0

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status for all providers"""
        status = {"rate_limiting_enabled": self.enable_rate_limiting}

        if self.enable_rate_limiting:
            if self.openrouter_limiter:
                status["openrouter"] = self.openrouter_limiter.get_status()
            if self.gemini_limiter:
                status["gemini"] = self.gemini_limiter.get_status()

        return status
