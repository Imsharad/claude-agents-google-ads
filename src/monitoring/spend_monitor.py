# src/monitoring/spend_monitor.py

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TARGET_SPEND_MICROS = 20000 * 1_000_000  # 20,000 INR in micros
TOTAL_DAYS = 60
MILESTONES_MICROS = {
    "5k": 5000 * 1_000_000,
    "10k": 10000 * 1_000_000,
    "15k": 15000 * 1_000_000,
    "20k": 20000 * 1_000_000,
}


class PacingStatus(Enum):
    """Enum for account spend pacing status."""

    GREEN = "GREEN"  # On track or ahead of schedule
    YELLOW = "YELLOW"  # Moderately behind schedule (e.g., >20% behind)
    RED = "RED"  # Significantly behind schedule (e.g., >50% behind or 2x)


class DailySpend(BaseModel):
    """Data model for a daily spend snapshot."""

    date: str = Field(..., description="The date of the spend record (YYYY-MM-DD).")
    spend_micros: int = Field(..., description="The total account spend in micros.")


class ShadowLedger:
    """Handles local tracking of spend data in a JSON file."""

    def __init__(self, ledger_path: Path):
        self.ledger_path = ledger_path
        if not self.ledger_path.exists():
            self.ledger_path.touch()
            self.ledger_path.write_text("[]")

    def read_entries(self) -> list[DailySpend]:
        """Reads all spend entries from the ledger."""
        try:
            with open(self.ledger_path, "r") as f:
                data = json.load(f)
            return [DailySpend(**entry) for entry in data]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def write_entry(self, spend_data: DailySpend):
        """Appends a new spend entry to the ledger."""
        entries = self.read_entries()
        # Avoid duplicate entries for the same day
        entries = [e for e in entries if e.date != spend_data.date]
        entries.append(spend_data)
        entries.sort(key=lambda e: e.date)
        with open(self.ledger_path, "w") as f:
            json.dump([e.model_dump() for e in entries], f, indent=2)


class SpendMonitor:
    """A class to monitor Google Ads account spend against a promotional target."""

    def __init__(
        self,
        client: GoogleAdsClient,
        customer_id: str,
        ledger_path: Optional[Path] = None,
    ):
        self.client = client
        self.customer_id = customer_id
        self.google_ads_service = self.client.get_service("GoogleAdsService")
        self.ledger = ShadowLedger(
            ledger_path
            if ledger_path
            else Path(f"spend_ledger_{self.customer_id}.json")
        )

    def get_account_spend(self, start_date: str) -> int:
        """
        Retrieves the total account spend from a given start date.

        Args:
            start_date: The start date in 'YYYY-MM-DD' format.

        Returns:
            The total spend in micros, or 0 if an error occurs.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        query = f"""
            SELECT metrics.cost_micros
            FROM customer
            WHERE segments.date BETWEEN '{start_date}' AND '{today}'
        """
        try:
            response = self.google_ads_service.search(
                customer_id=self.customer_id, query=query
            )
            # The query returns one row per day; sum them to get the total.
            total_spend = 0
            for row in response:
                total_spend += row.metrics.cost_micros

            logger.info(f"Total spend since {start_date}: {total_spend} micros.")

            # Record today's spend in the shadow ledger
            spend_entry = DailySpend(date=today, spend_micros=total_spend)
            self.ledger.write_entry(spend_entry)

            return total_spend
        except GoogleAdsException as ex:
            logger.error(f"Failed to retrieve account spend: {ex}")
            return 0

    @staticmethod
    def calculate_pacing(
        current_spend: int,
        target: int,
        days_elapsed: int,
        total_days: int,
    ) -> PacingStatus:
        """
        Calculates the pacing of the ad spend.

        Args:
            current_spend: The current total spend in micros.
            target: The target spend in micros.
            days_elapsed: The number of days that have passed.
            total_days: The total number of days for the promotional period.

        Returns:
            The PacingStatus (GREEN, YELLOW, or RED).
        """
        if days_elapsed == 0:
            return PacingStatus.GREEN

        expected_pace = (target / total_days) * days_elapsed
        actual_spend = current_spend

        if actual_spend >= expected_pace:
            return PacingStatus.GREEN

        # More than 50% behind schedule
        if actual_spend < expected_pace / 2:
            return PacingStatus.RED

        # More than 20% behind schedule
        if actual_spend < expected_pace * 0.8:
            return PacingStatus.YELLOW

        return PacingStatus.GREEN

    def check_milestones(self, current_spend: int) -> list[str]:
        """
        Checks if any spend milestones have been reached.

        Returns:
            A list of milestone keys that have been reached.
        """
        reached_milestones = []

        # Find the last recorded spend from the ledger to avoid re-notifying
        entries = self.ledger.read_entries()
        last_spend = entries[-2].spend_micros if len(entries) > 1 else 0

        for key, value in MILESTONES_MICROS.items():
            if last_spend < value <= current_spend:
                logger.info(f"Milestone reached: {key} ({value} micros)")
                reached_milestones.append(key)
        return reached_milestones
