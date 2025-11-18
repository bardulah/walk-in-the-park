"""
Financial Guardrails
Validates LLM outputs against authoritative data sources to prevent hallucinations
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from config.logging_config import get_logger


logger = get_logger("guardrails")


class ValidationError:
    """Represents a validation error found by guardrails"""

    def __init__(self, field: str, claimed_value: Any, actual_value: Any,
                 error_type: str, severity: str = "error"):
        self.field = field
        self.claimed_value = claimed_value
        self.actual_value = actual_value
        self.error_type = error_type
        self.severity = severity  # "error", "warning", "info"

    def __str__(self):
        return (f"{self.severity.upper()}: {self.field} - "
                f"claimed {self.claimed_value} vs actual {self.actual_value} "
                f"({self.error_type})")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'field': self.field,
            'claimed_value': self.claimed_value,
            'actual_value': self.actual_value,
            'error_type': self.error_type,
            'severity': self.severity
        }


class FinancialGuardrails:
    """
    Validates LLM analysis outputs against authoritative data sources

    This implements the "Layer 4: Guardrails & Verification" from research,
    which can catch 90%+ of verifiable errors before they cause impact.

    Usage:
        guardrails = FinancialGuardrails(data_provider)
        is_valid, errors = guardrails.validate_analysis(ticker, analysis)

        if not is_valid:
            # Handle validation failures
            logger.warning(f"Analysis failed validation: {errors}")
    """

    def __init__(self, data_provider=None, tolerance_config: Optional[Dict[str, float]] = None):
        """
        Initialize guardrails

        Args:
            data_provider: Market data provider (e.g., yfinance, Alpha Vantage)
            tolerance_config: Dict of tolerance thresholds for various metrics
        """
        self.data_provider = data_provider
        self.logger = logger

        # Default tolerance thresholds
        self.tolerances = {
            'price_pct': 0.05,  # 5% tolerance for price discrepancies
            'market_cap_pct': 0.10,  # 10% tolerance for market cap
            'volume_pct': 0.20,  # 20% tolerance for volume
            'pe_ratio_pct': 0.15,  # 15% tolerance for P/E ratio
            'date_days': 7,  # 7 days tolerance for analysis dates
        }

        # Override with custom tolerances
        if tolerance_config:
            self.tolerances.update(tolerance_config)

    def validate_analysis(self, ticker: str, analysis: Dict[str, Any],
                         strict_mode: bool = False) -> Tuple[bool, List[ValidationError]]:
        """
        Validate LLM analysis against authoritative data

        Args:
            ticker: Stock ticker symbol
            analysis: Analysis dict from LLM
            strict_mode: If True, warnings count as failures

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        # Validate current price
        if 'current_price' in analysis:
            price_errors = self._validate_price(ticker, analysis['current_price'])
            errors.extend(price_errors)

        # Validate market cap
        if 'market_cap' in analysis:
            mcap_errors = self._validate_market_cap(ticker, analysis['market_cap'])
            errors.extend(mcap_errors)

        # Validate volume
        if 'volume' in analysis or 'avg_volume' in analysis:
            volume_errors = self._validate_volume(ticker, analysis)
            errors.extend(volume_errors)

        # Validate P/E ratio
        if 'pe_ratio' in analysis or 'p_e_ratio' in analysis:
            pe_value = analysis.get('pe_ratio') or analysis.get('p_e_ratio')
            pe_errors = self._validate_pe_ratio(ticker, pe_value)
            errors.extend(pe_errors)

        # Validate dates
        if 'analysis_date' in analysis:
            date_errors = self._validate_date(analysis['analysis_date'])
            errors.extend(date_errors)

        # Validate recommendation format
        if 'recommendation' in analysis:
            rec_errors = self._validate_recommendation(analysis['recommendation'])
            errors.extend(rec_errors)

        # Validate numerical ranges
        range_errors = self._validate_numerical_ranges(analysis)
        errors.extend(range_errors)

        # Determine if valid
        if strict_mode:
            is_valid = len(errors) == 0
        else:
            # Only count errors, not warnings
            error_count = sum(1 for e in errors if e.severity == 'error')
            is_valid = error_count == 0

        if not is_valid:
            self.logger.warning(
                f"Validation failed for {ticker}: {len(errors)} issues found"
            )
            for error in errors:
                self.logger.debug(str(error))
        else:
            self.logger.debug(f"Validation passed for {ticker}")

        return is_valid, errors

    def _validate_price(self, ticker: str, claimed_price: float) -> List[ValidationError]:
        """Validate current price"""
        errors = []

        if self.data_provider is None:
            self.logger.debug("No data provider - skipping price validation")
            return errors

        try:
            actual_price = self._get_current_price(ticker)

            if actual_price is None:
                errors.append(ValidationError(
                    field='current_price',
                    claimed_value=claimed_price,
                    actual_value=None,
                    error_type='data_unavailable',
                    severity='warning'
                ))
                return errors

            # Calculate percentage difference
            pct_diff = abs(claimed_price - actual_price) / actual_price

            if pct_diff > self.tolerances['price_pct']:
                errors.append(ValidationError(
                    field='current_price',
                    claimed_value=claimed_price,
                    actual_value=actual_price,
                    error_type=f'price_mismatch_{pct_diff*100:.1f}%',
                    severity='error'
                ))

        except Exception as e:
            self.logger.error(f"Price validation failed: {e}")
            errors.append(ValidationError(
                field='current_price',
                claimed_value=claimed_price,
                actual_value=None,
                error_type=f'validation_error_{str(e)}',
                severity='warning'
            ))

        return errors

    def _validate_market_cap(self, ticker: str, claimed_mcap: float) -> List[ValidationError]:
        """Validate market capitalization"""
        errors = []

        if self.data_provider is None:
            return errors

        try:
            actual_mcap = self._get_market_cap(ticker)

            if actual_mcap is None:
                return errors

            pct_diff = abs(claimed_mcap - actual_mcap) / actual_mcap

            if pct_diff > self.tolerances['market_cap_pct']:
                errors.append(ValidationError(
                    field='market_cap',
                    claimed_value=claimed_mcap,
                    actual_value=actual_mcap,
                    error_type=f'market_cap_mismatch_{pct_diff*100:.1f}%',
                    severity='error'
                ))

        except Exception as e:
            self.logger.error(f"Market cap validation failed: {e}")

        return errors

    def _validate_volume(self, ticker: str, analysis: Dict[str, Any]) -> List[ValidationError]:
        """Validate trading volume"""
        errors = []

        if self.data_provider is None:
            return errors

        volume_field = 'volume' if 'volume' in analysis else 'avg_volume'
        claimed_volume = analysis.get(volume_field)

        if claimed_volume is None:
            return errors

        try:
            actual_volume = self._get_volume(ticker)

            if actual_volume is None:
                return errors

            pct_diff = abs(claimed_volume - actual_volume) / actual_volume

            if pct_diff > self.tolerances['volume_pct']:
                severity = 'warning' if pct_diff < 0.5 else 'error'
                errors.append(ValidationError(
                    field=volume_field,
                    claimed_value=claimed_volume,
                    actual_value=actual_volume,
                    error_type=f'volume_mismatch_{pct_diff*100:.1f}%',
                    severity=severity
                ))

        except Exception as e:
            self.logger.error(f"Volume validation failed: {e}")

        return errors

    def _validate_pe_ratio(self, ticker: str, claimed_pe: float) -> List[ValidationError]:
        """Validate P/E ratio"""
        errors = []

        if self.data_provider is None:
            return errors

        try:
            actual_pe = self._get_pe_ratio(ticker)

            if actual_pe is None:
                return errors

            pct_diff = abs(claimed_pe - actual_pe) / actual_pe

            if pct_diff > self.tolerances['pe_ratio_pct']:
                errors.append(ValidationError(
                    field='pe_ratio',
                    claimed_value=claimed_pe,
                    actual_value=actual_pe,
                    error_type=f'pe_ratio_mismatch_{pct_diff*100:.1f}%',
                    severity='warning'  # P/E can vary by calculation method
                ))

        except Exception as e:
            self.logger.error(f"P/E ratio validation failed: {e}")

        return errors

    def _validate_date(self, analysis_date: str) -> List[ValidationError]:
        """Validate analysis date is reasonable"""
        errors = []

        try:
            # Parse date (handle multiple formats)
            if isinstance(analysis_date, str):
                # Try ISO format first
                try:
                    date_obj = datetime.fromisoformat(analysis_date.replace('Z', '+00:00'))
                except ValueError:
                    # Try other common formats
                    from dateutil import parser
                    date_obj = parser.parse(analysis_date)
            else:
                date_obj = analysis_date

            now = datetime.now()

            # Check if date is in the future
            if date_obj > now:
                errors.append(ValidationError(
                    field='analysis_date',
                    claimed_value=analysis_date,
                    actual_value=now.isoformat(),
                    error_type='future_date',
                    severity='error'
                ))

            # Check if date is too old
            elif (now - date_obj) > timedelta(days=self.tolerances['date_days']):
                errors.append(ValidationError(
                    field='analysis_date',
                    claimed_value=analysis_date,
                    actual_value=now.isoformat(),
                    error_type='stale_date',
                    severity='warning'
                ))

        except Exception as e:
            errors.append(ValidationError(
                field='analysis_date',
                claimed_value=analysis_date,
                actual_value=None,
                error_type=f'invalid_date_format_{str(e)}',
                severity='warning'
            ))

        return errors

    def _validate_recommendation(self, recommendation: str) -> List[ValidationError]:
        """Validate recommendation format"""
        errors = []

        valid_recommendations = {
            'strong_buy', 'buy', 'hold', 'sell', 'strong_sell',
            'bullish', 'bearish', 'neutral',
            'accumulate', 'reduce', 'avoid'
        }

        if isinstance(recommendation, str):
            rec_lower = recommendation.lower().replace(' ', '_')

            if rec_lower not in valid_recommendations:
                errors.append(ValidationError(
                    field='recommendation',
                    claimed_value=recommendation,
                    actual_value=list(valid_recommendations),
                    error_type='invalid_recommendation',
                    severity='warning'
                ))

        return errors

    def _validate_numerical_ranges(self, analysis: Dict[str, Any]) -> List[ValidationError]:
        """Validate numerical values are in reasonable ranges"""
        errors = []

        # Validate percentages (should be 0-100 or 0-1 depending on context)
        percentage_fields = [
            'confidence', 'conviction_level', 'probability',
            'upside_potential_pct', 'downside_risk_pct'
        ]

        for field in percentage_fields:
            if field in analysis:
                value = analysis[field]

                if isinstance(value, (int, float)):
                    # Check if it's a probability (0-1) or percentage (0-100)
                    if value < 0 or value > 100:
                        errors.append(ValidationError(
                            field=field,
                            claimed_value=value,
                            actual_value='0-100',
                            error_type='out_of_range',
                            severity='error'
                        ))

        # Validate positive-only fields
        positive_fields = [
            'price', 'current_price', 'target_price',
            'market_cap', 'volume', 'shares_outstanding'
        ]

        for field in positive_fields:
            if field in analysis:
                value = analysis[field]

                if isinstance(value, (int, float)) and value <= 0:
                    errors.append(ValidationError(
                        field=field,
                        claimed_value=value,
                        actual_value='>0',
                        error_type='negative_value',
                        severity='error'
                    ))

        return errors

    # Data provider interface methods
    # These should be implemented based on your actual data provider

    def _get_current_price(self, ticker: str) -> Optional[float]:
        """Get current price from data provider"""
        if self.data_provider is None:
            return None

        try:
            if hasattr(self.data_provider, 'get_price'):
                return self.data_provider.get_price(ticker)
            elif hasattr(self.data_provider, 'get_quote'):
                quote = self.data_provider.get_quote(ticker)
                return quote.get('price') or quote.get('last')
            else:
                self.logger.warning("Data provider has no get_price or get_quote method")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get price for {ticker}: {e}")
            return None

    def _get_market_cap(self, ticker: str) -> Optional[float]:
        """Get market cap from data provider"""
        if self.data_provider is None:
            return None

        try:
            if hasattr(self.data_provider, 'get_market_cap'):
                return self.data_provider.get_market_cap(ticker)
            elif hasattr(self.data_provider, 'get_info'):
                info = self.data_provider.get_info(ticker)
                return info.get('marketCap')
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to get market cap for {ticker}: {e}")
            return None

    def _get_volume(self, ticker: str) -> Optional[float]:
        """Get volume from data provider"""
        if self.data_provider is None:
            return None

        try:
            if hasattr(self.data_provider, 'get_volume'):
                return self.data_provider.get_volume(ticker)
            elif hasattr(self.data_provider, 'get_quote'):
                quote = self.data_provider.get_quote(ticker)
                return quote.get('volume')
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to get volume for {ticker}: {e}")
            return None

    def _get_pe_ratio(self, ticker: str) -> Optional[float]:
        """Get P/E ratio from data provider"""
        if self.data_provider is None:
            return None

        try:
            if hasattr(self.data_provider, 'get_pe_ratio'):
                return self.data_provider.get_pe_ratio(ticker)
            elif hasattr(self.data_provider, 'get_info'):
                info = self.data_provider.get_info(ticker)
                return info.get('trailingPE') or info.get('forwardPE')
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to get P/E ratio for {ticker}: {e}")
            return None

    def validate_batch(self, analyses: List[Tuple[str, Dict[str, Any]]],
                      strict_mode: bool = False) -> Dict[str, Tuple[bool, List[ValidationError]]]:
        """
        Validate multiple analyses in batch

        Args:
            analyses: List of (ticker, analysis) tuples
            strict_mode: If True, warnings count as failures

        Returns:
            Dict mapping ticker to (is_valid, errors) tuples
        """
        results = {}

        for ticker, analysis in analyses:
            is_valid, errors = self.validate_analysis(ticker, analysis, strict_mode)
            results[ticker] = (is_valid, errors)

        return results

    def get_validation_report(self, errors: List[ValidationError]) -> str:
        """
        Generate human-readable validation report

        Args:
            errors: List of validation errors

        Returns:
            Formatted report string
        """
        if not errors:
            return "✅ All validations passed"

        report_parts = [
            f"\n⚠️  Validation Report: {len(errors)} issues found\n",
            "=" * 60 + "\n"
        ]

        # Group by severity
        errors_by_severity = {}
        for error in errors:
            severity = error.severity
            if severity not in errors_by_severity:
                errors_by_severity[severity] = []
            errors_by_severity[severity].append(error)

        # Report errors first, then warnings
        for severity in ['error', 'warning', 'info']:
            if severity in errors_by_severity:
                report_parts.append(f"\n{severity.upper()}S ({len(errors_by_severity[severity])}):\n")

                for error in errors_by_severity[severity]:
                    report_parts.append(f"  • {error}\n")

        return "".join(report_parts)
