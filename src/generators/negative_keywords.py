"""
TASK-013: Negative Keyword Generation

This module provides lists of negative keywords, both universal and
vertical-specific, to prevent ad spend on irrelevant search queries.
"""

from typing import List, Dict
from src.models.enums import VerticalType


def get_universal_negatives() -> List[str]:
    """
    Returns a list of universal negative keywords.
    REQ-9: Must include terms related to free, jobs, etc.
    """
    return [
        "free",
        "cheap",
        "crack",
        "torrent",
        "download",
        "job",
        "career",
        "hiring",
        "apply",
        "salary",
        "internship",
    ]


def generate_vertical_negatives(vertical: VerticalType) -> List[str]:
    """
    Generates a list of negative keywords tailored to a specific vertical.
    """
    # Using a dictionary to map verticals to their negative keyword lists
    vertical_map: Dict[VerticalType, List[str]] = {
        VerticalType.EDUCATION: [
            "university credit",
            "degree program",
            "accredited",
            "financial aid",
            "student loans",
            "scholarship",
            "for kids",
            "beginners",
            "101",
            "tutorial",
            "youtube",
        ],
        VerticalType.SAAS: [
            "open source",
            "self-hosted",
            "reviews",
            "comparison",
            "vs",
            "alternative to",
            "support forum",
            "documentation",
            "api docs",
            "status page",
            "enterprise",
        ],
        VerticalType.SERVICE: [
            "diy",
            "do it yourself",
            "home remedy",
            "pictures",
            "video",
            "how to",
            "tools",
            "equipment",
            "supplies",
            "cost",
            "price",
            "reviews",
        ],
    }

    # Return the list for the given vertical, or an empty list if not found
    return vertical_map.get(vertical, [])
