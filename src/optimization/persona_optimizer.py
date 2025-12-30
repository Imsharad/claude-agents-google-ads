from typing import List, Dict, Any
import logging

from src.config.google_ads_client import get_google_ads_client
from src.reporting.query_builder import QueryBuilder, ReportType

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PersonaOptimizer:
    """
    A class to handle persona (ad group) optimization logic.
    """

    def __init__(self):
        self.client = get_google_ads_client()
        self.google_ads_service = self.client.get_service("GoogleAdsService")
        self.query_builder = QueryBuilder()

    def _get_campaign_details(
        self, customer_id: str, campaign_id: str
    ) -> Dict[str, Any]:
        """Fetches campaign-level details, including bidding strategy and target CPA."""
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.bidding_strategy_type,
                campaign.target_cpa.target_cpa_micros
            FROM campaign
            WHERE campaign.id = '{campaign_id}'
        """
        response = self.google_ads_service.search_stream(
            customer_id=customer_id, query=query
        )
        for batch in response:
            for row in batch.results:
                return {
                    "bidding_strategy_type": row.campaign.bidding_strategy_type,
                    "target_cpa_micros": row.campaign.target_cpa.target_cpa_micros,
                }
        return {}

    def _get_ad_group_performance(
        self, customer_id: str, campaign_id: str
    ) -> List[Dict[str, Any]]:
        """Fetches ad group performance data for a given campaign."""
        query = self.query_builder.build_performance_query(
            report_type=ReportType.AD_GROUP,
            metrics=[
                "metrics.cost_micros",
                "metrics.conversions",
                "metrics.cost_per_conversion",
            ],
        )
        query += f" AND campaign.id = '{campaign_id}'"

        response = self.google_ads_service.search_stream(
            customer_id=customer_id, query=query
        )
        ad_group_performance = []
        for batch in response:
            for row in batch.results:
                ad_group_performance.append(
                    {
                        "ad_group_id": row.ad_group.id,
                        "cost_micros": row.metrics.cost_micros,
                        "conversions": row.metrics.conversions,
                        "cost_per_conversion": row.metrics.cost_per_conversion,
                    }
                )
        return ad_group_performance

    def identify_losing_personas(self, customer_id: str, campaign_id: str) -> List[str]:
        """
        Identifies ad groups that are performing poorly based on specific criteria.
        """
        campaign_details = self._get_campaign_details(customer_id, campaign_id)
        target_cpa = campaign_details.get("target_cpa_micros", 0)
        ad_groups = self._get_ad_group_performance(customer_id, campaign_id)
        losing_ad_groups = []

        for ad_group in ad_groups:
            is_losing = False
            # Criteria 1: cost_per_conversion > target_cpa
            if target_cpa > 0 and ad_group["cost_per_conversion"] > target_cpa:
                is_losing = True
            # Criteria 2: conversions = 0 AND spend > ₹2000
            if (
                ad_group["conversions"] == 0
                and ad_group["cost_micros"] > 2000 * 1_000_000
            ):
                is_losing = True

            if is_losing:
                losing_ad_groups.append(ad_group["ad_group_id"])
                logging.info(
                    f"Identified losing ad group {ad_group['ad_group_id']} (Cost: {ad_group['cost_micros']}, Conversions: {ad_group['conversions']}, CPA: {ad_group['cost_per_conversion']})"
                )

        return losing_ad_groups

    def identify_winning_personas(
        self, customer_id: str, campaign_id: str
    ) -> List[str]:
        """
        Identifies ad groups that are performing well based on specific criteria.
        """
        campaign_details = self._get_campaign_details(customer_id, campaign_id)
        target_cpa = campaign_details.get("target_cpa_micros", 0)
        ad_groups = self._get_ad_group_performance(customer_id, campaign_id)
        winning_ad_groups = []

        if not target_cpa or target_cpa == 0:
            logging.warning(
                f"Cannot identify winning personas for campaign {campaign_id} without a target CPA."
            )
            return []

        for ad_group in ad_groups:
            # Criteria: cost_per_conversion < target_cpa AND conversions >= 5
            if (
                ad_group["cost_per_conversion"] < target_cpa
                and ad_group["conversions"] >= 5
            ):
                winning_ad_groups.append(ad_group["ad_group_id"])
                logging.info(
                    f"Identified winning ad group {ad_group['ad_group_id']} (Cost: {ad_group['cost_micros']}, Conversions: {ad_group['conversions']}, CPA: {ad_group['cost_per_conversion']})"
                )

        return winning_ad_groups

    def pause_ad_group(self, customer_id: str, ad_group_id: str):
        """
        Pauses a given ad group.
        """
        ad_group_service = self.client.get_service("AdGroupService")
        ad_group_resource_name = ad_group_service.ad_group_path(
            customer_id, ad_group_id
        )

        ad_group_operation = self.client.get_type("AdGroupOperation")

        ad_group = ad_group_operation.update
        ad_group.resource_name = ad_group_resource_name
        ad_group.status = self.client.get_type("AdGroupStatusEnum").AdGroupStatus.PAUSED

        self.client.copy_from(
            ad_group_operation.update_mask,
            self.client.get_type("FieldMask", paths=["status"]),
        )

        try:
            ad_group_service.mutate_ad_groups(
                customer_id=customer_id, operations=[ad_group_operation]
            )
            logging.info(f"Ad group {ad_group_resource_name} paused successfully.")
        except Exception as e:
            logging.error(f"Failed to pause ad group {ad_group_resource_name}: {e}")
            raise

    def _get_ad_group_details(
        self, customer_id: str, ad_group_id: str
    ) -> Dict[str, Any]:
        """Fetches ad group details, including the campaign resource name."""
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.bidding_strategy_type,
                campaign.maximize_clicks.cpc_bid_limit_micros
            FROM ad_group
            WHERE ad_group.id = '{ad_group_id}'
        """
        response = self.google_ads_service.search_stream(
            customer_id=customer_id, query=query
        )
        for batch in response:
            for row in batch.results:
                return {
                    "campaign_id": row.campaign.id,
                    "bidding_strategy_type": row.campaign.bidding_strategy_type,
                    "cpc_bid_limit_micros": row.campaign.maximize_clicks.cpc_bid_limit_micros,
                }
        return {}

    def _update_keyword_bids(
        self, customer_id: str, ad_group_id: str, percentage: float
    ):
        """Increases CPC bid for all keywords in an ad group by a percentage."""
        ad_group_criterion_service = self.client.get_service("AdGroupCriterionService")

        query = f"""
            SELECT
                ad_group_criterion.resource_name,
                ad_group_criterion.cpc_bid_micros
            FROM ad_group_criterion
            WHERE ad_group.id = '{ad_group_id}'
            AND ad_group_criterion.type = 'KEYWORD'
            AND ad_group_criterion.status = 'ENABLED'
        """
        response = self.google_ads_service.search_stream(
            customer_id=customer_id, query=query
        )

        operations = []
        for batch in response:
            for row in batch.results:
                criterion = row.ad_group_criterion
                if criterion.cpc_bid_micros:
                    new_bid = int(criterion.cpc_bid_micros * (1 + percentage))

                    operation = self.client.get_type("AdGroupCriterionOperation")
                    update_criterion = operation.update
                    update_criterion.resource_name = criterion.resource_name
                    update_criterion.cpc_bid_micros = new_bid

                    self.client.copy_from(
                        operation.update_mask,
                        self.client.get_type("FieldMask", paths=["cpc_bid_micros"]),
                    )
                    operations.append(operation)

        if not operations:
            logging.warning(
                f"No keywords with existing bids found to update for ad group {ad_group_id}."
            )
            return

        try:
            ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id, operations=operations
            )
            logging.info(
                f"Successfully increased bids by {percentage:.2%} for {len(operations)} keywords in ad group {ad_group_id}."
            )
        except Exception as e:
            logging.error(
                f"Failed to update keyword bids for ad group {ad_group_id}: {e}"
            )
            raise

    def increase_bids(
        self, customer_id: str, ad_group_id: str, percentage: float = 0.20
    ):
        """
        Increases bids for a given ad group, depending on the campaign's bidding strategy.
        """
        ad_group_details = self._get_ad_group_details(customer_id, ad_group_id)
        if not ad_group_details:
            logging.error(f"Could not retrieve details for ad group {ad_group_id}.")
            return

        bidding_strategy = ad_group_details["bidding_strategy_type"]
        bidding_strategy_enum = self.client.get_type(
            "BiddingStrategyTypeEnum"
        ).BiddingStrategyType

        if bidding_strategy == bidding_strategy_enum.MANUAL_CPC:
            logging.info(
                f"Bidding strategy is Manual CPC. Increasing keyword bids for ad group {ad_group_id}."
            )
            self._update_keyword_bids(customer_id, ad_group_id, percentage)
        elif bidding_strategy == bidding_strategy_enum.MAXIMIZE_CLICKS:
            campaign_id = ad_group_details["campaign_id"]
            current_limit = ad_group_details["cpc_bid_limit_micros"]

            if not current_limit:
                logging.warning(
                    f"Campaign {campaign_id} has no CPC bid limit. Cannot increase."
                )
                return

            new_limit = int(current_limit * (1 + percentage))

            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")

            campaign = campaign_operation.update
            campaign.resource_name = campaign_service.campaign_path(
                customer_id, campaign_id
            )
            campaign.maximize_clicks.cpc_bid_limit_micros = new_limit

            self.client.copy_from(
                campaign_operation.update_mask,
                self.client.get_type(
                    "FieldMask", paths=["maximize_clicks.cpc_bid_limit_micros"]
                ),
            )

            try:
                campaign_service.mutate_campaigns(
                    customer_id=customer_id, operations=[campaign_operation]
                )
                logging.info(
                    f"Successfully increased Maximize Clicks bid cap to {new_limit} for campaign {campaign_id}."
                )
            except Exception as e:
                logging.error(
                    f"Failed to increase bid cap for campaign {campaign_id}: {e}"
                )
                raise
        elif bidding_strategy in [
            bidding_strategy_enum.TARGET_CPA,
            bidding_strategy_enum.TARGET_ROAS,
        ]:
            logging.info(
                f"Bidding strategy is {bidding_strategy.name}. No action taken as it is an automated strategy."
            )
        else:
            logging.warning(f"Unhandled bidding strategy: {bidding_strategy.name}")
