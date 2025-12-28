"""
TASK-015: Example Configuration Tests

These tests validate that example configuration files exist and
are valid according to the CampaignConfiguration Pydantic model.
Tests are written BEFORE implementation (Test-Driven Development).

Run with: pytest tests/test_example_configs.py -v

Note: Tests will be SKIPPED until TASK-015 implementation exists.
"""

import json
from pathlib import Path

import pytest

# Path to examples directory
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# Skip entire module if examples directory doesn't exist yet (TDD pattern)
if not EXAMPLES_DIR.exists():
    pytest.skip("TASK-015 not implemented (examples/ directory missing)", allow_module_level=True)

# These imports require TASK-012 to be complete
from src.models.configuration import CampaignConfiguration  # noqa: E402
from src.models.enums import VerticalType, MonetizationModel  # noqa: E402


class TestExampleFilesExist:
    """Test that all required example files exist."""

    def test_examples_directory_exists(self):
        """Examples directory should exist."""
        assert EXAMPLES_DIR.exists(), f"Missing directory: {EXAMPLES_DIR}"
        assert EXAMPLES_DIR.is_dir(), f"Not a directory: {EXAMPLES_DIR}"

    def test_workshop_config_exists(self):
        """Education vertical example (workshop) should exist."""
        config_path = EXAMPLES_DIR / "workshop_config.json"
        assert config_path.exists(), f"Missing: {config_path}"

    def test_dentist_config_exists(self):
        """Service vertical example (dentist) should exist."""
        config_path = EXAMPLES_DIR / "dentist_config.json"
        assert config_path.exists(), f"Missing: {config_path}"

    def test_saas_config_exists(self):
        """SaaS vertical example should exist."""
        config_path = EXAMPLES_DIR / "saas_config.json"
        assert config_path.exists(), f"Missing: {config_path}"


