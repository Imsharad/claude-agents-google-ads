# tests/test_ctr_monitor.py

import unittest.mock as mock

import pytest
from google.ads.googleads.errors import GoogleAdsException
from src.monitoring.ctr_monitor import AdPerformance, CTRMonitor


@pytest.fixture
def mock_google_ads_client():
    """Fixture for a mocked Google Ads client."""
    return mock.MagicMock()


def test_check_ad_performance_success(mock_google_ads_client):
    """Test check_ad_performance successfully retrieves and parses data."""
    # Arrange
    mock_service = mock.MagicMock()
    mock_google_ads_client.get_service.return_value = mock_service

    # Create mock API response
    mock_row1 = mock.MagicMock()
    mock_row1.ad_group_ad.ad.id = 123
    mock_row1.ad_group_ad.resource_name = "customers/1/adGroupAds/123~456"
    mock_row1.metrics.ctr = 0.05
    mock_row1.metrics.impressions = 200
    mock_row1.metrics.clicks = 10

    mock_row2 = mock.MagicMock()
    mock_row2.ad_group_ad.ad.id = 456
    mock_row2.ad_group_ad.resource_name = "customers/1/adGroupAds/456~789"
    mock_row2.metrics.ctr = 0.005
    mock_row2.metrics.impressions = 300
    mock_row2.metrics.clicks = 1

    mock_batch = mock.MagicMock()
    mock_batch.results = [mock_row1, mock_row2]
    mock_service.search_stream.return_value = [mock_batch]

    monitor = CTRMonitor(client=mock_google_ads_client)
    customer_id = "test_customer"
    campaign_id = "test_campaign"

    # Act
    result = monitor.check_ad_performance(customer_id, campaign_id)

    # Assert
    assert len(result) == 2
    assert isinstance(result[0], AdPerformance)
    assert result[0].ad_id == "123"
    assert result[0].ad_group_ad_resource_name == "customers/1/adGroupAds/123~456"
    assert result[0].ctr == 0.05
    assert result[1].ad_id == "456"
    assert result[1].ctr == 0.005

    mock_service.search_stream.assert_called_once()


def test_check_ad_performance_exception(mock_google_ads_client):
    """Test check_ad_performance handles GoogleAdsException."""
    # Arrange
    mock_service = mock.MagicMock()
    mock_google_ads_client.get_service.return_value = mock_service
    mock_service.search_stream.side_effect = GoogleAdsException(
        error=mock.MagicMock(),
        failure=mock.MagicMock(),
        request_id="test_request_id",
        call=mock.MagicMock(),
    )

    monitor = CTRMonitor(client=mock_google_ads_client)
    customer_id = "test_customer"
    campaign_id = "test_campaign"

    # Act
    result = monitor.check_ad_performance(customer_id, campaign_id)

    # Assert
    assert result == []


def test_identify_underperformers():
    """Test identify_underperformers correctly filters ads."""
    # Arrange
    ads = [
        AdPerformance(
            ad_id="1",
            ad_group_ad_resource_name="resource1",
            ctr=0.02,
            impressions=150,
            clicks=3,
        ),
        AdPerformance(
            ad_id="2",
            ad_group_ad_resource_name="resource2",
            ctr=0.009,
            impressions=200,
            clicks=1,
        ),
        AdPerformance(
            ad_id="3",
            ad_group_ad_resource_name="resource3",
            ctr=0.005,
            impressions=500,
            clicks=2,
        ),
        AdPerformance(
            ad_id="4",
            ad_group_ad_resource_name="resource4",
            ctr=0.01,
            impressions=300,
            clicks=3,
        ),
    ]
    monitor = CTRMonitor(client=mock.MagicMock())

    # Act
    result = monitor.identify_underperformers(ads, threshold=0.01)

    # Assert
    assert len(result) == 2
    assert "resource2" in result
    assert "resource3" in result
    assert "resource1" not in result
    assert "resource4" not in result


def test_identify_underperformers_empty_list():
    """Test identify_underperformers with an empty list."""
    # Arrange
    monitor = CTRMonitor(client=mock.MagicMock())

    # Act
    result = monitor.identify_underperformers([], threshold=0.01)

    # Assert
    assert result == []


def test_pause_underperforming_ads(mock_google_ads_client):
    """Test pause_underperforming_ads constructs and sends correct API call."""
    # Arrange
    mock_ad_group_ad_service = mock.MagicMock()
    mock_google_ads_client.get_service.return_value = mock_ad_group_ad_service

    # Mock the enums and types
    mock_google_ads_client.enums.AdGroupAdStatusEnum.PAUSED = "PAUSED"
    mock_google_ads_client.get_type.side_effect = lambda name, **kwargs: mock.MagicMock()


    monitor = CTRMonitor(client=mock_google_ads_client)
    customer_id = "test_customer"
    underperforming_ads = ["resource1", "resource2"]

    # Act
    monitor.pause_underperforming_ads(customer_id, underperforming_ads)

    # Assert
    mock_google_ads_client.get_service.assert_called_with("AdGroupAdService")
    mock_ad_group_ad_service.mutate_ad_group_ads.assert_called_once()

    # Check the operations passed to the mutate call
    call_args = mock_ad_group_ad_service.mutate_ad_group_ads.call_args
    assert call_args[1]["customer_id"] == customer_id
    operations = call_args[1]["operations"]
    assert len(operations) == 2
    assert operations[0].update.resource_name == "resource1"
    assert operations[0].update.status == "PAUSED"
    assert operations[1].update.resource_name == "resource2"


def test_pause_underperforming_ads_no_ads(mock_google_ads_client):
    """Test pause_underperforming_ads does nothing when list is empty."""
    # Arrange
    mock_ad_group_ad_service = mock.MagicMock()
    mock_google_ads_client.get_service.return_value = mock_ad_group_ad_service

    monitor = CTRMonitor(client=mock_google_ads_client)
    customer_id = "test_customer"

    # Act
    monitor.pause_underperforming_ads(customer_id, [])

    # Assert
    mock_ad_group_ad_service.mutate_ad_group_ads.assert_not_called()
