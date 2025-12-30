# tests/test_spend_monitor.py

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.ads.googleads.errors import GoogleAdsException
from pydantic import ValidationError

from src.monitoring.spend_monitor import (
    TARGET_SPEND_MICROS,
    TOTAL_DAYS,
    DailySpend,
    PacingStatus,
    ShadowLedger,
    SpendMonitor,
)


@pytest.fixture
def temp_ledger_path(tmp_path: Path) -> Path:
    """Provides a temporary file path for the shadow ledger."""
    return tmp_path / "test_ledger.json"


@pytest.fixture
def shadow_ledger(temp_ledger_path: Path) -> ShadowLedger:
    """Returns an initialized ShadowLedger instance with a temporary path."""
    return ShadowLedger(ledger_path=temp_ledger_path)


@pytest.fixture
def mock_google_ads_client() -> MagicMock:
    """Provides a mock of the GoogleAdsClient."""
    mock_client = MagicMock()
    # Mock the service and the search method
    mock_service = mock_client.get_service.return_value
    mock_service.search.return_value = [
        MagicMock(metrics=MagicMock(cost_micros=1_000_000))
    ]
    return mock_client


@pytest.fixture
def spend_monitor(
    mock_google_ads_client: MagicMock, temp_ledger_path: Path
) -> SpendMonitor:
    """Returns an initialized SpendMonitor with a mock client and temp ledger."""
    return SpendMonitor(
        client=mock_google_ads_client,
        customer_id="1234567890",
        ledger_path=temp_ledger_path,
    )


class TestShadowLedger:
    """Tests for the ShadowLedger class."""

    def test_initialization_creates_file(self, temp_ledger_path: Path):
        """Test that a new ledger file is created if it doesn't exist."""
        assert not temp_ledger_path.exists()
        ShadowLedger(ledger_path=temp_ledger_path)
        assert temp_ledger_path.exists()
        assert temp_ledger_path.read_text() == "[]"

    def test_write_and_read_entry(self, shadow_ledger: ShadowLedger):
        """Test writing a single entry and reading it back."""
        entry = DailySpend(date="2023-01-01", spend_micros=50000)
        shadow_ledger.write_entry(entry)
        entries = shadow_ledger.read_entries()
        assert len(entries) == 1
        assert entries[0] == entry

    def test_write_multiple_entries_and_sorts(self, shadow_ledger: ShadowLedger):
        """Test that multiple entries are written and sorted by date."""
        entry1 = DailySpend(date="2023-01-02", spend_micros=100000)
        entry2 = DailySpend(date="2023-01-01", spend_micros=50000)
        shadow_ledger.write_entry(entry1)
        shadow_ledger.write_entry(entry2)
        entries = shadow_ledger.read_entries()
        assert len(entries) == 2
        assert entries[0].date == "2023-01-01"
        assert entries[1].date == "2023-01-02"

    def test_update_existing_entry(self, shadow_ledger: ShadowLedger):
        """Test that writing an entry for an existing date updates it."""
        entry1 = DailySpend(date="2023-01-01", spend_micros=50000)
        shadow_ledger.write_entry(entry1)
        entry2 = DailySpend(date="2023-01-01", spend_micros=60000)
        shadow_ledger.write_entry(entry2)
        entries = shadow_ledger.read_entries()
        assert len(entries) == 1
        assert entries[0].spend_micros == 60000

    def test_read_from_nonexistent_file(self, tmp_path: Path):
        """Test reading from a path that doesn't exist."""
        ledger = ShadowLedger(tmp_path / "nonexistent.json")
        assert ledger.read_entries() == []

    def test_read_from_corrupted_file(self, temp_ledger_path: Path):
        """Test reading from a file with invalid JSON."""
        temp_ledger_path.write_text("not json")
        ledger = ShadowLedger(temp_ledger_path)
        assert ledger.read_entries() == []


