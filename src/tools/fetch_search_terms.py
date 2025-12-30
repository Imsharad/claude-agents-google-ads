"""
TASK-021: MCP Tool for fetching search terms report from Google Ads API.
"""

from google.ads.googleads.errors import GoogleAdsException
from claude_agent_sdk import tool
from src.config.google_ads_client import get_google_ads_client


def _fetch_search_terms(
    customer_id: str, campaign_id: str, date_range: str = "LAST_30_DAYS"
) -> dict:
    """
    Fetches search terms report for a given campaign.

    This tool retrieves a report of search terms from the Google Ads API,
    including performance metrics like impressions, clicks, conversions, and cost.
    It is useful for negative keyword mining.

    Args:
        customer_id: The Google Ads customer ID.
        campaign_id: The ID of the campaign to fetch the report for.
        date_range: The date range for the report (e.g., "LAST_7_DAYS", "LAST_30_DAYS").
                    Defaults to "LAST_30_DAYS".

    Returns:
        A dictionary containing a list of search terms and their metrics.
        Returns an error message if the API call fails.
    """
    google_ads_client = get_google_ads_client()
    ga_service = google_ads_client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            search_term_view.search_term,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.cost_micros
        FROM search_term_view
        WHERE campaign = 'customers/{customer_id}/campaigns/{campaign_id}'
        AND segments.date DURING {date_range}
    """

    search_request = google_ads_client.get_type("SearchGoogleAdsStreamRequest")
    search_request.customer_id = customer_id
    search_request.query = query

    try:
        stream = ga_service.search_stream(search_request)
        search_terms = []
        for batch in stream:
            for row in batch.results:
                search_terms.append(
                    {
                        "search_term": row.search_term_view.search_term,
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "conversions": row.metrics.conversions,
                        "cost_micros": row.metrics.cost_micros,
                    }
                )
        return {"search_terms": search_terms}
    except GoogleAdsException as ex:
        return {"error": f"Google Ads API failed with message: {ex.message}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}


@tool(
    "fetch_search_terms",
    "Fetches search terms report for a given campaign.",
    {
        "customer_id": str,
        "campaign_id": str,
        "date_range": str,
    },
)
def fetch_search_terms(
    customer_id: str, campaign_id: str, date_range: str = "LAST_30_DAYS"
) -> dict:
    return _fetch_search_terms(customer_id, campaign_id, date_range)
