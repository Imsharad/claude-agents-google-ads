# src/budget/golden_ratio_scaler.py

import math

# Constants based on PRD Section 3.3.1
MAX_DAILY_BUDGET_MICROS = 2000 * 1_000_000
CIRCUIT_BREAKER_THRESHOLD_MICROS = 2400 * 1_000_000
MAX_DAILY_CHANGE_PERCENTAGE = 0.20

# LTV:CAC Decision Matrix Scaling Factors
MAINTAIN_FACTOR = 1.0
GOLDEN_RATIO_SCALE_UP = 1.618
AGGRESSIVE_SCALE_UP = 2.618
PAUSE_FACTOR = 0.0


class GoldenRatioScaler:
    """
    Implements the Golden Ratio budget scaling strategy based on LTV:CAC ratio.
    """

    @staticmethod
    def calculate_ltv_cac_ratio(
        conversions: int, total_spend_micros: int, avg_ltv: float
    ) -> float:
        """
        Calculates the Lifetime Value to Customer Acquisition Cost ratio.

        Args:
            conversions: The number of conversions.
            total_spend_micros: The total ad spend in micros.
            avg_ltv: The average Lifetime Value of a customer.

        Returns:
            The calculated LTV:CAC ratio. Returns 0.0 if conversions are zero.
        """
        if conversions == 0:
            return 0.0

        total_spend = total_spend_micros / 1_000_000
        cac = total_spend / conversions
        if cac == 0:
            return float("inf") # Avoid division by zero if spend is zero but conversions are not

        return avg_ltv / cac

    @staticmethod
    def get_scaling_factor(ltv_cac: float) -> float:
        """
        Determines the scaling factor based on the LTV:CAC ratio.

        Args:
            ltv_cac: The LTV to CAC ratio.

        Returns:
            The scaling factor.
        """
        if ltv_cac < 1.0:
            return PAUSE_FACTOR
        elif 1.0 <= ltv_cac < 3.0:
            return MAINTAIN_FACTOR
        elif 3.0 <= ltv_cac < 4.0:
            return GOLDEN_RATIO_SCALE_UP
        else:  # ltv_cac >= 4.0
            return AGGRESSIVE_SCALE_UP

    @staticmethod
    def calculate_new_budget(current_budget_micros: int, ltv_cac: float) -> int:
        """
        Calculates the new daily budget based on the LTV:CAC ratio,
        applying gradual scaling and circuit breaker rules.

        Args:
            current_budget_micros: The current daily budget in micros.
            ltv_cac: The LTV to CAC ratio.

        Returns:
            The new daily budget in micros.
        """
        scaling_factor = GoldenRatioScaler.get_scaling_factor(ltv_cac)

        if scaling_factor == PAUSE_FACTOR:
            return 0

        target_budget = current_budget_micros * scaling_factor

        # Gradual scaling: <20% change per day
        max_increase = current_budget_micros * MAX_DAILY_CHANGE_PERCENTAGE
        max_decrease = current_budget_micros * MAX_DAILY_CHANGE_PERCENTAGE

        if target_budget > current_budget_micros:
            increase = target_budget - current_budget_micros
            if increase > max_increase:
                target_budget = current_budget_micros + max_increase
        elif target_budget < current_budget_micros:
            decrease = current_budget_micros - target_budget
            if decrease > max_decrease:
                target_budget = current_budget_micros - max_decrease

        # Circuit breaker: Cap the new budget at the maximum daily limit.
        new_budget = min(target_budget, MAX_DAILY_BUDGET_MICROS)

        return math.ceil(new_budget)
