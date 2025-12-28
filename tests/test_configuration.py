import pytest
from pydantic import ValidationError

from src.models.configuration import CampaignConfiguration
from src.models.enums import MonetizationModel, VerticalType


def test_valid_campaign_configuration():
    """
    Tests that a valid campaign configuration is parsed correctly.
    """
    config = CampaignConfiguration(
        vertical_type=VerticalType.SAAS,
        offer_name="CRM Tool",
        target_audience_broad="Sales VPs",
        value_proposition_primary="Increase revenue",
        monetization_model=MonetizationModel.LEAD_GEN,
    )
    assert config.vertical_type == VerticalType.SAAS
    assert config.offer_name == "CRM Tool"
    assert config.target_audience_broad == "Sales VPs"
    assert config.value_proposition_primary == "Increase revenue"
    assert config.monetization_model == MonetizationModel.LEAD_GEN


def test_invalid_vertical_type():
    """
    Tests that an invalid vertical type raises a validation error.
    """
    with pytest.raises(ValidationError):
        CampaignConfiguration(
            vertical_type="INVALID_VERTICAL",
            offer_name="CRM Tool",
            target_audience_broad="Sales VPs",
            value_proposition_primary="Increase revenue",
            monetization_model=MonetizationModel.LEAD_GEN,
        )


def test_invalid_monetization_model():
    """
    Tests that an invalid monetization model raises a validation error.
    """
    with pytest.raises(ValidationError):
        CampaignConfiguration(
            vertical_type=VerticalType.SAAS,
            offer_name="CRM Tool",
            target_audience_broad="Sales VPs",
            value_proposition_primary="Increase revenue",
            monetization_model="INVALID_MODEL",
        )


def test_string_length_validation():
    """
    Tests that string length validation is enforced.
    """
    long_string = "a" * 201
    with pytest.raises(ValidationError):
        CampaignConfiguration(
            vertical_type=VerticalType.SAAS,
            offer_name=long_string,
            target_audience_broad="Sales VPs",
            value_proposition_primary="Increase revenue",
            monetization_model=MonetizationModel.LEAD_GEN,
        )

    with pytest.raises(ValidationError):
        CampaignConfiguration(
            vertical_type=VerticalType.SAAS,
            offer_name="CRM Tool",
            target_audience_broad=long_string,
            value_proposition_primary="Increase revenue",
            monetization_model=MonetizationModel.LEAD_GEN,
        )

    with pytest.raises(ValidationError):
        CampaignConfiguration(
            vertical_type=VerticalType.SAAS,
            offer_name="CRM Tool",
            target_audience_broad="Sales VPs",
            value_proposition_primary=long_string,
            monetization_model=MonetizationModel.LEAD_GEN,
        )


def test_missing_required_fields():
    """
    Tests that missing required fields raise a validation error.
    """
    with pytest.raises(ValidationError):
        CampaignConfiguration(
            vertical_type=VerticalType.SAAS,
            target_audience_broad="Sales VPs",
            value_proposition_primary="Increase revenue",
            monetization_model=MonetizationModel.LEAD_GEN,
        )
