"""
Trading System Metrics and Monitoring
Tracks performance, costs, accuracy, and system health
"""
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
from config.logging_config import get_logger


logger = get_logger("metrics")


class MetricsCollector:
    """
    Comprehensive metrics collection for trading system

    Tracks:
    - Hallucination rates by model
    - Consensus success/failure rates
    - Cost per analysis by agent
    - Response times by component
    - Decision accuracy (predictions vs outcomes)
    - Safety violations
    - Model cascade distribution

    Usage:
        metrics = MetricsCollector()

        # Track analysis
        with metrics.track_analysis('portfolio_analyst'):
            result = portfolio_analyst.analyze(data)

        metrics.record_cost(agent='portfolio_analyst', cost=0.05)
        metrics.record_hallucination(agent='market_analyst', caught=True)

        # Get summary
        summary = metrics.get_summary()
        metrics.print_dashboard()
    """

    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize metrics collector

        Args:
            persist_path: Path to persist metrics (optional)
        """
        self.persist_path = Path(persist_path) if persist_path else None
        self.logger = logger

        # Metrics storage
        self.metrics = {
            # Hallucinations
            'hallucinations': {
                'total': 0,
                'caught': 0,
                'missed': 0,
                'by_model': defaultdict(lambda: {'total': 0, 'caught': 0})
            },

            # Consensus
            'consensus': {
                'total_attempts': 0,
                'consensus_reached': 0,
                'consensus_failed': 0,
                'by_models': defaultdict(int)
            },

            # Costs
            'costs': {
                'total': 0.0,
                'by_agent': defaultdict(float),
                'by_model': defaultdict(float),
                'cascade_savings': 0.0
            },

            # Response times (in seconds)
            'response_times': {
                'by_agent': defaultdict(list),
                'by_phase': defaultdict(list)
            },

            # Accuracy (predictions vs outcomes)
            'accuracy': {
                'total_predictions': 0,
                'correct_predictions': 0,
                'predictions': []  # Store for analysis
            },

            # Safety
            'safety': {
                'violations': 0,
                'kill_switch_triggers': 0,
                'trades_blocked': 0,
                'by_violation_type': defaultdict(int)
            },

            # Model cascade
            'model_cascade': {
                'total_queries': 0,
                'simple_count': 0,
                'moderate_count': 0,
                'complex_count': 0
            },

            # System health
            'health': {
                'errors': 0,
                'warnings': 0,
                'by_component': defaultdict(int)
            }
        }

        # Recent events (rolling window)
        self.recent_events = deque(maxlen=1000)

        # Session start time
        self.session_start = datetime.now()

        self.logger.info("MetricsCollector initialized")

    def track_analysis(self, agent_name: str):
        """
        Context manager to track analysis duration

        Usage:
            with metrics.track_analysis('portfolio_analyst'):
                result = portfolio_analyst.analyze(data)
        """
        return AnalysisTimer(self, agent_name)

    def record_hallucination(
        self,
        agent: str,
        model: str,
        caught: bool,
        field: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Record hallucination event"""
        self.metrics['hallucinations']['total'] += 1

        if caught:
            self.metrics['hallucinations']['caught'] += 1
        else:
            self.metrics['hallucinations']['missed'] += 1

        # Track by model
        self.metrics['hallucinations']['by_model'][model]['total'] += 1
        if caught:
            self.metrics['hallucinations']['by_model'][model]['caught'] += 1

        # Record event
        self.recent_events.append({
            'type': 'hallucination',
            'agent': agent,
            'model': model,
            'caught': caught,
            'field': field,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

        if not caught:
            self.logger.warning(
                f"⚠️  Hallucination MISSED | Agent: {agent} | Model: {model} | Field: {field}"
            )

    def record_consensus(
        self,
        models: List[str],
        consensus_reached: bool,
        agreed_fields: Optional[Dict] = None,
        disagreed_fields: Optional[Dict] = None
    ):
        """Record consensus attempt"""
        self.metrics['consensus']['total_attempts'] += 1

        if consensus_reached:
            self.metrics['consensus']['consensus_reached'] += 1
        else:
            self.metrics['consensus']['consensus_failed'] += 1

        # Track model combination
        model_key = '+'.join(sorted(models))
        self.metrics['consensus']['by_models'][model_key] += 1

        # Record event
        self.recent_events.append({
            'type': 'consensus',
            'models': models,
            'reached': consensus_reached,
            'agreed_fields': list(agreed_fields.keys()) if agreed_fields else [],
            'disagreed_fields': list(disagreed_fields.keys()) if disagreed_fields else [],
            'timestamp': datetime.now().isoformat()
        })

    def record_cost(
        self,
        agent: str,
        model: str,
        cost: float,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ):
        """Record cost"""
        self.metrics['costs']['total'] += cost
        self.metrics['costs']['by_agent'][agent] += cost
        self.metrics['costs']['by_model'][model] += cost

        # Record event
        self.recent_events.append({
            'type': 'cost',
            'agent': agent,
            'model': model,
            'cost': cost,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'timestamp': datetime.now().isoformat()
        })

    def record_response_time(self, agent: str, duration_seconds: float, phase: Optional[str] = None):
        """Record response time"""
        self.metrics['response_times']['by_agent'][agent].append(duration_seconds)

        if phase:
            self.metrics['response_times']['by_phase'][phase].append(duration_seconds)

    def record_prediction(
        self,
        ticker: str,
        prediction: str,
        actual_outcome: Optional[str] = None,
        confidence: Optional[float] = None
    ):
        """
        Record trading prediction

        Args:
            ticker: Stock ticker
            prediction: Predicted direction (buy/sell/hold)
            actual_outcome: Actual result (if known)
            confidence: Confidence level
        """
        self.metrics['accuracy']['total_predictions'] += 1

        prediction_record = {
            'ticker': ticker,
            'prediction': prediction,
            'actual_outcome': actual_outcome,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat(),
            'correct': None
        }

        if actual_outcome is not None:
            correct = (prediction.lower() == actual_outcome.lower())
            prediction_record['correct'] = correct

            if correct:
                self.metrics['accuracy']['correct_predictions'] += 1

        self.metrics['accuracy']['predictions'].append(prediction_record)

    def record_safety_violation(
        self,
        violation_type: str,
        details: str,
        trade_blocked: bool = True
    ):
        """Record safety violation"""
        self.metrics['safety']['violations'] += 1
        self.metrics['safety']['by_violation_type'][violation_type] += 1

        if trade_blocked:
            self.metrics['safety']['trades_blocked'] += 1

        # Record event
        self.recent_events.append({
            'type': 'safety_violation',
            'violation_type': violation_type,
            'details': details,
            'trade_blocked': trade_blocked,
            'timestamp': datetime.now().isoformat()
        })

        self.logger.warning(
            f"⚠️  Safety Violation | Type: {violation_type} | Blocked: {trade_blocked}"
        )

    def record_kill_switch(self, reason: str):
        """Record kill switch activation"""
        self.metrics['safety']['kill_switch_triggers'] += 1

        self.recent_events.append({
            'type': 'kill_switch',
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })

        self.logger.critical(f"🚨 Kill switch triggered | Reason: {reason}")

    def record_model_cascade(self, complexity: str):
        """Record model cascade routing"""
        self.metrics['model_cascade']['total_queries'] += 1

        if complexity == 'simple':
            self.metrics['model_cascade']['simple_count'] += 1
        elif complexity == 'moderate':
            self.metrics['model_cascade']['moderate_count'] += 1
        else:
            self.metrics['model_cascade']['complex_count'] += 1

    def record_cascade_savings(self, savings: float):
        """Record cost savings from cascade"""
        self.metrics['costs']['cascade_savings'] += savings

    def record_error(self, component: str, error: str):
        """Record system error"""
        self.metrics['health']['errors'] += 1
        self.metrics['health']['by_component'][component] += 1

        self.recent_events.append({
            'type': 'error',
            'component': component,
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        })

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        # Calculate rates
        hallucination_rate = 0.0
        if self.metrics['hallucinations']['total'] > 0:
            hallucination_rate = (
                self.metrics['hallucinations']['caught'] /
                self.metrics['hallucinations']['total']
            ) * 100

        consensus_success_rate = 0.0
        if self.metrics['consensus']['total_attempts'] > 0:
            consensus_success_rate = (
                self.metrics['consensus']['consensus_reached'] /
                self.metrics['consensus']['total_attempts']
            ) * 100

        accuracy_rate = 0.0
        if self.metrics['accuracy']['total_predictions'] > 0:
            accuracy_rate = (
                self.metrics['accuracy']['correct_predictions'] /
                self.metrics['accuracy']['total_predictions']
            ) * 100

        # Calculate average response times
        avg_response_times = {}
        for agent, times in self.metrics['response_times']['by_agent'].items():
            if times:
                avg_response_times[agent] = sum(times) / len(times)

        # Session duration
        session_duration = (datetime.now() - self.session_start).total_seconds()

        return {
            'session': {
                'start_time': self.session_start.isoformat(),
                'duration_seconds': session_duration,
                'duration_formatted': self._format_duration(session_duration)
            },

            'hallucinations': {
                'total': self.metrics['hallucinations']['total'],
                'caught': self.metrics['hallucinations']['caught'],
                'missed': self.metrics['hallucinations']['missed'],
                'catch_rate_pct': hallucination_rate,
                'by_model': dict(self.metrics['hallucinations']['by_model'])
            },

            'consensus': {
                'total_attempts': self.metrics['consensus']['total_attempts'],
                'reached': self.metrics['consensus']['consensus_reached'],
                'failed': self.metrics['consensus']['consensus_failed'],
                'success_rate_pct': consensus_success_rate
            },

            'costs': {
                'total': round(self.metrics['costs']['total'], 4),
                'cascade_savings': round(self.metrics['costs']['cascade_savings'], 4),
                'by_agent': {k: round(v, 4) for k, v in self.metrics['costs']['by_agent'].items()},
                'by_model': {k: round(v, 4) for k, v in self.metrics['costs']['by_model'].items()}
            },

            'response_times': {
                'avg_by_agent': {k: round(v, 3) for k, v in avg_response_times.items()}
            },

            'accuracy': {
                'total_predictions': self.metrics['accuracy']['total_predictions'],
                'correct': self.metrics['accuracy']['correct_predictions'],
                'accuracy_rate_pct': accuracy_rate
            },

            'safety': {
                **self.metrics['safety'],
                'by_violation_type': dict(self.metrics['safety']['by_violation_type'])
            },

            'model_cascade': {
                **self.metrics['model_cascade'],
                'distribution': self._get_cascade_distribution()
            },

            'health': {
                'errors': self.metrics['health']['errors'],
                'warnings': self.metrics['health']['warnings'],
                'by_component': dict(self.metrics['health']['by_component'])
            }
        }

    def _get_cascade_distribution(self) -> Dict[str, float]:
        """Calculate model cascade distribution"""
        total = self.metrics['model_cascade']['total_queries']

        if total == 0:
            return {'simple': 0, 'moderate': 0, 'complex': 0}

        return {
            'simple': round((self.metrics['model_cascade']['simple_count'] / total) * 100, 1),
            'moderate': round((self.metrics['model_cascade']['moderate_count'] / total) * 100, 1),
            'complex': round((self.metrics['model_cascade']['complex_count'] / total) * 100, 1)
        }

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def print_dashboard(self):
        """Print metrics dashboard"""
        summary = self.get_summary()

        print("\n" + "="*70)
        print("TRADING SYSTEM METRICS DASHBOARD")
        print("="*70)

        # Session info
        print(f"\n📊 SESSION")
        print(f"  Start Time:  {summary['session']['start_time']}")
        print(f"  Duration:    {summary['session']['duration_formatted']}")

        # Hallucinations
        print(f"\n🔍 HALLUCINATION DETECTION")
        print(f"  Total:       {summary['hallucinations']['total']}")
        print(f"  Caught:      {summary['hallucinations']['caught']}")
        print(f"  Missed:      {summary['hallucinations']['missed']}")
        print(f"  Catch Rate:  {summary['hallucinations']['catch_rate_pct']:.1f}%")

        # Consensus
        print(f"\n🤝 CONSENSUS")
        print(f"  Attempts:    {summary['consensus']['total_attempts']}")
        print(f"  Reached:     {summary['consensus']['reached']}")
        print(f"  Failed:      {summary['consensus']['failed']}")
        print(f"  Success Rate: {summary['consensus']['success_rate_pct']:.1f}%")

        # Costs
        print(f"\n💰 COSTS")
        print(f"  Total Cost:         ${summary['costs']['total']:.4f}")
        print(f"  Cascade Savings:    ${summary['costs']['cascade_savings']:.4f}")
        if summary['costs']['by_agent']:
            print(f"  Top Agent Costs:")
            for agent, cost in sorted(summary['costs']['by_agent'].items(), key=lambda x: -x[1])[:3]:
                print(f"    {agent}: ${cost:.4f}")

        # Accuracy
        if summary['accuracy']['total_predictions'] > 0:
            print(f"\n🎯 ACCURACY")
            print(f"  Total Predictions:  {summary['accuracy']['total_predictions']}")
            print(f"  Correct:            {summary['accuracy']['correct']}")
            print(f"  Accuracy Rate:      {summary['accuracy']['accuracy_rate_pct']:.1f}%")

        # Safety
        print(f"\n🛡️  SAFETY")
        print(f"  Violations:         {summary['safety']['violations']}")
        print(f"  Trades Blocked:     {summary['safety']['trades_blocked']}")
        print(f"  Kill Switch Triggers: {summary['safety']['kill_switch_triggers']}")

        # Model Cascade
        if summary['model_cascade']['total_queries'] > 0:
            print(f"\n⚡ MODEL CASCADE")
            dist = summary['model_cascade']['distribution']
            print(f"  Simple:   {dist['simple']:.1f}%")
            print(f"  Moderate: {dist['moderate']:.1f}%")
            print(f"  Complex:  {dist['complex']:.1f}%")

        # Health
        print(f"\n🏥 SYSTEM HEALTH")
        print(f"  Errors:   {summary['health']['errors']}")
        print(f"  Warnings: {summary['health']['warnings']}")

        print("="*70 + "\n")

    def save_metrics(self, filepath: Optional[str] = None):
        """Save metrics to file"""
        if filepath is None and self.persist_path:
            filepath = self.persist_path / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        if filepath:
            with open(filepath, 'w') as f:
                json.dump(self.get_summary(), f, indent=2)

            self.logger.info(f"Metrics saved to {filepath}")


class AnalysisTimer:
    """Context manager for timing analysis"""

    def __init__(self, metrics_collector: MetricsCollector, agent_name: str):
        self.metrics = metrics_collector
        self.agent_name = agent_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.metrics.record_response_time(self.agent_name, duration)
