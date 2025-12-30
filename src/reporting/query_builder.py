from enum import Enum, auto
from typing import List, Optional


class ReportType(Enum):
    CAMPAIGN = auto()
    AD_GROUP = auto()
    KEYWORD = auto()
    SEARCH_TERM = auto()


class QueryBuilder:
    def build_performance_query(
        self,
        report_type: ReportType,
        date_range: str = "LAST_30_DAYS",
        metrics: Optional[List[str]] = None,
        segments: Optional[List[str]] = None,
    ) -> str:
        """Builds GAQL query with proper segmentation handling."""
        if metrics is None:
            metrics = [
                "metrics.impressions",
                "metrics.clicks",
                "metrics.cost_micros",
            ]
        if segments is None:
            segments = []

        select_fields = metrics + segments
        from_clause = ""
        where_clause = ""

        if report_type == ReportType.CAMPAIGN:
            select_fields.extend(["campaign.id", "campaign.name", "campaign.status"])
            from_clause = "campaign"
        elif report_type == ReportType.AD_GROUP:
            select_fields.extend(
                [
                    "ad_group.id",
                    "ad_group.name",
                    "ad_group_ad.ad.id",
                    "ad_group_ad.ad.name",
                    "ad_group_ad.status",
                    "campaign.id",
                    "campaign.name",
                ]
            )
            from_clause = "ad_group_ad"
        elif report_type == ReportType.KEYWORD:
            select_fields.extend(
                [
                    "ad_group_criterion.criterion.id",
                    "ad_group_criterion.keyword.text",
                    "ad_group.id",
                    "ad_group.name",
                    "campaign.id",
                    "campaign.name",
                ]
            )
            from_clause = "keyword_view"
            where_clause = "WHERE campaign.advertising_channel_type = 'SEARCH'"
        elif report_type == ReportType.SEARCH_TERM:
            select_fields.extend(
                [
                    "search_term_view.search_term",
                    "ad_group.id",
                    "ad_group.name",
                    "campaign.id",
                    "campaign.name",
                ]
            )
            from_clause = "search_term_view"
            where_clause = "WHERE campaign.advertising_channel_type = 'SEARCH'"

        query = f"""
            SELECT
                {', '.join(select_fields)}
            FROM {from_clause}
            {where_clause}
            DURING {date_range}
        """
        return " ".join(query.split())
