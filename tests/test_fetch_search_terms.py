"""
TASK-021: Tests for fetch_search_terms MCP Tool
"""

import unittest
from unittest.mock import MagicMock, patch
from src.tools.fetch_search_terms import _fetch_search_terms


# Create a fake exception class to simplify testing
class FakeGoogleAdsException(Exception):
    def __init__(self, message=""):
        self.message = message


class TestFetchSearchTerms(unittest.TestCase):
    @patch("src.tools.fetch_search_terms.get_google_ads_client")
    def test_fetch_search_terms_success(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_ga_service = mock_google_ads_client.get_service.return_value
        # Mock the search stream to return sample data
        mock_row = MagicMock()
        mock_row.search_term_view.search_term = "test search term"
        mock_row.metrics.impressions = 100
        mock_row.metrics.clicks = 10
        mock_row.metrics.conversions = 1
        mock_row.metrics.cost_micros = 1000000
        mock_batch = MagicMock()
        mock_batch.results = [mock_row]
        mock_ga_service.search_stream.return_value = [mock_batch]
        # Call the function
        result = _fetch_search_terms("12345", "67890")
        # Assertions
        expected_result = {
            "search_terms": [
                {
                    "search_term": "test search term",
                    "impressions": 100,
                    "clicks": 10,
                    "conversions": 1,
                    "cost_micros": 1000000,
                }
            ]
        }
        self.assertEqual(result, expected_result)
        mock_ga_service.search_stream.assert_called_once()

    @patch(
        "src.tools.fetch_search_terms.GoogleAdsException", new=FakeGoogleAdsException
    )
    @patch("src.tools.fetch_search_terms.get_google_ads_client")
    def test_fetch_search_terms_google_ads_error(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_ga_service = mock_google_ads_client.get_service.return_value
        # Mock the search stream to raise a GoogleAdsException
        mock_ga_service.search_stream.side_effect = FakeGoogleAdsException(
            "Test API Error"
        )
        # Call the function
        result = _fetch_search_terms("12345", "67890")
        # Assertions
        expected_result = {
            "error": "Google Ads API failed with message: Test API Error"
        }
        self.assertEqual(result, expected_result)

    @patch("src.tools.fetch_search_terms.get_google_ads_client")
    def test_fetch_search_terms_generic_error(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_ga_service = mock_google_ads_client.get_service.return_value
        # Mock the search stream to raise a generic exception
        mock_ga_service.search_stream.side_effect = Exception("Generic Error")
        # Call the function
        result = _fetch_search_terms("12345", "67890")
        # Assertions
        expected_result = {"error": "An unexpected error occurred: Generic Error"}
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