class TestSpendMonitor:
    """Tests for the SpendMonitor class."""

    @pytest.mark.parametrize(
        "current_spend, days_elapsed, expected_status",
        [
            # On track
            (TARGET_SPEND_MICROS / 2, TOTAL_DAYS / 2, PacingStatus.GREEN),
            # Ahead of schedule
            ((TARGET_SPEND_MICROS / 2) + 1, TOTAL_DAYS / 2, PacingStatus.GREEN),
            # Slightly behind but still GREEN
            (8_000_000_000, 30, PacingStatus.GREEN),
            # Exactly 20% behind, should be YELLOW
            (7_999_999_999, 30, PacingStatus.YELLOW),
            # Significantly behind, should be RED
            (4_900_000_000, 30, PacingStatus.RED),
            # Edge case: Day 0
            (0, 0, PacingStatus.GREEN),
            # Edge case: Day 1, no spend
            (0, 1, PacingStatus.RED),
        ],
    )
    def test_calculate_pacing(
        self,
        current_spend: int,
        days_elapsed: int,
        expected_status: PacingStatus,
    ):
        """Test the pacing calculation logic."""
        status = SpendMonitor.calculate_pacing(
            current_spend=current_spend,
            target=TARGET_SPEND_MICROS,
            days_elapsed=days_elapsed,
            total_days=TOTAL_DAYS,
        )
        assert status == expected_status

    def test_get_account_spend_success(self, spend_monitor: SpendMonitor):
        """Test successfully retrieving account spend."""
        start_date = "2023-01-01"
        spend = spend_monitor.get_account_spend(start_date)
        assert spend == 1_000_000
        # Verify it was written to the ledger
        today = datetime.now().strftime("%Y-%m-%d")
        entries = spend_monitor.ledger.read_entries()
        assert len(entries) == 1
        assert entries[0].date == today
        assert entries[0].spend_micros == 1_000_000
        # Verify the mock was called correctly
        spend_monitor.google_ads_service.search.assert_called_once()

    def test_get_account_spend_api_error(self, spend_monitor: SpendMonitor):
        """Test handling of a GoogleAdsException during spend retrieval."""
        spend_monitor.google_ads_service.search.side_effect = GoogleAdsException(
            error=None,
            call=None,
            request_id="test_id",
            failure=MagicMock(),
        )
        spend = spend_monitor.get_account_spend("2023-01-01")
        assert spend == 0

    def test_check_milestones_single(self, spend_monitor: SpendMonitor):
        """Test crossing a single milestone."""
        # Previous spend was below 5k
        spend_monitor.ledger.write_entry(
            DailySpend(date="2023-01-01", spend_micros=4_000_000_000)
        )
        # Current spend is above 5k
        current_spend = 5_100_000_000
        spend_monitor.ledger.write_entry(
            DailySpend(date="2023-01-02", spend_micros=current_spend)
        )
        milestones = spend_monitor.check_milestones(current_spend)
        assert milestones == ["5k"]

    def test_check_milestones_multiple(self, spend_monitor: SpendMonitor):
        """Test crossing multiple milestones at once."""
        spend_monitor.ledger.write_entry(
            DailySpend(date="2023-01-01", spend_micros=4_000_000_000)
        )
        current_spend = 10_500_000_000
        spend_monitor.ledger.write_entry(
            DailySpend(date="2023-01-02", spend_micros=current_spend)
        )
        milestones = spend_monitor.check_milestones(current_spend)
        assert "5k" in milestones
        assert "10k" in milestones

    def test_check_milestones_no_new_milestone(self, spend_monitor: SpendMonitor):
        """Test that no milestone is triggered if none was crossed."""
        spend_monitor.ledger.write_entry(
            DailySpend(date="2023-01-01", spend_micros=5_100_000_000)
        )
        current_spend = 5_200_000_000
        spend_monitor.ledger.write_entry(
            DailySpend(date="2023-01-02", spend_micros=current_spend)
        )
        milestones = spend_monitor.check_milestones(current_spend)
        assert milestones == []

    def test_check_milestones_no_prior_data(self, spend_monitor: SpendMonitor):
        """Test milestone check on the first spend record."""
        current_spend = 5_100_000_000
        # The first call to get_account_spend would write this.
        spend_monitor.ledger.write_entry(
            DailySpend(date="2023-01-01", spend_micros=current_spend)
        )
        milestones = spend_monitor.check_milestones(current_spend)
        # Assumes last spend was 0 because there's only one record.
        assert milestones == ["5k"]
