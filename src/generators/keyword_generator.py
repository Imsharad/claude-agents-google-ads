"""
TASK-013: Keyword Strategy Generator

This module generates keyword ideas based on the campaign configuration.
"""

from dataclasses import dataclass
from typing import List
import re
from src.models.configuration import CampaignConfiguration


@dataclass
class Keyword:
    """Represents a single keyword with its match type."""

    text: str
    match_type: str


def generate_keywords(config: CampaignConfiguration) -> List[Keyword]:
    """
    Generates a list of PHRASE match keywords from the campaign config.

    The strategy is to combine the offer name and value proposition to create
    a seed list of terms, then generate 2 and 3-word combinations.
    """
    # Combine offer and value prop, clean, and split into unique terms
    seed_text = f"{config.offer_name} {config.value_proposition_primary}"
    words = re.findall(r"\b\w+\b", seed_text.lower())
    unique_words = sorted(list(set([w for w in words if len(w) > 2])))

    # Use a set to ensure keyword uniqueness
    keywords = set()

    # 1. Add the exact offer name
    keywords.add(config.offer_name.lower())

    # 2. Generate 2-word combinations (bigrams)
    if len(unique_words) >= 2:
        for i in range(len(unique_words)):
            for j in range(i + 1, len(unique_words)):
                keywords.add(f"{unique_words[i]} {unique_words[j]}")
                keywords.add(f"{unique_words[j]} {unique_words[i]}")

    # 3. Generate 3-word combinations (trigrams) if we need more
    if len(keywords) < 20 and len(unique_words) >= 3:
        for i in range(len(unique_words)):
            for j in range(i + 1, len(unique_words)):
                for k in range(j + 1, len(unique_words)):
                    keywords.add(f"{unique_words[i]} {unique_words[j]} {unique_words[k]}")

    # 4. Ensure we have between 10 and 30 keywords
    final_keywords = sorted(list(keywords))

    # If we have too few, add single words until we reach 10
    if len(final_keywords) < 10:
        for word in unique_words:
            if len(final_keywords) < 10:
                final_keywords.append(word)

    # If we have too many, slice the list to the max limit
    if len(final_keywords) > 30:
        final_keywords = final_keywords[:30]

    # Return as a list of Keyword objects
    return [Keyword(text=kw, match_type="PHRASE") for kw in final_keywords]
