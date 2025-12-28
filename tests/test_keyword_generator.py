"""
TASK-013: Keyword Strategy Generator Tests

These tests define the expected behavior for the keyword generator.
Tests are written BEFORE implementation (Test-Driven Development).

Run with: pytest tests/test_keyword_generator.py -v

Note: Tests will be SKIPPED until TASK-013 implementation exists.
"""

import pytest

# Skip entire module if generators don't exist yet (TDD pattern)
pytest.importorskip(
    "src.generators.keyword_generator", reason="TASK-013 not implemented"
)

from src.generators.keyword_generator import generate_keywords, Keyword  # noqa: E402
from src.generators.negative_keywords import (  # noqa: E402
    get_universal_negatives,
    generate_vertical_negatives,
)
from src.models.configuration import CampaignConfiguration  # noqa: E402
from src.models.enums import VerticalType, MonetizationModel  # noqa: E402


class TestKeywordGeneration:
    """Test keyword generation from campaign configuration."""

    @pytest.fixture
    def education_config(self) -> CampaignConfiguration:
        """Sample education vertical configuration."""
        return CampaignConfiguration(
            vertical_type=VerticalType.EDUCATION,
            offer_name="AI Workshop",
            target_audience_broad="Mid-Career Professionals",
            value_proposition_primary="Master AI tools in 2 hours",
            monetization_model=MonetizationModel.TRIPWIRE_UPSELL,
        )

    @pytest.fixture
    def saas_config(self) -> CampaignConfiguration:
        """Sample SaaS vertical configuration."""
        return CampaignConfiguration(
            vertical_type=VerticalType.SAAS,
            offer_name="CRM Tool",
            target_audience_broad="Sales VPs",
            value_proposition_primary="Close more deals faster",
            monetization_model=MonetizationModel.DIRECT_SALE,
        )

    @pytest.fixture
    def service_config(self) -> CampaignConfiguration:
        """Sample service vertical configuration."""
        return CampaignConfiguration(
            vertical_type=VerticalType.SERVICE,
            offer_name="Dental Implants",
            target_audience_broad="Adults 40+",
            value_proposition_primary="Restore your smile confidently",
            monetization_model=MonetizationModel.LEAD_GEN,
        )

    def test_generate_keywords_returns_list(self, education_config):
        """Keywords should return a list of Keyword objects."""
        keywords = generate_keywords(education_config)
        assert isinstance(keywords, list)
        assert all(isinstance(k, Keyword) for k in keywords)

    def test_generate_keywords_count_range(self, education_config):
        """Should return between 10-30 keyword candidates."""
        keywords = generate_keywords(education_config)
        assert (
            10 <= len(keywords) <= 30
        ), f"Expected 10-30 keywords, got {len(keywords)}"

    def test_keyword_has_phrase_match_type(self, education_config):
        """All keywords should use PHRASE match type."""
        keywords = generate_keywords(education_config)
        for keyword in keywords:
            assert (
                keyword.match_type == "PHRASE"
            ), f"Expected PHRASE, got {keyword.match_type}"

    def test_keywords_derived_from_offer_name(self, education_config):
        """Keywords should include terms from offer_name."""
        keywords = generate_keywords(education_config)
        keyword_texts = [k.text.lower() for k in keywords]

        # At least one keyword should contain "ai" or "workshop"
        has_offer_term = any(
            "ai" in text or "workshop" in text for text in keyword_texts
        )
        assert has_offer_term, "Keywords should derive from offer_name"

    def test_keywords_derived_from_value_proposition(self, saas_config):
        """Keywords should include terms from value proposition."""
        keywords = generate_keywords(saas_config)
        keyword_texts = [k.text.lower() for k in keywords]

        # At least one keyword should relate to value proposition
        has_value_term = any(
            "deal" in text or "crm" in text or "sales" in text for text in keyword_texts
        )
        assert has_value_term, "Keywords should derive from value_proposition"

    def test_keywords_unique(self, education_config):
        """All keywords should be unique."""
        keywords = generate_keywords(education_config)
        keyword_texts = [k.text.lower() for k in keywords]
        assert len(keyword_texts) == len(
            set(keyword_texts)
        ), "Keywords should be unique"

    def test_keyword_not_empty(self, education_config):
        """Keywords should not have empty text."""
        keywords = generate_keywords(education_config)
        for keyword in keywords:
            assert keyword.text.strip(), "Keyword text should not be empty"


class TestKeywordModel:
    """Test the Keyword dataclass/model."""

    def test_keyword_has_required_fields(self):
        """Keyword should have text and match_type fields."""
        keyword = Keyword(text="ai workshop", match_type="PHRASE")
        assert hasattr(keyword, "text")
        assert hasattr(keyword, "match_type")

    def test_keyword_text_is_string(self):
        """Keyword text should be a string."""
        keyword = Keyword(text="test keyword", match_type="PHRASE")
        assert isinstance(keyword.text, str)


class TestUniversalNegatives:
    """Test universal negative keyword list."""

    def test_universal_negatives_returns_list(self):
        """Should return a list of strings."""
        negatives = get_universal_negatives()
        assert isinstance(negatives, list)
        assert all(isinstance(n, str) for n in negatives)

    def test_universal_negatives_contains_required_terms(self):
        """Should include standard negative terms from PRD."""
        negatives = get_universal_negatives()
        required_terms = [
            "free",
            "cheap",
            "crack",
            "torrent",
            "download",
            "job",
            "career",
            "hiring",
            "apply",
        ]

        for term in required_terms:
            assert term in negatives, f"Missing required negative: {term}"

    def test_universal_negatives_minimum_count(self):
        """Should have at least 9 universal negatives (per PRD REQ-9)."""
        negatives = get_universal_negatives()
        assert len(negatives) >= 9


class TestVerticalNegatives:
    """Test vertical-specific negative keyword generation."""

    def test_generate_vertical_negatives_education(self):
        """Education vertical should generate specific negatives."""
        negatives = generate_vertical_negatives(VerticalType.EDUCATION)
        assert isinstance(negatives, list)
        assert (
            len(negatives) >= 10
        ), "Should generate minimum 10 vertical-specific negatives"

    def test_generate_vertical_negatives_saas(self):
        """SaaS vertical should generate specific negatives."""
        negatives = generate_vertical_negatives(VerticalType.SAAS)
        assert isinstance(negatives, list)
        assert len(negatives) >= 10

    def test_generate_vertical_negatives_service(self):
        """Service vertical should generate specific negatives."""
        negatives = generate_vertical_negatives(VerticalType.SERVICE)
        assert isinstance(negatives, list)
        assert len(negatives) >= 10

    def test_vertical_negatives_are_strings(self):
        """Vertical negatives should all be strings."""
        negatives = generate_vertical_negatives(VerticalType.EDUCATION)
        assert all(isinstance(n, str) for n in negatives)

    def test_vertical_negatives_not_empty(self):
        """Vertical negatives should not have empty strings."""
        negatives = generate_vertical_negatives(VerticalType.SAAS)
        for neg in negatives:
            assert neg.strip(), "Negative keyword should not be empty"
