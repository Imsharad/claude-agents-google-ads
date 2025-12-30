# src/monitoring/ctr_monitor.py

import logging
from typing import List

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdPerformance(BaseModel):
    """Data model for ad performance metrics."""

    ad_id: str = Field(..., description="The ID of the ad.")
    ad_group_ad_resource_name: str = Field(
        ..., description="The resource name of the ad group ad."
    )
    ctr: float = Field(..., description="The click-through rate of the ad.")
    impressions: int = Field(
        ..., description="The number of impressions the ad received."
    )
    clicks: int = Field(..., description="The number of clicks the ad received.")


class CTRMonitor:
    """A class to monitor and manage ad performance based on CTR."""

    def __init__(self, client: GoogleAdsClient):
        """
        Initializes the CTRMonitor with a GoogleAdsClient.

        Args:
            client: An initialized Google Ads API client.
        """
        self.client = client
        self.google_ads_service = self.client.get_service("GoogleAdsService")

    def check_ad_performance(
        self, customer_id: str, campaign_id: str
    ) -> List[AdPerformance]:
        """
        Retrieves ad performance data for a given campaign.

        Args:
            customer_id: The ID of the Google Ads customer.
            campaign_id: The ID of the campaign to check.

        Returns:
            A list of AdPerformance objects.
        """
        query = f"""
            SELECT ad_group_ad.ad.id, ad_group_ad.resource_name, metrics.ctr, metrics.impressions, metrics.clicks
            FROM ad_group_ad
            WHERE campaign.id = {campaign_id}
            AND metrics.impressions > 100
        """
        try:
            response = self.google_ads_service.search_stream(
                customer_id=customer_id, query=query
            )
            ads_performance = []
            for batch in response:
                for row in batch.results:
                    ad_performance = AdPerformance(
                        ad_id=str(row.ad_group_ad.ad.id),
                        ad_group_ad_resource_name=row.ad_group_ad.resource_name,
                        ctr=row.metrics.ctr,
                        impressions=row.metrics.impressions,
                        clicks=row.metrics.clicks,
                    )
                    ads_performance.append(ad_performance)
            logger.info(f"Found {len(ads_performance)} ads with >100 impressions.")
            return ads_performance
        except GoogleAdsException as ex:
            logger.error(
                f'Request with ID "{ex.request_id}" failed with status '
                f'"{ex.error.code().name}" and includes the following errors:'
            )
            for error in ex.failure.errors:
                logger.error(f'\tError with message "{error.message}".')
                if error.location:
                    for field_path_element in error.location.field_path_elements:
                        logger.error(f"\t\tOn field: {field_path_element.field_name}")
            return []

    def identify_underperformers(
        self, ads: List[AdPerformance], threshold: float = 0.01
    ) -> List[str]:
        """
        Identifies ads that are performing below a given CTR threshold.

        Args:
            ads: A list of AdPerformance objects.
            threshold: The CTR threshold (default is 0.01 for 1%).

        Returns:
            A list of ad group ad resource names for the underperforming ads.
        """
        underperforming_ad_resource_names = [
            ad.ad_group_ad_resource_name for ad in ads if ad.ctr < threshold
        ]
        logger.info(
            f"Identified {len(underperforming_ad_resource_names)} underperforming ads "
            f"(CTR < {threshold})."
        )
        return underperforming_ad_resource_names

    def pause_underperforming_ads(
        self, customer_id: str, ad_group_ad_resource_names: List[str]
    ):
        """
        Pauses a list of underperforming ads.

        Args:
            customer_id: The ID of the Google Ads customer.
            ad_group_ad_resource_names: A list of ad group ad resource names to pause.
        """
        if not ad_group_ad_resource_names:
            logger.info("No underperforming ads to pause.")
            return

        ad_group_ad_service = self.client.get_service("AdGroupAdService")
        operations = []
        for resource_name in ad_group_ad_resource_names:
            operation = self.client.get_type("AdGroupAdOperation")
            ad_group_ad = operation.update
            ad_group_ad.resource_name = resource_name
            ad_group_ad.status = self.client.enums.AdGroupAdStatusEnum.PAUSED

            # Create a field mask to specify which fields are being updated.
            field_mask = self.client.get_type("FieldMask")
            field_mask.paths.append("status")
            self.client.copy_from(operation.update_mask, field_mask)

            operations.append(operation)

        try:
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id, operations=operations
            )
            logger.info(f"Paused {len(response.results)} underperforming ads.")
            for result in response.results:
                logger.info(f"Paused ad: {result.resource_name}")
        except GoogleAdsException as ex:
            logger.error(
                f'Request with ID "{ex.request_id}" failed with status '
                f'"{ex.error.code().name}" and includes the following errors:'
            )
            for error in ex.failure.errors:
                logger.error(f'\tError with message "{error.message}".')
