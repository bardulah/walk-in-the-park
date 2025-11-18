"""
Model Cascading for Cost Optimization
Routes queries to the cheapest capable model, saving up to 87% on LLM costs
"""
from typing import Dict, Any, Optional
from enum import Enum
from config.logging_config import get_logger


logger = get_logger("model_cascade")


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"      # 70% of queries - use cheapest model
    MODERATE = "moderate"  # 20% of queries - use mid-tier model
    COMPLEX = "complex"    # 10% of queries - use best model


class ModelTier:
    """Model tier configuration"""

    # Cost per 1M input tokens (2025 pricing)
    COSTS = {
        'gemini-flash': 0.075,
        'gemini-flash-lite': 0.075,
        'gpt-4o-mini': 0.15,
        'claude-3-haiku': 0.25,
        'gpt-4o': 5.00,
        'claude-3.5-sonnet': 3.00,
        'claude-3-opus': 15.00,
        'gemini-1.5-pro': 1.25
    }

    # Model tiers by capability
    SIMPLE_MODELS = ['gemini-flash', 'gemini-flash-lite']
    MODERATE_MODELS = ['gpt-4o-mini', 'claude-3-haiku']
    COMPLEX_MODELS = ['claude-3.5-sonnet', 'gpt-4o', 'gemini-1.5-pro']


