"""
Simplified LLM Router - OpenRouter only for MVP
(Gemini support to be added later after fixing dependencies)
"""
import json
from typing import Optional, Dict, Any
from openai import OpenAI

class LLMRouter:
    """Simple LLM router using OpenRouter"""

    def __init__(self, openrouter_api_key: str, gemini_api_key: str = None):
        """
        Initialize LLM router

        Args:
            openrouter_api_key: OpenRouter API key
            gemini_api_key: Gemini API key (not used in MVP, for compatibility)
        """
        self.openrouter_api_key = openrouter_api_key

        # Configure OpenRouter client
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key
        )

        # Track costs
        self.total_cost = 0.0

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
        Call LLM with given prompts

        Args:
            model: Model name (e.g., "gpt-4o-mini", "claude-3-5-sonnet")
            system_prompt: System/instruction prompt
            user_prompt: User message/query
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            json_mode: Request JSON output

        Returns:
            LLM response as string
        """
        # Map friendly names to OpenRouter model IDs
        model_map = {
            "gpt-4o-mini": "openai/gpt-4o-mini",
            "claude-3-5-sonnet": "anthropic/claude-3.5-sonnet",
            "claude-3-haiku": "anthropic/claude-3-haiku",
            "gemini-2.5-flash": "openai/gpt-4o-mini",  # Fallback to GPT-4o-mini for now
            "gemini-flash": "openai/gpt-4o-mini"
        }
        actual_model = model_map.get(model, model)

        try:
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # Call API
            response = self.client.chat.completions.create(
                model=actual_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if json_mode else None
            )

            # Extract cost
            if hasattr(response, 'usage'):
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

                if "gpt-4o-mini" in actual_model:
                    cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
                elif "claude-3.5-sonnet" in actual_model:
                    cost = (input_tokens / 1_000_000 * 3.00) + (output_tokens / 1_000_000 * 15.00)
                elif "claude-3-haiku" in actual_model:
                    cost = (input_tokens / 1_000_000 * 0.25) + (output_tokens / 1_000_000 * 1.25)
                else:
                    cost = 0.01  # Default estimate

                self.total_cost += cost

            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"OpenRouter API error: {e}")

    def get_total_cost(self) -> float:
        """Get total cost incurred so far"""
        return round(self.total_cost, 4)

    def reset_cost(self):
        """Reset cost counter"""
        self.total_cost = 0.0
