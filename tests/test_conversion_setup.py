"""
TASK-030: Tests for Conversion Tracking Setup Helper
"""

import unittest
from unittest.mock import MagicMock, patch, call
from src.tools.conversion_setup import check_conversion_setup, CheckConversionSetupInput


class TestConversionSetup(unittest.TestCase):
    @patch("src.tools.conversion_setup.get_google_ads_client")
    def test_check_conversion_setup_not_found(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_ga_service = mock_google_ads_client.get_service.return_value

        # Mock the search stream to return an empty iterator
        mock_ga_service.search_stream.return_value = iter([])

        # Call the function
        result = check_conversion_setup.handler(
            CheckConversionSetupInput(customer_id="12345")
        )

        # Assertions
        self.assertEqual(result["status"], "not_found")
        self.assertIn("No conversion actions found", result["message"])
        mock_ga_service.search_stream.assert_called_once()

    @patch("src.tools.conversion_setup.get_google_ads_client")
    def test_check_conversion_setup_inactive(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_ga_service = mock_google_ads_client.get_service.return_value

        # Mock the search stream responses
        # First call (any actions): return one result
        mock_row_any = MagicMock()
        mock_row_any.conversion_action.resource_name = "any_action"
        mock_batch_any = MagicMock()
        mock_batch_any.results = [mock_row_any]

        # Second call (active actions): return no results
        mock_ga_service.search_stream.side_effect = [
            iter([mock_batch_any]),
            iter([])
        ]

        # Call the function
        result = check_conversion_setup.handler(
            CheckConversionSetupInput(customer_id="12345")
        )

        # Assertions
        self.assertEqual(result["status"], "inactive")
        self.assertIn("no impressions have been recorded", result["message"])
        self.assertEqual(mock_ga_service.search_stream.call_count, 2)

    @patch("src.tools.conversion_setup.get_google_ads_client")
    def test_check_conversion_setup_active(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_ga_service = mock_google_ads_client.get_service.return_value

        # Mock the search stream responses
        # First call (any actions): return one result
        mock_row_any = MagicMock()
        mock_row_any.conversion_action.resource_name = "any_action"
        mock_batch_any = MagicMock()
        mock_batch_any.results = [mock_row_any]

        # Second call (active actions): return one result
        mock_row_active = MagicMock()
        mock_row_active.conversion_action.resource_name = "active_action_resource"
        mock_row_active.conversion_action.name = "Active Action"
        mock_batch_active = MagicMock()
        mock_batch_active.results = [mock_row_active]

        mock_ga_service.search_stream.side_effect = [
            iter([mock_batch_any]),
            iter([mock_batch_active])
        ]

        # Call the function
        result = check_conversion_setup.handler(
            CheckConversionSetupInput(customer_id="12345")
        )

        # Assertions
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["resource_name"], "active_action_resource")
        self.assertEqual(result["name"], "Active Action")
        self.assertIn("Conversion tracking is active", result["message"])
        self.assertEqual(mock_ga_service.search_stream.call_count, 2)


if __name__ == "__main__":
    unittest.main()
