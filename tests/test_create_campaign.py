import pytest
from unittest.mock import MagicMock, patch, call

from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v22.services.services.campaign_budget_service import (
    CampaignBudgetServiceClient,
)
from google.ads.googleads.v22.services.services.campaign_service import (
    CampaignServiceClient,
)
from google.ads.googleads.v22.services.services.ad_group_service import (
    AdGroupServiceClient,
)

from src.models.persona import Persona
from src.tools.create_campaign import create_growth_tier_campaign

CUSTOMER_ID = "1234567890"


@pytest.fixture
def mock_google_ads_client():
    mock_client = MagicMock()

    mock_campaign_service = MagicMock(spec=CampaignServiceClient)
    mock_campaign_budget_service = MagicMock(spec=CampaignBudgetServiceClient)
    mock_ad_group_service = MagicMock(spec=AdGroupServiceClient)

    mock_client.get_service.side_effect = lambda service_name, version=None: {
        "CampaignService": mock_campaign_service,
        "CampaignBudgetService": mock_campaign_budget_service,
        "AdGroupService": mock_ad_group_service,
    }.get(service_name)

    # Store and return the same mock for the same type to allow for comparison
    type_mocks = {}
    def get_type_mock(name):
        if name not in type_mocks:
            type_mocks[name] = MagicMock()
        return type_mocks[name]

    mock_client.get_type.side_effect = get_type_mock

    # Mock the return value for mutate_campaign_budgets
    mock_campaign_budget_response = MagicMock()
    mock_campaign_budget_response.results[0].resource_name = "campaignBudgetResourceName"
    mock_campaign_budget_service.mutate_campaign_budgets.return_value = mock_campaign_budget_response

    # Mock the return value for mutate_campaigns
    mock_campaign_response = MagicMock()
    mock_campaign_response.results[0].resource_name = "campaignResourceName"
    mock_campaign_service.mutate_campaigns.return_value = mock_campaign_response

    # Mock the return value for mutate_ad_groups
    mock_ad_group_response = MagicMock()
    mock_ad_group_response.results[0].resource_name = "adGroupResourceName"
    mock_ad_group_service.mutate_ad_groups.return_value = mock_ad_group_response

    return mock_client


@patch("src.tools.create_campaign.get_google_ads_client")
def test_create_campaign_tripwire_upsell(mock_get_google_ads_client, mock_google_ads_client):
    mock_get_google_ads_client.return_value = mock_google_ads_client
    personas = [Persona(name="Test Persona", description="")]

    create_growth_tier_campaign(
        customer_id=CUSTOMER_ID,
        campaign_name="Test Campaign",
        budget_micros=1000000,
        monetization_model="TRIPWIRE_UPSELL",
        personas=personas,
        target_cpa_micros=10000,
    )

    campaign_service = mock_google_ads_client.get_service("CampaignService")
    campaign_operation = campaign_service.mutate_campaigns.call_args[1]["operations"][0]
    campaign = campaign_operation.create
    assert (
        campaign.bidding_strategy_type
        == mock_google_ads_client.get_type("BiddingStrategyTypeEnum").BiddingStrategyType.MAXIMIZE_CONVERSIONS
    )
    assert campaign.maximize_conversions.target_cpa_micros == 10000


@patch("src.tools.create_campaign.get_google_ads_client")
def test_create_campaign_direct_sale(mock_get_google_ads_client, mock_google_ads_client):
    mock_get_google_ads_client.return_value = mock_google_ads_client
    personas = [Persona(name="Test Persona", description="")]

    create_growth_tier_campaign(
        customer_id=CUSTOMER_ID,
        campaign_name="Test Campaign",
        budget_micros=1000000,
        monetization_model="DIRECT_SALE",
        personas=personas,
        target_roas=3.5,
    )

    campaign_service = mock_google_ads_client.get_service("CampaignService")
    campaign_operation = campaign_service.mutate_campaigns.call_args[1]["operations"][0]
    campaign = campaign_operation.create
    assert (
        campaign.bidding_strategy_type
        == mock_google_ads_client.get_type("BiddingStrategyTypeEnum").BiddingStrategyType.TARGET_ROAS
    )
    assert campaign.target_roas.target_roas == 3.5


