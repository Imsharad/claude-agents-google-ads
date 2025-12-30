"""
TASK-030: Implement Conversion Tracking Setup Helper

This module provides a tool to check the status of conversion tracking in Google Ads.
"""

from pydantic import BaseModel, Field
from claude_agent_sdk import tool
from src.config.google_ads_client import get_google_ads_client


class CheckConversionSetupInput(BaseModel):
    customer_id: str = Field(..., description="The Google Ads customer ID.")


@tool(
    name="check_conversion_setup",
    description="Checks if conversion tracking is configured and active for a given Google Ads customer.",
    input_schema=CheckConversionSetupInput,
)
def check_conversion_setup(props: CheckConversionSetupInput) -> dict:
    """
    Checks if conversion tracking is configured and active for a given Google Ads customer.

    This tool queries the ConversionActionService to find existing conversion actions.
    It then validates whether tracking is working by checking for recent impressions.

    Args:
        props: An object containing the customer_id.

    Returns:
        A dictionary containing the status of the conversion setup.
        Possible statuses are:
        - "not_found": No conversion actions are set up.
        - "inactive": Conversion actions exist but have no recent impressions.
        - "active": Conversion tracking is set up and appears to be working.
    """
    google_ads_client = get_google_ads_client()
    ga_service = google_ads_client.get_service("GoogleAdsService")
    customer_id = props.customer_id

    # First, check if any conversion actions exist at all.
    query_any_actions = """
        SELECT conversion_action.resource_name
        FROM conversion_action
        WHERE conversion_action.status = 'ENABLED'
        LIMIT 1
    """
    search_request_any = google_ads_client.get_type("SearchGoogleAdsStreamRequest")
    search_request_any.customer_id = customer_id
    search_request_any.query = query_any_actions
    stream_any = ga_service.search_stream(search_request_any)

    try:
        # Check if the iterator is empty
        first_batch = next(iter(stream_any))
        if not first_batch.results:
            return {
                "status": "not_found",
                "message": "No conversion actions found. Please set up conversion tracking in your Google Ads account. This typically requires adding a tracking tag to your website.",
            }
    except StopIteration:
        return {
            "status": "not_found",
            "message": "No conversion actions found. Please set up conversion tracking in your Google Ads account. This typically requires adding a tracking tag to your website.",
        }

    # If actions exist, check for impressions.
    query_active_actions = """
        SELECT conversion_action.resource_name, conversion_action.name
        FROM conversion_action
        WHERE conversion_action.status = 'ENABLED'
        AND metrics.impressions > 0
        LIMIT 1
    """
    search_request_active = google_ads_client.get_type("SearchGoogleAdsStreamRequest")
    search_request_active.customer_id = customer_id
    search_request_active.query = query_active_actions
    stream_active = ga_service.search_stream(search_request_active)

    try:
        for batch in stream_active:
            for row in batch.results:
                return {
                    "status": "active",
                    "resource_name": row.conversion_action.resource_name,
                    "name": row.conversion_action.name,
                    "message": "Conversion tracking is active and receiving impressions.",
                }
    except StopIteration:
        pass  # Fall through to the inactive case

    return {
        "status": "inactive",
        "message": "Conversion actions are set up, but no impressions have been recorded recently. Please verify your tracking tag implementation.",
    }
