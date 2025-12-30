import pytest
from src.reporting.query_builder import QueryBuilder, ReportType


@pytest.fixture
def query_builder():
    return QueryBuilder()


def test_build_performance_query_campaign(query_builder):
    query = query_builder.build_performance_query(ReportType.CAMPAIGN)
    expected_query = (
        "SELECT metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "campaign.id, campaign.name, campaign.status "
        "FROM campaign "
        "DURING LAST_30_DAYS"
    )
    assert " ".join(query.split()) == " ".join(expected_query.split())


def test_build_performance_query_ad_group(query_builder):
    query = query_builder.build_performance_query(ReportType.AD_GROUP)
    expected_query = (
        "SELECT metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "ad_group.id, ad_group.name, ad_group_ad.ad.id, ad_group_ad.ad.name, "
        "ad_group_ad.status, campaign.id, campaign.name "
        "FROM ad_group_ad "
        "DURING LAST_30_DAYS"
    )
    assert " ".join(query.split()) == " ".join(expected_query.split())


def test_build_performance_query_keyword(query_builder):
    query = query_builder.build_performance_query(ReportType.KEYWORD)
    expected_query = (
        "SELECT metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "ad_group_criterion.criterion.id, ad_group_criterion.keyword.text, "
        "ad_group.id, ad_group.name, campaign.id, campaign.name "
        "FROM keyword_view "
        "WHERE campaign.advertising_channel_type = 'SEARCH' "
        "DURING LAST_30_DAYS"
    )
    assert " ".join(query.split()) == " ".join(expected_query.split())


def test_build_performance_query_search_term(query_builder):
    query = query_builder.build_performance_query(ReportType.SEARCH_TERM)
    expected_query = (
        "SELECT metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "search_term_view.search_term, ad_group.id, ad_group.name, "
        "campaign.id, campaign.name "
        "FROM search_term_view "
        "WHERE campaign.advertising_channel_type = 'SEARCH' "
        "DURING LAST_30_DAYS"
    )
    assert " ".join(query.split()) == " ".join(expected_query.split())


def test_build_performance_query_with_custom_metrics_and_segments(query_builder):
    query = query_builder.build_performance_query(
        ReportType.CAMPAIGN,
        metrics=["metrics.conversions"],
        segments=["segments.date"],
    )
    expected_query = (
        "SELECT metrics.conversions, segments.date, "
        "campaign.id, campaign.name, campaign.status "
        "FROM campaign "
        "DURING LAST_30_DAYS"
    )
    assert " ".join(query.split()) == " ".join(expected_query.split())


def test_build_performance_query_with_custom_date_range(query_builder):
    query = query_builder.build_performance_query(
        ReportType.CAMPAIGN,
        date_range="YESTERDAY",
    )
    expected_query = (
        "SELECT metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "campaign.id, campaign.name, campaign.status "
        "FROM campaign "
        "DURING YESTERDAY"
    )
    assert " ".join(query.split()) == " ".join(expected_query.split())
