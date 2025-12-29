# TODO: Replace with Golden Ratio scaler (TASK-032)

MINIMUM_BUDGET = 10000
RUPEE_TO_MICROS = 1_000_000


class BudgetValidationError(ValueError):
    """Custom exception for budget validation errors."""

    pass


def validate_budget(budget: int) -> bool:
    """
    Validates the budget against the minimum threshold.

    Args:
        budget: The budget amount in rupees.

    Returns:
        True if the budget is valid.

    Raises:
        BudgetValidationError: If the budget is below the minimum threshold.
    """
    if budget < MINIMUM_BUDGET:
        raise BudgetValidationError(
            f"Provided budget {budget} is below the minimum required amount of {MINIMUM_BUDGET}."
        )
    return True


def calculate_daily_budget(total_budget: int, duration_days: int) -> int:
    """
    Calculates the daily budget in micros.

    Args:
        total_budget: The total budget in rupees.
        duration_days: The campaign duration in days.

    Returns:
        The daily budget in micros.
    """
    validate_budget(total_budget)
    if duration_days <= 0:
        raise ValueError("Duration must be a positive integer.")

    daily_budget_rupees = total_budget / duration_days
    return round(daily_budget_rupees * RUPEE_TO_MICROS)