class ModelCascade:
    """
    Intelligent model routing based on query complexity

    Research shows 87% cost savings by routing:
    - 70% of queries to cheapest models ($0.075/1M)
    - 20% of queries to mid-tier models ($0.15/1M)
    - 10% of queries to premium models ($3.00/1M)

    Average cost: (0.7 * $0.075) + (0.2 * $0.15) + (0.1 * $3.00) = $0.38/1M
    vs. using only premium: $3.00/1M
    Savings: 87%

    Usage:
        cascade = ModelCascade()

        # Automatic routing
        model = cascade.select_model(query, context)
        response = llm_router.call(model=model, ...)

        # With cost tracking
        result = cascade.call_with_routing(
            llm_router=llm_router,
            query=query,
            context=context,
            system_prompt=system_prompt
        )
    """

    def __init__(
        self,
        simple_model: str = 'gemini-flash',
        moderate_model: str = 'gpt-4o-mini',
        complex_model: str = 'claude-3.5-sonnet',
        enable_tracking: bool = True
    ):
        """
        Initialize model cascade

        Args:
            simple_model: Model for simple queries (default: gemini-flash)
            moderate_model: Model for moderate queries (default: gpt-4o-mini)
            complex_model: Model for complex queries (default: claude-3.5-sonnet)
            enable_tracking: Track cost savings
        """
        self.simple_model = simple_model
        self.moderate_model = moderate_model
        self.complex_model = complex_model
        self.enable_tracking = enable_tracking

        self.logger = logger

        # Cost tracking
        self.stats = {
            'total_queries': 0,
            'simple_count': 0,
            'moderate_count': 0,
            'complex_count': 0,
            'total_cost': 0.0,
            'cost_if_all_complex': 0.0,
            'savings': 0.0
        }

        self.logger.info(
            f"ModelCascade initialized | Simple: {simple_model} | "
            f"Moderate: {moderate_model} | Complex: {complex_model}"
        )

    def estimate_complexity(
        self,
        query: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueryComplexity:
        """
        Estimate query complexity

        Args:
            query: User query/prompt
            context: Additional context
            metadata: Optional metadata for complexity hints

        Returns:
            QueryComplexity level
        """
        # Check for explicit complexity hints
        if metadata and 'complexity' in metadata:
            complexity_hint = metadata['complexity'].lower()
            if complexity_hint in ['simple', 'easy', 'basic']:
                return QueryComplexity.SIMPLE
            elif complexity_hint in ['complex', 'hard', 'detailed', 'comprehensive']:
                return QueryComplexity.COMPLEX

        # Keyword-based complexity detection
        query_lower = query.lower()

        # Complex keywords
        complex_keywords = [
            'analyze deeply', 'comprehensive', 'detailed analysis',
            'complex', 'synthesize', 'evaluate thoroughly',
            'compare and contrast', 'multi-factor', 'scenario analysis',
            'risk assessment', 'portfolio optimization'
        ]

        if any(kw in query_lower for kw in complex_keywords):
            self.logger.debug(f"Complex query detected (keywords): {query[:50]}...")
            return QueryComplexity.COMPLEX

        # Simple keywords
        simple_keywords = [
            'what is', 'define', 'list', 'show', 'get',
            'current price', 'ticker', 'simple', 'quick'
        ]

        if any(kw in query_lower for kw in simple_keywords):
            self.logger.debug(f"Simple query detected (keywords): {query[:50]}...")
            return QueryComplexity.SIMPLE

        # Length-based heuristics
        total_length = len(query)
        if context:
            total_length += len(context)

        if total_length < 200:
            # Short query = likely simple
            self.logger.debug(f"Simple query detected (length): {total_length} chars")
            return QueryComplexity.SIMPLE

        elif total_length < 1000:
            # Medium length = moderate complexity
            self.logger.debug(f"Moderate query detected (length): {total_length} chars")
            return QueryComplexity.MODERATE

        else:
            # Long query/context = complex
            self.logger.debug(f"Complex query detected (length): {total_length} chars")
            return QueryComplexity.COMPLEX

    def select_model(
        self,
        query: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force_complexity: Optional[QueryComplexity] = None
    ) -> str:
        """
        Select appropriate model based on query complexity

        Args:
            query: User query
            context: Additional context
            metadata: Optional complexity hints
            force_complexity: Force specific complexity level

        Returns:
            Model identifier
        """
        # Estimate or use forced complexity
        if force_complexity:
            complexity = force_complexity
        else:
            complexity = self.estimate_complexity(query, context, metadata)

        # Select model based on complexity
        if complexity == QueryComplexity.SIMPLE:
            model = self.simple_model
            self.stats['simple_count'] += 1
        elif complexity == QueryComplexity.MODERATE:
            model = self.moderate_model
            self.stats['moderate_count'] += 1
        else:  # COMPLEX
            model = self.complex_model
            self.stats['complex_count'] += 1

        self.stats['total_queries'] += 1

        self.logger.info(
            f"Routing query to {model} (complexity: {complexity.value})"
        )

        return model

    def call_with_routing(
        self,
        llm_router,
        query: str,
        system_prompt: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        temperature: float = 0.5,
        max_tokens: int = 2000,
        json_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Call LLM with automatic model routing

        Args:
            llm_router: LLM router instance
            query: User query
            system_prompt: System prompt
            context: Optional context
            metadata: Optional metadata
            temperature: Temperature setting
            max_tokens: Max tokens
            json_mode: JSON mode

        Returns:
            Dict with response and cost tracking
        """
        # Select model
        model = self.select_model(query, context, metadata)

        # Build full user prompt
        user_prompt = query
        if context:
            user_prompt = f"{context}\n\n{query}"

        # Estimate tokens (rough)
        estimated_input_tokens = (len(system_prompt) + len(user_prompt)) / 4
        estimated_output_tokens = max_tokens / 2  # Assume 50% utilization

        # Call LLM
        try:
            response = llm_router.call(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode
            )

            # Track costs
            if self.enable_tracking:
                self._track_cost(model, estimated_input_tokens, estimated_output_tokens)

            return {
                'response': response,
                'model_used': model,
                'estimated_cost': self._estimate_call_cost(
                    model, estimated_input_tokens, estimated_output_tokens
                ),
                'success': True
            }

        except Exception as e:
            self.logger.error(f"LLM call failed with {model}: {e}")

            # Fallback to complex model if routing failed
            if model != self.complex_model:
                self.logger.warning(f"Retrying with {self.complex_model}")

                response = llm_router.call(
                    model=self.complex_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode
                )

                return {
                    'response': response,
                    'model_used': self.complex_model,
                    'fallback': True,
                    'success': True
                }

            raise

    def _track_cost(self, model: str, input_tokens: float, output_tokens: float):
        """Track cost for analytics"""
        cost = self._estimate_call_cost(model, input_tokens, output_tokens)
        self.stats['total_cost'] += cost

        # Calculate what it would cost with complex model
        complex_cost = self._estimate_call_cost(
            self.complex_model, input_tokens, output_tokens
        )
        self.stats['cost_if_all_complex'] += complex_cost

        # Calculate savings
        self.stats['savings'] = (
            self.stats['cost_if_all_complex'] - self.stats['total_cost']
        )

    def _estimate_call_cost(
        self,
        model: str,
        input_tokens: float,
        output_tokens: float
    ) -> float:
        """Estimate cost of a single call"""
        input_cost_per_token = ModelTier.COSTS.get(model, 3.00) / 1_000_000
        output_cost_per_token = input_cost_per_token * 3  # Output typically 3x

        return (input_tokens * input_cost_per_token) + (output_tokens * output_cost_per_token)

    def get_stats(self) -> Dict[str, Any]:
        """Get cost statistics"""
        if self.stats['total_queries'] == 0:
            return self.stats

        # Calculate distribution
        distribution = {
            'simple_pct': (self.stats['simple_count'] / self.stats['total_queries']) * 100,
            'moderate_pct': (self.stats['moderate_count'] / self.stats['total_queries']) * 100,
            'complex_pct': (self.stats['complex_count'] / self.stats['total_queries']) * 100
        }

        # Calculate savings percentage
        if self.stats['cost_if_all_complex'] > 0:
            savings_pct = (self.stats['savings'] / self.stats['cost_if_all_complex']) * 100
        else:
            savings_pct = 0.0

        return {
            **self.stats,
            'distribution': distribution,
            'savings_pct': savings_pct,
            'avg_cost_per_query': self.stats['total_cost'] / self.stats['total_queries']
        }

    def print_stats(self):
        """Print cost statistics"""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("MODEL CASCADE COST STATISTICS")
        print("="*60)
        print(f"Total Queries: {stats['total_queries']}")
        print(f"\nDistribution:")
        print(f"  Simple:   {stats['simple_count']:>4} ({stats['distribution']['simple_pct']:>5.1f}%) -> {self.simple_model}")
        print(f"  Moderate: {stats['moderate_count']:>4} ({stats['distribution']['moderate_pct']:>5.1f}%) -> {self.moderate_model}")
        print(f"  Complex:  {stats['complex_count']:>4} ({stats['distribution']['complex_pct']:>5.1f}%) -> {self.complex_model}")
        print(f"\nCosts:")
        print(f"  Actual Cost:             ${stats['total_cost']:.4f}")
        print(f"  Cost if All Complex:     ${stats['cost_if_all_complex']:.4f}")
        print(f"  Savings:                 ${stats['savings']:.4f}")
        print(f"  Savings Percentage:      {stats['savings_pct']:.1f}%")
        print(f"  Avg Cost per Query:      ${stats['avg_cost_per_query']:.6f}")
        print("="*60 + "\n")

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_queries': 0,
            'simple_count': 0,
            'moderate_count': 0,
            'complex_count': 0,
            'total_cost': 0.0,
            'cost_if_all_complex': 0.0,
            'savings': 0.0
        }
        self.logger.info("Statistics reset")
