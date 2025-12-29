"""
TASK-027: Implement Shared Negative Keyword Sets

This module manages shared negative keyword sets in Google Ads.
"""

from typing import List
from google.ads.googleads.client import GoogleAdsClient
from src.config.google_ads_client import get_google_ads_client
from src.generators.negative_keywords import get_universal_negatives

UNIVERSAL_NEGATIVE_KEYWORDS_SET_NAME = "Universal Negative Keywords"


def apply_universal_negative_keywords_to_campaign(
    customer_id: str, campaign_id: str
):
    """
    Applies the universal negative keyword shared set to a campaign.

    Checks if the set exists. If not, it creates and populates it.
    Then, it attaches the set to the specified campaign.

    Args:
        customer_id: The Google Ads customer ID.
        campaign_id: The ID of the campaign.
    """
    google_ads_client = get_google_ads_client()
    ga_service = google_ads_client.get_service("GoogleAdsService")

    # Search for the shared set
    query = f"""
        SELECT shared_set.resource_name
        FROM shared_set
        WHERE shared_set.name = '{UNIVERSAL_NEGATIVE_KEYWORDS_SET_NAME}'
    """
    search_request = google_ads_client.get_type("SearchGoogleAdsStreamRequest")
    search_request.customer_id = customer_id
    search_request.query = query
    stream = ga_service.search_stream(search_request)

    shared_set_resource_name = None
    for batch in stream:
        for row in batch.results:
            shared_set_resource_name = row.shared_set.resource_name
            break
        if shared_set_resource_name:
            break

    # If the shared set doesn't exist, create it
    if not shared_set_resource_name:
        shared_set_resource_name = create_shared_negative_set(
            customer_id, UNIVERSAL_NEGATIVE_KEYWORDS_SET_NAME
        )
        add_keywords_to_shared_set(
            customer_id, shared_set_resource_name, get_universal_negatives()
        )

    # Attach the shared set to the campaign
    attach_shared_set_to_campaign(
        customer_id, campaign_id, shared_set_resource_name
    )


def create_shared_negative_set(customer_id: str, name: str) -> str:
    """
    Creates a new shared negative keyword set.

    Args:
        customer_id: The Google Ads customer ID.
        name: The name of the shared set.

    Returns:
        The resource name of the newly created shared set.
    """
    google_ads_client = get_google_ads_client()
    shared_set_service = google_ads_client.get_service("SharedSetService")

    shared_set_operation = google_ads_client.get_type("SharedSetOperation")
    shared_set = shared_set_operation.create
    shared_set.name = name
    shared_set.type_ = google_ads_client.get_type("SharedSetTypeEnum").SharedSetType.NEGATIVE_KEYWORDS

    response = shared_set_service.mutate_shared_sets(
        customer_id=customer_id, operations=[shared_set_operation]
    )

    return response.results[0].resource_name


def add_keywords_to_shared_set(
    customer_id: str, shared_set_resource_name: str, keywords: List[str]
):
    """
    Adds keywords to a shared negative keyword set.

    Args:
        customer_id: The Google Ads customer ID.
        shared_set_resource_name: The resource name of the shared set.
        keywords: A list of negative keywords to add.
    """
    google_ads_client = get_google_ads_client()
    shared_criterion_service = google_ads_client.get_service("SharedCriterionService")

    operations = []
    for keyword in keywords:
        operation = google_ads_client.get_type("SharedCriterionOperation")
        shared_criterion = operation.create
        shared_criterion.shared_set = shared_set_resource_name
        shared_criterion.keyword.text = keyword
        shared_criterion.keyword.match_type = (
            google_ads_client.get_type("KeywordMatchTypeEnum").KeywordMatchType.BROAD
        )
        operations.append(operation)

    shared_criterion_service.mutate_shared_criteria(
        customer_id=customer_id, operations=operations
    )


def attach_shared_set_to_campaign(
    customer_id: str, campaign_id: str, shared_set_resource_name: str
):
    """
    Attaches a shared negative keyword set to a campaign.

    Args:
        customer_id: The Google Ads customer ID.
        campaign_id: The ID of the campaign.
        shared_set_resource_name: The resource name of the shared set.
    """
    google_ads_client = get_google_ads_client()
    campaign_shared_set_service = google_ads_client.get_service(
        "CampaignSharedSetService"
    )

    campaign_resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"

    operation = google_ads_client.get_type("CampaignSharedSetOperation")
    campaign_shared_set = operation.create
    campaign_shared_set.campaign = campaign_resource_name
    campaign_shared_set.shared_set = shared_set_resource_name

    campaign_shared_set_service.mutate_campaign_shared_sets(
        customer_id=customer_id, operations=[operation]
    )
