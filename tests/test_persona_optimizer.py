import unittest
from unittest.mock import MagicMock, patch

from src.optimization.persona_optimizer import PersonaOptimizer

class TestPersonaOptimizer(unittest.TestCase):

    def setUp(self):
        """Set up the test case."""
        self.mock_client = MagicMock()
        # Mock the get_google_ads_client function where it is used
        self.mock_get_client = patch('src.optimization.persona_optimizer.get_google_ads_client', return_value=self.mock_client).start()

        self.optimizer = PersonaOptimizer()
        self.customer_id = "1234567890"
        self.campaign_id = "9876543210"

    def tearDown(self):
        """Tear down the test case."""
        patch.stopall()

    def test_identify_losing_personas_by_cpa(self):
        """Test identifying losing personas based on high cost per conversion."""
        # Mock campaign details to return a target CPA
        self.optimizer._get_campaign_details = MagicMock(return_value={"target_cpa_micros": 10000000}) # 10 currency units
        # Mock performance data with one ad group having a high CPA
        mock_performance_data = [
            {"ad_group_id": "1", "cost_per_conversion": 15000000, "conversions": 2, "cost_micros": 30000000},
            {"ad_group_id": "2", "cost_per_conversion": 8000000, "conversions": 5, "cost_micros": 40000000},
        ]
        self.optimizer._get_ad_group_performance = MagicMock(return_value=mock_performance_data)

        losing_personas = self.optimizer.identify_losing_personas(self.customer_id, self.campaign_id)
        self.assertEqual(losing_personas, ["1"])

    def test_identify_losing_personas_by_spend(self):
        """Test identifying losing personas based on high spend with no conversions."""
        self.optimizer._get_campaign_details = MagicMock(return_value={"target_cpa_micros": 10000000})
        mock_performance_data = [
            {"ad_group_id": "1", "cost_per_conversion": 0, "conversions": 0, "cost_micros": 2500 * 1000000}, # > 2000 currency units
            {"ad_group_id": "2", "cost_per_conversion": 8000000, "conversions": 5, "cost_micros": 40000000},
        ]
        self.optimizer._get_ad_group_performance = MagicMock(return_value=mock_performance_data)

        losing_personas = self.optimizer.identify_losing_personas(self.customer_id, self.campaign_id)
        self.assertEqual(losing_personas, ["1"])


    def test_identify_winning_personas(self):
        """Test identifying winning personas."""
        self.optimizer._get_campaign_details = MagicMock(return_value={"target_cpa_micros": 10000000})
        mock_performance_data = [
            {"ad_group_id": "1", "cost_per_conversion": 15000000, "conversions": 2, "cost_micros": 30000000},
            {"ad_group_id": "2", "cost_per_conversion": 8000000, "conversions": 5, "cost_micros": 40000000}, # Winning
            {"ad_group_id": "3", "cost_per_conversion": 7000000, "conversions": 4, "cost_micros": 28000000}, # Not enough conversions
        ]
        self.optimizer._get_ad_group_performance = MagicMock(return_value=mock_performance_data)

        winning_personas = self.optimizer.identify_winning_personas(self.customer_id, self.campaign_id)
        self.assertEqual(winning_personas, ["2"])

    def test_pause_ad_group(self):
        """Test pausing an ad group."""
        ad_group_id = "1"
        mock_ad_group_service = self.mock_client.get_service.return_value
        mock_ad_group_service.ad_group_path.return_value = f"customers/{self.customer_id}/adGroups/{ad_group_id}"

        self.optimizer.pause_ad_group(self.customer_id, ad_group_id)

        mock_ad_group_service.ad_group_path.assert_called_once_with(self.customer_id, ad_group_id)
        mock_ad_group_service.mutate_ad_groups.assert_called_once()

    def test_increase_bids_manual_cpc(self):
        """Test increasing bids for Manual CPC strategy."""
        ad_group_id = "1"
        bidding_strategy_enum = self.mock_client.get_type.return_value.BiddingStrategyType
        self.optimizer._get_ad_group_details = MagicMock(return_value={"bidding_strategy_type": bidding_strategy_enum.MANUAL_CPC})

        # Mock the GoogleAdsService to simulate finding keywords
        mock_google_ads_service = self.mock_client.get_service.return_value
        mock_google_ads_service.search_stream.return_value = [MagicMock(results=[MagicMock(ad_group_criterion=MagicMock(resource_name="keyword1", cpc_bid_micros=100000))])]

        self.optimizer.increase_bids(self.customer_id, ad_group_id)

        # Check that the criterion service was called to mutate bids
        mock_ad_group_criterion_service = self.mock_client.get_service.return_value
        mock_ad_group_criterion_service.mutate_ad_group_criteria.assert_called_once()

    def test_increase_bids_maximize_clicks(self):
        """Test increasing bids for Maximize Clicks strategy."""
        ad_group_id = "1"
        campaign_id = "campaign1"
        current_bid_limit = 1000000  # 1 currency unit

        bidding_strategy_enum = self.mock_client.get_type.return_value.BiddingStrategyType
        self.optimizer._get_ad_group_details = MagicMock(return_value={
            "bidding_strategy_type": bidding_strategy_enum.MAXIMIZE_CLICKS,
            "campaign_id": campaign_id,
            "cpc_bid_limit_micros": current_bid_limit
        })

        mock_campaign_service = self.mock_client.get_service.return_value

        self.optimizer.increase_bids(self.customer_id, ad_group_id, 0.20)

        mock_campaign_service.mutate_campaigns.assert_called_once()

        called_args, called_kwargs = mock_campaign_service.mutate_campaigns.call_args
        sent_operations = called_kwargs['operations']
        self.assertEqual(len(sent_operations), 1)

        updated_campaign = sent_operations[0].update
        self.assertEqual(updated_campaign.maximize_clicks.cpc_bid_limit_micros, 1200000)

if __name__ == '__main__':
    unittest.main()
