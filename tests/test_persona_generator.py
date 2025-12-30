"""
TASK-022: Add unit tests for the persona generator.
"""
import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from src.generators.persona_generator import generate_personas, PersonaListSchema
from src.models.configuration import CampaignConfiguration
from src.models.enums import VerticalType, MonetizationModel

@pytest.fixture
def mock_anthropic_client():
    """Fixture to mock the Anthropic client."""
    with patch('src.generators.persona_generator.client') as mock_client:
        yield mock_client

@pytest.fixture
def sample_config():
    """Provides a sample campaign configuration."""
    return CampaignConfiguration(
        vertical_type=VerticalType.SERVICE,
        offer_name="Cybersecurity Audit",
        target_audience_broad="Small business owners",
        value_proposition_primary="Protect your business from cyber threats",
        monetization_model=MonetizationModel.LEAD_GEN,
    )

def test_generate_personas_success(mock_anthropic_client: MagicMock, sample_config: CampaignConfiguration):
    """
    Tests successful persona generation with valid LLM output.
    """
    mock_response = PersonaListSchema(
        personas=[
            {
                "name": "Proactive Paul",
                "pain_point": "Worried about data breaches and regulatory fines.",
                "purchase_driver": "Wants peace of mind and a clear security roadmap.",
                "ad_group_name": "persona_proactive_paul",
            },
            {
                "name": "Reactive Rita",
                "pain_point": "Recently experienced a minor security incident.",
                "purchase_driver": "Needs to prevent future incidents from happening.",
                "ad_group_name": "persona_reactive_rita",
            },
            {
                "name": "Compliant Chris",
                "pain_point": "Struggles to keep up with industry compliance (e.g., GDPR, HIPAA).",
                "purchase_driver": "Needs to ensure the business meets all legal requirements.",
                "ad_group_name": "persona_compliant_chris",
            },
        ]
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    result = generate_personas(sample_config)

    assert isinstance(result, PersonaListSchema)
    assert len(result.personas) == 3
    assert result.personas[0].name == "Proactive Paul"
    mock_anthropic_client.messages.create.assert_called_once()

def test_generate_personas_validation_error(mock_anthropic_client: MagicMock, sample_config: CampaignConfiguration):
    """
    Tests that a Pydantic ValidationError is raised for invalid LLM output.
    """
    # Simulate the LLM returning data that doesn't match the schema
    # Pydantic and instructor will raise a ValidationError internally
    mock_anthropic_client.messages.create.side_effect = ValidationError.from_exception_data(
        title="PersonaListSchema",
        line_errors=[
            {
                "loc": ("personas", 0, "ad_group_name"),
                "msg": "String should match pattern '^persona_[a-z_]+$'",
                    "type": "string_pattern_mismatch",
                    "ctx": {"pattern": "^persona_[a-z_]+$"},
            }
        ],
    )

    with pytest.raises(ValidationError):
        generate_personas(sample_config)

    mock_anthropic_client.messages.create.assert_called_once()