class TestExampleFilesValidJson:
    """Test that example files contain valid JSON."""

    @pytest.fixture
    def workshop_config_path(self) -> Path:
        return EXAMPLES_DIR / "workshop_config.json"

    @pytest.fixture
    def dentist_config_path(self) -> Path:
        return EXAMPLES_DIR / "dentist_config.json"

    @pytest.fixture
    def saas_config_path(self) -> Path:
        return EXAMPLES_DIR / "saas_config.json"

    def test_workshop_config_valid_json(self, workshop_config_path):
        """Workshop config should be valid JSON."""
        with open(workshop_config_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_dentist_config_valid_json(self, dentist_config_path):
        """Dentist config should be valid JSON."""
        with open(dentist_config_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_saas_config_valid_json(self, saas_config_path):
        """SaaS config should be valid JSON."""
        with open(saas_config_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)


class TestWorkshopConfigValidation:
    """Test that workshop config passes Pydantic validation."""

    @pytest.fixture
    def workshop_config(self) -> dict:
        """Load workshop configuration from file."""
        config_path = EXAMPLES_DIR / "workshop_config.json"
        with open(config_path) as f:
            return json.load(f)

    def test_workshop_config_validates(self, workshop_config):
        """Workshop config should pass CampaignConfiguration validation."""
        config = CampaignConfiguration(**workshop_config)
        assert config is not None

    def test_workshop_config_vertical_is_education(self, workshop_config):
        """Workshop should be EDUCATION vertical."""
        config = CampaignConfiguration(**workshop_config)
        assert config.vertical_type == VerticalType.EDUCATION

    def test_workshop_config_has_offer_name(self, workshop_config):
        """Workshop should have a meaningful offer name."""
        config = CampaignConfiguration(**workshop_config)
        assert config.offer_name
        assert len(config.offer_name) > 0

    def test_workshop_config_monetization_model(self, workshop_config):
        """Workshop should use TRIPWIRE_UPSELL model (per PRD Section 5)."""
        config = CampaignConfiguration(**workshop_config)
        assert config.monetization_model == MonetizationModel.TRIPWIRE_UPSELL


class TestDentistConfigValidation:
    """Test that dentist config passes Pydantic validation."""

    @pytest.fixture
    def dentist_config(self) -> dict:
        """Load dentist configuration from file."""
        config_path = EXAMPLES_DIR / "dentist_config.json"
        with open(config_path) as f:
            return json.load(f)

    def test_dentist_config_validates(self, dentist_config):
        """Dentist config should pass CampaignConfiguration validation."""
        config = CampaignConfiguration(**dentist_config)
        assert config is not None

    def test_dentist_config_vertical_is_service(self, dentist_config):
        """Dentist should be SERVICE vertical."""
        config = CampaignConfiguration(**dentist_config)
        assert config.vertical_type == VerticalType.SERVICE

    def test_dentist_config_has_offer_name(self, dentist_config):
        """Dentist should have a meaningful offer name."""
        config = CampaignConfiguration(**dentist_config)
        assert config.offer_name
        assert len(config.offer_name) > 0

    def test_dentist_config_monetization_model(self, dentist_config):
        """Dentist should use LEAD_GEN model (per PRD Section 5)."""
        config = CampaignConfiguration(**dentist_config)
        assert config.monetization_model == MonetizationModel.LEAD_GEN


class TestSaaSConfigValidation:
    """Test that SaaS config passes Pydantic validation."""

    @pytest.fixture
    def saas_config(self) -> dict:
        """Load SaaS configuration from file."""
        config_path = EXAMPLES_DIR / "saas_config.json"
        with open(config_path) as f:
            return json.load(f)

    def test_saas_config_validates(self, saas_config):
        """SaaS config should pass CampaignConfiguration validation."""
        config = CampaignConfiguration(**saas_config)
        assert config is not None

    def test_saas_config_vertical_is_saas(self, saas_config):
        """SaaS config should be SAAS vertical."""
        config = CampaignConfiguration(**saas_config)
        assert config.vertical_type == VerticalType.SAAS

    def test_saas_config_has_offer_name(self, saas_config):
        """SaaS should have a meaningful offer name."""
        config = CampaignConfiguration(**saas_config)
        assert config.offer_name
        assert len(config.offer_name) > 0

    def test_saas_config_monetization_model(self, saas_config):
        """SaaS should use DIRECT_SALE model (Free Trial per PRD Section 5)."""
        config = CampaignConfiguration(**saas_config)
        # PRD says "Free Trial Model" which maps to DIRECT_SALE
        assert config.monetization_model == MonetizationModel.DIRECT_SALE


class TestConfigurationCompleteness:
    """Test that all configurations have all required fields."""

    @pytest.fixture(params=["workshop_config.json", "dentist_config.json", "saas_config.json"])
    def config_data(self, request) -> dict:
        """Load each configuration file."""
        config_path = EXAMPLES_DIR / request.param
        with open(config_path) as f:
            return json.load(f)

    def test_config_has_vertical_type(self, config_data):
        """All configs should have vertical_type."""
        assert "vertical_type" in config_data

    def test_config_has_offer_name(self, config_data):
        """All configs should have offer_name."""
        assert "offer_name" in config_data

    def test_config_has_target_audience(self, config_data):
        """All configs should have target_audience_broad."""
        assert "target_audience_broad" in config_data

    def test_config_has_value_proposition(self, config_data):
        """All configs should have value_proposition_primary."""
        assert "value_proposition_primary" in config_data

    def test_config_has_monetization_model(self, config_data):
        """All configs should have monetization_model."""
        assert "monetization_model" in config_data


class TestConfigurationContent:
    """Test that configurations have meaningful content."""

    @pytest.fixture(params=["workshop_config.json", "dentist_config.json", "saas_config.json"])
    def config(self, request) -> CampaignConfiguration:
        """Load and validate each configuration."""
        config_path = EXAMPLES_DIR / request.param
        with open(config_path) as f:
            data = json.load(f)
        return CampaignConfiguration(**data)

    def test_offer_name_not_placeholder(self, config):
        """Offer name should not be a placeholder like 'TBD' or 'TODO'."""
        assert config.offer_name.lower() not in ["tbd", "todo", "placeholder", "example"]

    def test_target_audience_descriptive(self, config):
        """Target audience should be descriptive (> 10 chars)."""
        assert len(config.target_audience_broad) > 10

    def test_value_proposition_descriptive(self, config):
        """Value proposition should be descriptive (> 10 chars)."""
        assert len(config.value_proposition_primary) > 10

    def test_value_proposition_max_length(self, config):
        """Value proposition should respect max length (200 chars per PRD)."""
        assert len(config.value_proposition_primary) <= 200
