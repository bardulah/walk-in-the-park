"""Tests for FinancialGuardrails"""
import pytest
from datetime import datetime, timedelta
from utils.guardrails import FinancialGuardrails, ValidationError


class MockDataProvider:
    """Mock data provider for testing"""

    def get_price(self, ticker):
        return 150.0

    def get_market_cap(self, ticker):
        return 2_500_000_000_000  # $2.5T

    def get_volume(self, ticker):
        return 50_000_000

    def get_pe_ratio(self, ticker):
        return 28.5


class TestValidationError:
    """Test ValidationError class"""

    def test_validation_error_creation(self):
        """Test ValidationError creation"""
        error = ValidationError(
            field='current_price',
            claimed_value=155.0,
            actual_value=150.0,
            error_type='price_mismatch',
            severity='error'
        )

        assert error.field == 'current_price'
        assert error.claimed_value == 155.0
        assert error.actual_value == 150.0
        assert error.severity == 'error'

    def test_validation_error_to_dict(self):
        """Test ValidationError to_dict"""
        error = ValidationError(
            field='price',
            claimed_value=100,
            actual_value=90,
            error_type='mismatch',
            severity='warning'
        )

        error_dict = error.to_dict()

        assert error_dict['field'] == 'price'
        assert error_dict['claimed_value'] == 100
        assert error_dict['actual_value'] == 90
        assert error_dict['severity'] == 'warning'


class TestFinancialGuardrails:
    """Test FinancialGuardrails functionality"""

    def test_init(self):
        """Test guardrails initialization"""
        guardrails = FinancialGuardrails()

        assert guardrails.tolerances['price_pct'] == 0.05
        assert guardrails.tolerances['market_cap_pct'] == 0.10

    def test_init_with_custom_tolerances(self):
        """Test custom tolerance configuration"""
        custom_tolerances = {'price_pct': 0.10, 'market_cap_pct': 0.20}
        guardrails = FinancialGuardrails(tolerance_config=custom_tolerances)

        assert guardrails.tolerances['price_pct'] == 0.10
        assert guardrails.tolerances['market_cap_pct'] == 0.20

    def test_validate_price_within_tolerance(self):
        """Test price validation within tolerance"""
        provider = MockDataProvider()
        guardrails = FinancialGuardrails(data_provider=provider)

        analysis = {'current_price': 152.0}  # Within 5% of 150

        is_valid, errors = guardrails.validate_analysis('AAPL', analysis)

        assert is_valid
        assert len(errors) == 0

    def test_validate_price_outside_tolerance(self):
        """Test price validation outside tolerance"""
        provider = MockDataProvider()
        guardrails = FinancialGuardrails(data_provider=provider)

        analysis = {'current_price': 170.0}  # >5% difference from 150

        is_valid, errors = guardrails.validate_analysis('AAPL', analysis)

        assert not is_valid
        assert len(errors) > 0
        assert errors[0].field == 'current_price'
        assert errors[0].severity == 'error'

    def test_validate_recommendation_valid(self):
        """Test valid recommendation"""
        guardrails = FinancialGuardrails()

        analysis = {'recommendation': 'buy'}

        is_valid, errors = guardrails.validate_analysis('AAPL', analysis)

        assert is_valid

    def test_validate_recommendation_invalid(self):
        """Test invalid recommendation"""
        guardrails = FinancialGuardrails()

        analysis = {'recommendation': 'maybe_buy'}  # Invalid

        is_valid, errors = guardrails.validate_analysis('AAPL', analysis, strict_mode=True)

        # In non-strict mode, invalid recommendation is a warning
        assert not is_valid  # strict mode
        assert any(e.field == 'recommendation' for e in errors)

    def test_validate_date_future(self):
        """Test future date validation"""
        guardrails = FinancialGuardrails()

        future_date = (datetime.now() + timedelta(days=1)).isoformat()
        analysis = {'analysis_date': future_date}

        is_valid, errors = guardrails.validate_analysis('AAPL', analysis)

        assert not is_valid
        assert any(e.error_type == 'future_date' for e in errors)

    def test_validate_date_stale(self):
        """Test stale date validation"""
        guardrails = FinancialGuardrails()

        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        analysis = {'analysis_date': old_date}

        is_valid, errors = guardrails.validate_analysis('AAPL', analysis, strict_mode=True)

        # Stale date is a warning
        assert not is_valid  # In strict mode
        assert any('stale_date' in e.error_type for e in errors)

    def test_validate_numerical_ranges_negative_price(self):
        """Test negative price validation"""
        guardrails = FinancialGuardrails()

        analysis = {'current_price': -50.0}  # Invalid negative price

        is_valid, errors = guardrails.validate_analysis('AAPL', analysis)

        assert not is_valid
        assert any(e.error_type == 'negative_value' for e in errors)

    def test_validate_numerical_ranges_percentage(self):
        """Test percentage range validation"""
        guardrails = FinancialGuardrails()

        analysis = {'confidence': 150}  # Invalid >100%

        is_valid, errors = guardrails.validate_analysis('AAPL', analysis)

        assert not is_valid
        assert any(e.error_type == 'out_of_range' for e in errors)

    def test_strict_mode_vs_normal_mode(self):
        """Test strict mode vs normal mode"""
        guardrails = FinancialGuardrails()

        # Analysis with warning-level issue
        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        analysis = {'analysis_date': old_date}

        # Normal mode: warnings don't fail validation
        is_valid_normal, _ = guardrails.validate_analysis('AAPL', analysis, strict_mode=False)
        assert is_valid_normal

        # Strict mode: warnings fail validation
        is_valid_strict, _ = guardrails.validate_analysis('AAPL', analysis, strict_mode=True)
        assert not is_valid_strict

    def test_get_validation_report(self):
        """Test validation report generation"""
        guardrails = FinancialGuardrails()

        errors = [
            ValidationError('price', 100, 90, 'mismatch', 'error'),
            ValidationError('volume', 1000, 900, 'mismatch', 'warning')
        ]

        report = guardrails.get_validation_report(errors)

        assert 'ERRORS' in report
        assert 'WARNINGS' in report
        assert '2 issues found' in report

    def test_get_validation_report_no_errors(self):
        """Test validation report with no errors"""
        guardrails = FinancialGuardrails()

        report = guardrails.get_validation_report([])

        assert 'All validations passed' in report
