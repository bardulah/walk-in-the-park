"""
Base Agent Class
Provides common functionality for all trading agents
"""
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from utils.json_parser import safe_json_parse


class BaseAgent(ABC):
    """
    Abstract base class for all trading agents

    Provides:
    - Common initialization pattern
    - LLM call wrapper with error handling
    - JSON parsing with fallback
    - Progress logging
    """

    def __init__(
        self,
        llm_router,
        model: str,
        temperature: float = 0.5,
        max_tokens: int = 2000,
        agent_name: str = None
    ):
        """
        Initialize base agent

        Args:
            llm_router: LLM router for model calls
            model: Model identifier (e.g., "gpt-4o-mini", "claude-3-5-sonnet")
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
            agent_name: Display name for logging (defaults to class name)
        """
        self.llm_router = llm_router
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.agent_name = agent_name or self.__class__.__name__

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = True
    ) -> str:
        """
        Call LLM with error handling

        Args:
            system_prompt: System instructions for the LLM
            user_prompt: User query/task
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            json_mode: Request JSON output

        Returns:
            Raw LLM response string

        Raises:
            RuntimeError: If LLM call fails
        """
        try:
            response = self.llm_router.call(
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                json_mode=json_mode
            )
            return response
        except Exception as e:
            raise RuntimeError(f"{self.agent_name} LLM call failed: {e}")

    def _parse_json_response(
        self,
        response: str,
        default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse JSON response with robust fallback

        Args:
            response: Raw LLM response string
            default: Default value if parsing fails

        Returns:
            Parsed JSON as dict

        Raises:
            ValueError: If parsing fails and no default provided
        """
        return safe_json_parse(response, default=default)

    def _log_progress(self, message: str, emoji: str = "🔧"):
        """
        Log progress message

        Args:
            message: Progress message
            emoji: Emoji icon (optional)
        """
        print(f"\n{emoji} {self.agent_name}: {message}")
        print(f"   Model: {self.model}")

    def _log_info(self, message: str):
        """Log info message without model details"""
        print(f"   {message}")

    @abstractmethod
    def analyze(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method - must be implemented by subclasses

        Returns:
            Analysis results as dict
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get system prompt for this agent

        Returns:
            System prompt string
        """
        pass

    def _build_error_response(
        self,
        error: Exception,
        error_type: str = "ANALYSIS_ERROR"
    ) -> Dict[str, Any]:
        """
        Build standardized error response

        Args:
            error: Exception that occurred
            error_type: Error type identifier

        Returns:
            Error response dict
        """
        return {
            "error": error_type,
            "message": str(error),
            "agent": self.agent_name,
            "success": False
        }

    def __repr__(self):
        return f"{self.agent_name}(model={self.model}, temp={self.temperature})"