@patch("src.tools.create_campaign.get_google_ads_client")
def test_create_campaign_lead_gen(mock_get_google_ads_client, mock_google_ads_client):
    mock_get_google_ads_client.return_value = mock_google_ads_client
    personas = [Persona(name="Test Persona", description="")]

    create_growth_tier_campaign(
        customer_id=CUSTOMER_ID,
        campaign_name="Test Campaign",
        budget_micros=1000000,
        monetization_model="LEAD_GEN",
        personas=personas,
        cpc_bid_cap_micros=50000,
    )

    campaign_service = mock_google_ads_client.get_service("CampaignService")
    campaign_operation = campaign_service.mutate_campaigns.call_args[1]["operations"][0]
    campaign = campaign_operation.create
    assert (
        campaign.bidding_strategy_type
        == mock_google_ads_client.get_type("BiddingStrategyTypeEnum").BiddingStrategyType.MAXIMIZE_CLICKS
    )
    assert campaign.maximize_clicks.cpc_bid_limit_micros == 50000


@patch("src.tools.create_campaign.get_google_ads_client")
def test_create_campaign_book_call(mock_get_google_ads_client, mock_google_ads_client):
    mock_get_google_ads_client.return_value = mock_google_ads_client
    personas = [Persona(name="Test Persona", description="")]

    create_growth_tier_campaign(
        customer_id=CUSTOMER_ID,
        campaign_name="Test Campaign",
        budget_micros=1000000,
        monetization_model="BOOK_CALL",
        personas=personas,
    )

    campaign_service = mock_google_ads_client.get_service("CampaignService")
    campaign_operation = campaign_service.mutate_campaigns.call_args[1]["operations"][0]
    campaign = campaign_operation.create
    assert (
        campaign.bidding_strategy_type
        == mock_google_ads_client.get_type("BiddingStrategyTypeEnum").BiddingStrategyType.MAXIMIZE_CONVERSIONS
    )


@patch("src.tools.create_campaign.get_google_ads_client")
def test_ad_group_creation(mock_get_google_ads_client, mock_google_ads_client):
    mock_get_google_ads_client.return_value = mock_google_ads_client
    personas = [
        Persona(name="Persona A", description=""),
        Persona(name="Persona B", description=""),
    ]

    create_growth_tier_campaign(
        customer_id=CUSTOMER_ID,
        campaign_name="Test Ad Group Campaign",
        budget_micros=1000000,
        monetization_model="BOOK_CALL",
        personas=personas,
    )

    ad_group_service = mock_google_ads_client.get_service("AdGroupService")

    # Check call count
    assert ad_group_service.mutate_ad_groups.call_count == 2

    # Check that it was called with the correct persona names, regardless of order
    call_args = [call[1]['operations'][0].create.name for call in ad_group_service.mutate_ad_groups.call_args_list]
    assert "Test Ad Group Campaign - Persona A" in call_args
    assert "Test Ad Group Campaign - Persona B" in call_args


@patch("src.tools.create_campaign.get_google_ads_client")
def test_invalid_monetization_model(mock_get_google_ads_client, mock_google_ads_client):
    mock_get_google_ads_client.return_value = mock_google_ads_client
    with pytest.raises(ValueError):
        create_growth_tier_campaign(
            customer_id=CUSTOMER_ID,
            campaign_name="Test Campaign",
            budget_micros=1000000,
            monetization_model="INVALID_MODEL",
            personas=[],
        )


@patch("src.tools.create_campaign.get_google_ads_client")
def test_google_ads_exception_propagation(mock_get_google_ads_client, mock_google_ads_client):
    mock_get_google_ads_client.return_value = mock_google_ads_client

    mock_error = MagicMock()
    mock_failure = MagicMock()
    mock_failure.errors = [mock_error]

    campaign_budget_service = mock_google_ads_client.get_service("CampaignBudgetService")
    campaign_budget_service.mutate_campaign_budgets.side_effect = GoogleAdsException(
        failure=mock_failure, call=MagicMock(), error=mock_error, request_id="12345"
    )

    with pytest.raises(GoogleAdsException):
        create_growth_tier_campaign(
            customer_id=CUSTOMER_ID,
            campaign_name="Test Campaign",
            budget_micros=1000000,
            monetization_model="BOOK_CALL",
            personas=[],
        )
