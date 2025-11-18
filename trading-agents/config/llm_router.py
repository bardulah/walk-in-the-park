"""
LLM Router - Routes calls to appropriate LLM provider
Supports Gemini (for credits) and OpenRouter (for other models)
"""
import os
import json
from typing import Optional, Dict, Any
import google.generativeai as genai
from openai import OpenAI

class LLMRouter:
    """Routes LLM calls to appropriate provider"""

    def __init__(self, gemini_api_key: str, openrouter_api_key: str):
        """
        Initialize LLM router

        Args:
            gemini_api_key: Google Gemini API key
            openrouter_api_key: OpenRouter API key for other models
        """
        self.gemini_api_key = gemini_api_key
        self.openrouter_api_key = openrouter_api_key

        # Configure Gemini
        genai.configure(api_key=gemini_api_key)

        # Configure OpenRouter client
        self.openrouter_client = OpenAI(
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
            model: Model name (e.g., "gemini-2.5-flash", "gpt-4o-mini", "claude-3-5-sonnet")
            system_prompt: System/instruction prompt
            user_prompt: User message/query
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            json_mode: Request JSON output

        Returns:
            LLM response as string
        """
        if model.startswith("gemini"):
            return self._call_gemini(model, system_prompt, user_prompt, temperature, max_tokens)
        else:
            return self._call_openrouter(model, system_prompt, user_prompt, temperature, max_tokens, json_mode)

    def _call_gemini(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call Google Gemini API"""
        try:
            # Map to actual Gemini model names
            model_map = {
                "gemini-2.5-flash": "gemini-2.0-flash-exp",
                "gemini-2.5-pro": "gemini-2.0-flash-exp",  # Using flash for now
                "gemini-flash": "gemini-2.0-flash-exp"
            }
            actual_model = model_map.get(model, "gemini-2.0-flash-exp")

            # Initialize model
            gemini_model = genai.GenerativeModel(
                model_name=actual_model,
                system_instruction=system_prompt
            )

            # Generate response
            response = gemini_model.generate_content(
                user_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )

            # Extract cost (approximate)
            # Gemini Flash: $0.30/M input, $2.50/M output
            # Use character-based estimation: 1 token ≈ 4 characters for English text
            input_chars = len(system_prompt) + len(user_prompt)
            output_chars = len(response.text)
            input_tokens = input_chars // 4
            output_tokens = output_chars // 4
            cost = (input_tokens / 1_000_000 * 0.30) + (output_tokens / 1_000_000 * 2.50)
            self.total_cost += cost

            return response.text

        except Exception as e:
            print(f"⚠️  Gemini API error: {e}")
            # Fallback to OpenRouter GPT-4o-mini
            print("  → Falling back to OpenRouter gpt-4o-mini")
            return self._call_openrouter("gpt-4o-mini", system_prompt, user_prompt, temperature, max_tokens, True)

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
        try:
            # Map friendly names to OpenRouter model IDs
            model_map = {
                "gpt-4o-mini": "openai/gpt-4o-mini",
                "claude-3-5-sonnet": "anthropic/claude-3.5-sonnet",
                "claude-3-haiku": "anthropic/claude-3-haiku"
            }
            actual_model = model_map.get(model, model)

            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # Call API
            response = self.openrouter_client.chat.completions.create(
                model=actual_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if json_mode else None
            )

            # Extract cost
            if hasattr(response, 'usage'):
                # Approximate costs (will vary by model)
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
