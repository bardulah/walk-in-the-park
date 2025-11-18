"""
Multi-Model Consensus Mechanism
Validates critical decisions using multiple LLMs to prevent hallucinations and errors
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from config.logging_config import get_logger


logger = get_logger("consensus")


class ConsensusResult:
    """Result from consensus mechanism"""

    def __init__(
        self,
        consensus_reached: bool,
        agreed_fields: Dict[str, Any],
        disagreed_fields: Dict[str, List[Any]],
        model_responses: List[Dict[str, Any]],
        confidence: str = "low"
    ):
        """
        Initialize consensus result

        Args:
            consensus_reached: Whether models reached consensus
            agreed_fields: Fields where models agreed
            disagreed_fields: Fields where models disagreed (with all values)
            model_responses: Full responses from each model
            confidence: Confidence level (high|medium|low)
        """
        self.consensus_reached = consensus_reached
        self.agreed_fields = agreed_fields
        self.disagreed_fields = disagreed_fields
        self.model_responses = model_responses
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            'consensus_reached': self.consensus_reached,
            'agreed_fields': self.agreed_fields,
            'disagreed_fields': self.disagreed_fields,
            'model_responses': self.model_responses,
            'confidence': self.confidence,
            'num_models': len(self.model_responses)
        }

    def __repr__(self):
        status = "✅ CONSENSUS" if self.consensus_reached else "⚠️  NO CONSENSUS"
        return f"ConsensusResult({status}, confidence={self.confidence})"


class ConsensusValidator:
    """
    Multi-model consensus validator

    Queries multiple LLMs in parallel and requires agreement on critical fields
    before accepting a recommendation. This is "Layer 5: Consensus Cross-Verification"
    from the research, which shows 95%+ confidence in consensus outputs.

    Usage:
        validator = ConsensusValidator(llm_router)

        # For high-stakes decisions
        result = validator.get_consensus(
            models=['gpt-4o', 'claude-3.5-sonnet', 'gemini-1.5-pro'],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            critical_fields=['recommendation', 'risk_level']
        )

        if result.consensus_reached:
            # Models agree - safe to proceed
            decision = result.agreed_fields
        else:
            # Models disagree - escalate to human review
            return {'needs_human_review': True, 'consensus_result': result}
    """

    def __init__(self, llm_router, max_workers: int = 3):
        """
        Initialize consensus validator

        Args:
            llm_router: LLM router for making calls
            max_workers: Maximum parallel workers
        """
        self.llm_router = llm_router
        self.max_workers = max_workers
        self.logger = logger

    def get_consensus(
        self,
        models: List[str],
        system_prompt: str,
        user_prompt: str,
        critical_fields: List[str],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        agreement_threshold: float = 0.67  # 2/3 agreement
    ) -> ConsensusResult:
        """
        Get consensus from multiple models

        Args:
            models: List of model identifiers (e.g., ['gpt-4o', 'claude-3.5-sonnet'])
            system_prompt: System prompt for all models
            user_prompt: User prompt for all models
            critical_fields: Fields that must agree for consensus
            temperature: Temperature for LLM calls
            max_tokens: Max tokens for responses
            agreement_threshold: Minimum fraction of models that must agree

        Returns:
            ConsensusResult
        """
        if len(models) < 2:
            raise ValueError("Need at least 2 models for consensus")

        self.logger.info(f"Getting consensus from {len(models)} models: {models}")

        # Query all models in parallel
        responses = self._query_models_parallel(
            models=models,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Parse responses
        parsed_responses = []
        for model, response in zip(models, responses):
            try:
                from utils.json_parser import safe_json_parse
                parsed = safe_json_parse(response)
                parsed['_model'] = model
                parsed_responses.append(parsed)
            except Exception as e:
                self.logger.error(f"Failed to parse response from {model}: {e}")
                parsed_responses.append({'_model': model, '_error': str(e)})

        # Check consensus on critical fields
        agreed_fields, disagreed_fields = self._check_agreement(
            responses=parsed_responses,
            critical_fields=critical_fields,
            threshold=agreement_threshold
        )

        # Determine if consensus reached
        consensus_reached = len(disagreed_fields) == 0

        # Determine confidence
        if consensus_reached and len(models) >= 3:
            confidence = "high"
        elif consensus_reached:
            confidence = "medium"
        else:
            confidence = "low"

        result = ConsensusResult(
            consensus_reached=consensus_reached,
            agreed_fields=agreed_fields,
            disagreed_fields=disagreed_fields,
            model_responses=parsed_responses,
            confidence=confidence
        )

        if consensus_reached:
            self.logger.info(f"✅ Consensus reached: {list(agreed_fields.keys())}")
        else:
            self.logger.warning(f"⚠️  No consensus: {list(disagreed_fields.keys())}")

        return result

    def _query_models_parallel(
        self,
        models: List[str],
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> List[str]:
        """Query multiple models in parallel"""

        def query_model(model: str) -> str:
            """Query single model"""
            try:
                self.logger.debug(f"Querying {model}...")

                response = self.llm_router.call(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=True
                )

                self.logger.debug(f"Response from {model}: {len(response)} chars")
                return response

            except Exception as e:
                self.logger.error(f"Query failed for {model}: {e}")
                return json.dumps({'error': str(e), '_model': model})

        # Execute queries in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            responses = list(executor.map(query_model, models))

        return responses

    def _check_agreement(
        self,
        responses: List[Dict[str, Any]],
        critical_fields: List[str],
        threshold: float
    ) -> tuple[Dict[str, Any], Dict[str, List[Any]]]:
        """
        Check agreement across responses

        Args:
            responses: Parsed responses from models
            critical_fields: Fields to check
            threshold: Agreement threshold (0.0-1.0)

        Returns:
            Tuple of (agreed_fields, disagreed_fields)
        """
        agreed_fields = {}
        disagreed_fields = {}

        num_models = len(responses)
        required_agreement = int(num_models * threshold)

        for field in critical_fields:
            # Collect values for this field
            values = []
            for response in responses:
                if field in response and '_error' not in response:
                    values.append(response[field])

            if not values:
                # Field missing from all responses
                disagreed_fields[field] = []
                continue

            # Normalize values for comparison
            normalized_values = [self._normalize_value(v) for v in values]

            # Count occurrences of each value
            value_counts = {}
            for norm_val, orig_val in zip(normalized_values, values):
                if norm_val not in value_counts:
                    value_counts[norm_val] = {'count': 0, 'original': orig_val}
                value_counts[norm_val]['count'] += 1

            # Find most common value
            max_count = max(v['count'] for v in value_counts.values())
            most_common = [
                v['original'] for v in value_counts.values()
                if v['count'] == max_count
            ][0]

            # Check if threshold met
            if max_count >= required_agreement:
                agreed_fields[field] = most_common
            else:
                # Disagreement - return all values
                disagreed_fields[field] = values

        return agreed_fields, disagreed_fields

    def _normalize_value(self, value: Any) -> Any:
        """
        Normalize value for comparison

        Handles variations like:
        - "buy" vs "BUY" vs "Buy"
        - 0.5 vs 50 (percentage)
        - "strong_buy" vs "strong buy"
        """
        if isinstance(value, str):
            # Lowercase and remove spaces/underscores
            return value.lower().replace(' ', '').replace('_', '')

        if isinstance(value, (int, float)):
            # Round to 2 decimal places
            return round(float(value), 2)

        if isinstance(value, bool):
            return value

        if isinstance(value, list):
            # Sort lists for comparison
            return tuple(sorted(str(v) for v in value))

        # Default: convert to string
        return str(value)

    def validate_high_stakes_decision(
        self,
        models: List[str],
        system_prompt: str,
        user_prompt: str,
        min_models: int = 3,
        critical_fields: Optional[List[str]] = None
    ) -> ConsensusResult:
        """
        Validate high-stakes decision requiring strong consensus

        Args:
            models: Models to use (will use first min_models if more provided)
            system_prompt: System prompt
            user_prompt: User prompt
            min_models: Minimum number of models required
            critical_fields: Critical fields to check

        Returns:
            ConsensusResult
        """
        if len(models) < min_models:
            raise ValueError(f"Need at least {min_models} models for high-stakes validation")

        # Use first min_models
        models_to_use = models[:min_models]

        # Default critical fields for trading decisions
        if critical_fields is None:
            critical_fields = ['recommendation', 'risk_level', 'action']

        self.logger.info(f"High-stakes validation with {len(models_to_use)} models")

        return self.get_consensus(
            models=models_to_use,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            critical_fields=critical_fields,
            temperature=0.2,  # Low temperature for consistency
            agreement_threshold=0.67  # Require 2/3 agreement
        )

    def get_majority_vote(
        self,
        responses: List[Dict[str, Any]],
        field: str
    ) -> Optional[Any]:
        """
        Get majority vote for a specific field

        Args:
            responses: Model responses
            field: Field to get majority for

        Returns:
            Majority value or None if no majority
        """
        values = [r.get(field) for r in responses if field in r]

        if not values:
            return None

        # Count occurrences
        from collections import Counter
        counts = Counter(self._normalize_value(v) for v in values)

        # Get most common
        most_common = counts.most_common(1)[0]

        # Find original value
        most_common_normalized = most_common[0]
        for val in values:
            if self._normalize_value(val) == most_common_normalized:
                return val

        return None

    def __repr__(self):
        return f"ConsensusValidator(max_workers={self.max_workers})"


# Utility function for easy consensus checking
def require_consensus(
    llm_router,
    models: List[str],
    system_prompt: str,
    user_prompt: str,
    critical_fields: List[str]
) -> Dict[str, Any]:
    """
    Convenience function to get consensus or raise for disagreement

    Args:
        llm_router: LLM router
        models: Models to use
        system_prompt: System prompt
        user_prompt: User prompt
        critical_fields: Critical fields

    Returns:
        Agreed fields dict

    Raises:
        ValueError: If consensus not reached
    """
    validator = ConsensusValidator(llm_router)

    result = validator.get_consensus(
        models=models,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        critical_fields=critical_fields
    )

    if not result.consensus_reached:
        raise ValueError(
            f"Consensus not reached. Disagreed fields: {list(result.disagreed_fields.keys())}"
        )

    return result.agreed_fields
