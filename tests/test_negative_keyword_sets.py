"""
TASK-027: Tests for Shared Negative Keyword Sets
"""

import unittest
from unittest.mock import MagicMock, patch
from src.tools.negative_keywords import (
    create_shared_negative_set,
    add_keywords_to_shared_set,
    attach_shared_set_to_campaign,
    apply_universal_negative_keywords_to_campaign,
)


class TestNegativeKeywordSets(unittest.TestCase):
    @patch("src.tools.negative_keywords.attach_shared_set_to_campaign")
    @patch("src.tools.negative_keywords.add_keywords_to_shared_set")
    @patch("src.tools.negative_keywords.create_shared_negative_set")
    @patch("src.tools.negative_keywords.get_google_ads_client")
    def test_apply_universal_negative_keywords_to_campaign_set_exists(
        self,
        mock_get_google_ads_client,
        mock_create_shared_negative_set,
        mock_add_keywords_to_shared_set,
        mock_attach_shared_set_to_campaign,
    ):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_ga_service = mock_google_ads_client.get_service.return_value

        # Mock the search stream to return an existing shared set
        mock_row = MagicMock()
        mock_row.shared_set.resource_name = "existing_set"
        mock_batch = MagicMock()
        mock_batch.results = [mock_row]
        mock_ga_service.search_stream.return_value = [mock_batch]

        # Call the function
        apply_universal_negative_keywords_to_campaign("12345", "67890")

        # Assertions
        mock_create_shared_negative_set.assert_not_called()
        mock_add_keywords_to_shared_set.assert_not_called()
        mock_attach_shared_set_to_campaign.assert_called_once_with(
            "12345", "67890", "existing_set"
        )

    @patch("src.tools.negative_keywords.get_universal_negatives")
    @patch("src.tools.negative_keywords.attach_shared_set_to_campaign")
    @patch("src.tools.negative_keywords.add_keywords_to_shared_set")
    @patch("src.tools.negative_keywords.create_shared_negative_set")
    @patch("src.tools.negative_keywords.get_google_ads_client")
    def test_apply_universal_negative_keywords_to_campaign_set_does_not_exist(
        self,
        mock_get_google_ads_client,
        mock_create_shared_negative_set,
        mock_add_keywords_to_shared_set,
        mock_attach_shared_set_to_campaign,
        mock_get_universal_negatives,
    ):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_ga_service = mock_google_ads_client.get_service.return_value

        # Mock the search stream to return no results
        mock_ga_service.search_stream.return_value = []

        # Mock the create_shared_negative_set function
        mock_create_shared_negative_set.return_value = "new_set"
        mock_get_universal_negatives.return_value = ["kw1", "kw2"]

        # Call the function
        apply_universal_negative_keywords_to_campaign("12345", "67890")

        # Assertions
        mock_create_shared_negative_set.assert_called_once()
        mock_add_keywords_to_shared_set.assert_called_once_with(
            "12345", "new_set", ["kw1", "kw2"]
        )
        mock_attach_shared_set_to_campaign.assert_called_once_with(
            "12345", "67890", "new_set"
        )

    @patch("src.tools.negative_keywords.get_google_ads_client")
    def test_create_shared_negative_set(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_shared_set_service = mock_google_ads_client.get_service.return_value
        mock_response = MagicMock()
        mock_response.results[0].resource_name = "shared_set_resource_name"
        mock_shared_set_service.mutate_shared_sets.return_value = mock_response

        # Call the function
        resource_name = create_shared_negative_set("12345", "Test Set")

        # Assertions
        self.assertEqual(resource_name, "shared_set_resource_name")
        mock_shared_set_service.mutate_shared_sets.assert_called_once()

    @patch("src.tools.negative_keywords.get_google_ads_client")
    def test_add_keywords_to_shared_set(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_shared_criterion_service = (
            mock_google_ads_client.get_service.return_value
        )

        # Call the function
        add_keywords_to_shared_set(
            "12345", "shared_set_resource_name", ["kw1", "kw2"]
        )

        # Assertions
        mock_shared_criterion_service.mutate_shared_criteria.assert_called_once()

    @patch("src.tools.negative_keywords.get_google_ads_client")
    def test_attach_shared_set_to_campaign(self, mock_get_google_ads_client):
        # Mock the Google Ads client and its services
        mock_google_ads_client = MagicMock()
        mock_get_google_ads_client.return_value = mock_google_ads_client
        mock_campaign_shared_set_service = (
            mock_google_ads_client.get_service.return_value
        )

        # Call the function
        attach_shared_set_to_campaign("12345", "67890", "shared_set_resource_name")

        # Assertions
        mock_campaign_shared_set_service.mutate_campaign_shared_sets.assert_called_once()


if __name__ == "__main__":
    unittest.main()
