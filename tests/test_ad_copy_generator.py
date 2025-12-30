"""
Unit tests for the ad_copy_generator module.
"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError
from src.generators.ad_copy_generator import (
    generate_polarity_ads,
    AdCopySchema,
    AdVariation,
)
from src.generators.persona_generator import PersonaSchema
from src.models.configuration import CampaignConfiguration
from src.models.enums import VerticalType, MonetizationModel


@pytest.fixture
def mock_persona():
    """Provides a mock PersonaSchema object for tests."""
    return PersonaSchema(
        name="Test Persona",
        pain_point="Struggles with testing.",
        purchase_driver="Needs reliable code.",
        ad_group_name="persona_test_group",
    )


@pytest.fixture
def mock_config():
    """Provides a mock CampaignConfiguration object for tests."""
    return CampaignConfiguration(
        vertical_type=VerticalType.SAAS,
        offer_name="Test Offer",
        target_audience_broad="Developers",
        value_proposition_primary="Write better code.",
        monetization_model=MonetizationModel.DIRECT_SALE,
    )


@patch("src.generators.ad_copy_generator.client")
def test_generate_polarity_ads_success(mock_client, mock_persona, mock_config):
    """
    Tests successful generation of PULL and PUSH ad variations.
    """
    # Mock the response from the LLM client
    mock_pull_copy = AdCopySchema(
        headlines=["Unlock Potential", "Achieve Goals", "Success Awaits"],
        descriptions=["Our tool helps you succeed.", "Join thousands of happy users."],
    )
    mock_push_copy = AdCopySchema(
        headlines=["Don't Miss Out", "Limited Time Offer", "Act Now!"],
        descriptions=["Spots are filling up fast.", "Avoid the regret of waiting."],
    )

    # Configure the mock to return different values on subsequent calls
    mock_client.messages.create.side_effect = [mock_pull_copy, mock_push_copy]

    # Call the function
    ad_variations = generate_polarity_ads(mock_persona, mock_config)

    # Assertions
    assert len(ad_variations) == 2
    assert isinstance(ad_variations[0], AdVariation)
    assert ad_variations[0].angle == "PULL"
    assert ad_variations[0].copy.model_copy() == mock_pull_copy.model_copy()

    assert isinstance(ad_variations[1], AdVariation)
    assert ad_variations[1].angle == "PUSH"
    assert ad_variations[1].copy.model_copy() == mock_push_copy.model_copy()

    # Check that the client was called twice
    assert mock_client.messages.create.call_count == 2

    # Verify the content of the prompts passed to the client
    call_args = mock_client.messages.create.call_args_list

    # Check Pull Prompt
    pull_prompt = call_args[0].kwargs["messages"][0]["content"]
    assert 'ad copy using the "Pull" (Desire/Gain) angle' in pull_prompt
    assert "Name: Test Persona" in pull_prompt
    assert "Offer Name: Test Offer" in pull_prompt

    # Check Push Prompt
    push_prompt = call_args[1].kwargs["messages"][0]["content"]
    assert 'ad copy using the "Push" (Fear/FOMO) angle' in push_prompt
    assert "Name: Test Persona" in push_prompt
    assert "Offer Name: Test Offer" in push_prompt


def test_ad_copy_schema_validation():
    """
    Tests the validation rules within the AdCopySchema.
    """
    # Test valid data
    AdCopySchema(
        headlines=["Valid Headline"] * 3,
        descriptions=["Valid description."] * 2,
    )

    # Test headline too long
    with pytest.raises(ValidationError, match="Headline must be 30 characters or less"):
        AdCopySchema(
            headlines=["This is a headline that is way too long to be valid."] * 3,
            descriptions=["Valid description."] * 2,
        )

    # Test description too long
    with pytest.raises(
        ValidationError, match="Description must be 90 characters or less"
    ):
        AdCopySchema(
            headlines=["Valid Headline"] * 3,
            descriptions=[
                "This description is extremely long and will fail the validation check because it exceeds the ninety character limit."
            ]
            * 2,
        )

    # Test too few headlines
    with pytest.raises(ValidationError):
        AdCopySchema(headlines=["One"], descriptions=["Desc 1", "Desc 2"])

    # Test blocked keyword
    with pytest.raises(ValidationError, match="Ad copy contains a blocked keyword"):
        AdCopySchema(
            headlines=["A headline with a guarantee"] * 3,
            descriptions=["Valid description."] * 2,
        )

    with pytest.raises(ValidationError, match="Ad copy contains a blocked keyword"):
        AdCopySchema(
            headlines=["Valid Headline"] * 3,
            descriptions=["This is a risk-free offer.", "Another description."],
        )
