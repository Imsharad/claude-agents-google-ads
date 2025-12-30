# tests/test_golden_ratio_scaler.py

import pytest
from src.budget.golden_ratio_scaler import GoldenRatioScaler

# Constants for convenience
MICROS_IN_RUPEE = 1_000_000
MAX_BUDGET = 2000 * MICROS_IN_RUPEE
CIRCUIT_BREAKER = 2400 * MICROS_IN_RUPEE

@pytest.fixture
def scaler():
    """Provides a GoldenRatioScaler instance for tests."""
    return GoldenRatioScaler()

# Test cases for calculate_ltv_cac_ratio
@pytest.mark.parametrize(
    "conversions, total_spend_micros, avg_ltv, expected_ratio",
    [
        (10, 500 * MICROS_IN_RUPEE, 200, 4.0),  # LTV/CAC = 200 / (500/10) = 4.0
        (0, 500 * MICROS_IN_RUPEE, 200, 0.0),   # Zero conversions
        (5, 0, 200, float("inf")),              # Zero spend, non-zero conversions
        (20, 1000 * MICROS_IN_RUPEE, 150, 3.0), # LTV/CAC = 150 / (1000/20) = 3.0
    ],
)
def test_calculate_ltv_cac_ratio(scaler, conversions, total_spend_micros, avg_ltv, expected_ratio):
    assert scaler.calculate_ltv_cac_ratio(conversions, total_spend_micros, avg_ltv) == expected_ratio

# Test cases for get_scaling_factor
@pytest.mark.parametrize(
    "ltv_cac, expected_factor",
    [
        (0.5, 0.0),    # PAUSE
        (0.99, 0.0),   # PAUSE
        (1.0, 1.0),    # MAINTAIN
        (2.5, 1.0),    # MAINTAIN
        (2.99, 1.0),   # MAINTAIN
        (3.0, 1.618),  # SCALE
        (3.5, 1.618),  # SCALE
        (3.99, 1.618), # SCALE
        (4.0, 2.618),  # AGGRESSIVE SCALE
        (10.0, 2.618), # AGGRESSIVE SCALE
    ],
)
def test_get_scaling_factor(scaler, ltv_cac, expected_factor):
    assert scaler.get_scaling_factor(ltv_cac) == expected_factor

# Test cases for calculate_new_budget
def test_calculate_new_budget_pause(scaler):
    """Test if budget is set to 0 when LTV:CAC < 1.0."""
    assert scaler.calculate_new_budget(1000 * MICROS_IN_RUPEE, 0.8) == 0

def test_calculate_new_budget_maintain(scaler):
    """Test if budget is maintained when 1.0 <= LTV:CAC < 3.0."""
    current_budget = 1000 * MICROS_IN_RUPEE
    # With a scaling factor of 1.0, the budget should not change.
    assert scaler.calculate_new_budget(current_budget, 2.5) == current_budget

def test_calculate_new_budget_gradual_scale_up(scaler):
    """Test the 20% cap on budget increase for golden ratio scaling."""
    current_budget = 1000 * MICROS_IN_RUPEE
    # Target would be 1618, but that's a 61.8% increase.
    # It should be capped at 20% increase, which is 1200.
    expected_budget = 1200 * MICROS_IN_RUPEE
    assert scaler.calculate_new_budget(current_budget, 3.5) == expected_budget

def test_calculate_new_budget_gradual_aggressive_scale_up(scaler):
    """Test the 20% cap on budget increase for aggressive scaling."""
    current_budget = 1000 * MICROS_IN_RUPEE
    # Target would be 2618, but that's a 161.8% increase.
    # It should be capped at 20% increase, which is 1200.
    expected_budget = 1200 * MICROS_IN_RUPEE
    assert scaler.calculate_new_budget(current_budget, 4.5) == expected_budget

def test_calculate_new_budget_circuit_breaker_triggered(scaler):
    """Test that the budget is capped at MAX_BUDGET when the target exceeds the circuit breaker."""
    # Current budget is high, so a 20% increase will go over the circuit breaker
    current_budget = 2100 * MICROS_IN_RUPEE
    # 20% increase would be 2100 * 1.2 = 2520, which is > CIRCUIT_BREAKER (2400)
    # The budget should be capped at MAX_BUDGET (2000)
    assert scaler.calculate_new_budget(current_budget, 4.5) == MAX_BUDGET

def test_calculate_new_budget_max_budget_cap(scaler):
    """Test that the budget is capped at MAX_BUDGET when the target is between MAX and CIRCUIT_BREAKER."""
    current_budget = 1800 * MICROS_IN_RUPEE
    # 20% increase is 1800 * 1.2 = 2160.
    # This is > MAX_BUDGET (2000) but < CIRCUIT_BREAKER (2400).
    # The budget should be capped at MAX_BUDGET (2000).
    assert scaler.calculate_new_budget(current_budget, 4.5) == MAX_BUDGET

def test_calculate_new_budget_no_change(scaler):
    """Test budget calculation when no change is needed."""
    current_budget = 1500 * MICROS_IN_RUPEE
    assert scaler.calculate_new_budget(current_budget, 1.5) == current_budget

def test_decrease_logic_is_not_triggered(scaler):
    """
    This test confirms that the current implementation's decrease logic is never
    triggered because the only scaling factor < 1 is 0.0 (PAUSE), which returns
    immediately.
    """
    current_budget = 1000 * MICROS_IN_RUPEE
    # With LTV:CAC < 1, scaling factor is 0, so budget becomes 0 immediately.
    assert scaler.calculate_new_budget(current_budget, 0.5) == 0

    # There's no LTV:CAC that results in a scaling factor between 0 and 1,
    # so the gradual decrease path is never taken.
