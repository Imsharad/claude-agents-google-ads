"""
TASK-014: Static Budget Calculator Tests

These tests define the expected behavior for the budget calculator.
Tests are written BEFORE implementation (Test-Driven Development).

Note: This is a placeholder implementation that will be replaced by
TASK-032 (Golden Ratio Budget Scaler) in Phase 2.

Run with: pytest tests/test_budget_calculator.py -v

Note: Tests will be SKIPPED until TASK-014 implementation exists.
"""

import pytest

# Skip entire module if budget calculator doesn't exist yet (TDD pattern)
pytest.importorskip("src.budget.calculator", reason="TASK-014 not implemented")

from src.budget.calculator import (  # noqa: E402
    calculate_daily_budget,
    validate_budget,
    BudgetValidationError,
)


class TestDailyBudgetCalculation:
    """Test daily budget calculation from total budget and duration."""

    def test_calculate_daily_budget_standard_case(self):
        """Standard case: ₹20,000 over 30 days = ~₹666.67/day."""
        # Google Ads API uses micros (1 rupee = 1,000,000 micros)
        total_budget = 20000  # ₹20,000
        duration_days = 30

        daily_budget_micros = calculate_daily_budget(total_budget, duration_days)

        # ₹666.67 = 666,666,667 micros (rounded)
        expected_micros = 666_666_667
        # Allow small rounding difference
        assert abs(daily_budget_micros - expected_micros) < 1000

    def test_calculate_daily_budget_returns_integer(self):
        """Budget in micros should be an integer."""
        daily_budget = calculate_daily_budget(20000, 30)
        assert isinstance(daily_budget, int)

    def test_calculate_daily_budget_60_days(self):
        """60-day campaign: ₹20,000 / 60 = ₹333.33/day."""
        daily_budget_micros = calculate_daily_budget(20000, 60)

        # ₹333.33 = 333,333,333 micros
        expected_micros = 333_333_333
        assert abs(daily_budget_micros - expected_micros) < 1000

    def test_calculate_daily_budget_minimum_viable(self):
        """Minimum budget: ₹10,000 over 30 days = ₹333.33/day."""
        daily_budget_micros = calculate_daily_budget(10000, 30)

        # ₹333.33 = 333,333,333 micros
        expected_micros = 333_333_333
        assert abs(daily_budget_micros - expected_micros) < 1000

    def test_calculate_daily_budget_custom_duration(self):
        """Custom duration: ₹15,000 over 45 days."""
        daily_budget_micros = calculate_daily_budget(15000, 45)

        # ₹333.33 = 333,333,333 micros
        expected_micros = 333_333_333
        assert abs(daily_budget_micros - expected_micros) < 1000


class TestBudgetValidation:
    """Test budget validation rules."""

    def test_validate_budget_minimum_threshold(self):
        """Budget must be at least ₹10,000."""
        # Valid budget
        assert validate_budget(10000) is True
        assert validate_budget(20000) is True
        assert validate_budget(50000) is True

    def test_validate_budget_below_minimum_raises_error(self):
        """Budget below ₹10,000 should raise validation error."""
        with pytest.raises(BudgetValidationError) as exc_info:
            validate_budget(5000)

        assert "minimum" in str(exc_info.value).lower()

    def test_validate_budget_zero_raises_error(self):
        """Zero budget should raise validation error."""
        with pytest.raises(BudgetValidationError):
            validate_budget(0)

    def test_validate_budget_negative_raises_error(self):
        """Negative budget should raise validation error."""
        with pytest.raises(BudgetValidationError):
            validate_budget(-1000)


class TestDailyBudgetEdgeCases:
    """Test edge cases for budget calculation."""

    def test_calculate_daily_budget_one_day(self):
        """Single day campaign should return full budget."""
        daily_budget_micros = calculate_daily_budget(10000, 1)

        # ₹10,000 = 10,000,000,000 micros
        expected_micros = 10_000_000_000
        assert daily_budget_micros == expected_micros

    def test_calculate_daily_budget_zero_days_raises_error(self):
        """Zero duration days should raise error."""
        with pytest.raises((ValueError, ZeroDivisionError, BudgetValidationError)):
            calculate_daily_budget(20000, 0)

    def test_calculate_daily_budget_negative_days_raises_error(self):
        """Negative duration days should raise error."""
        with pytest.raises((ValueError, BudgetValidationError)):
            calculate_daily_budget(20000, -5)

    def test_calculate_daily_budget_below_minimum_raises_error(self):
        """Budget below minimum should raise error."""
        with pytest.raises(BudgetValidationError):
            calculate_daily_budget(5000, 30)


class TestMicrosConversion:
    """Test rupee to micros conversion accuracy."""

    def test_one_rupee_equals_million_micros(self):
        """1 rupee = 1,000,000 micros in Google Ads API."""
        # ₹1 for 1 day
        daily_budget_micros = calculate_daily_budget(1, 1)
        assert daily_budget_micros == 1_000_000

    def test_large_budget_conversion(self):
        """Large budget conversion should be accurate."""
        # ₹100,000 for 100 days = ₹1,000/day
        daily_budget_micros = calculate_daily_budget(100000, 100)

        # ₹1,000 = 1,000,000,000 micros
        expected_micros = 1_000_000_000
        assert daily_budget_micros == expected_micros


class TestBudgetValidationErrorMessage:
    """Test that validation errors have helpful messages."""

    def test_validation_error_includes_minimum_amount(self):
        """Error message should include the minimum required amount."""
        with pytest.raises(BudgetValidationError) as exc_info:
            validate_budget(5000)

        error_message = str(exc_info.value)
        assert "10000" in error_message or "10,000" in error_message

    def test_validation_error_includes_provided_amount(self):
        """Error message should include the amount that was provided."""
        with pytest.raises(BudgetValidationError) as exc_info:
            validate_budget(5000)

        error_message = str(exc_info.value)
        assert "5000" in error_message or "5,000" in error_message
