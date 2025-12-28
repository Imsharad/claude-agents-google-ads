"""
Pytest configuration and shared fixtures.

This file contains fixtures that are shared across multiple test modules.
"""

import pytest


# Note: These fixtures will work once TASK-012 implements the models.
# Until then, imports will fail and tests will be skipped/fail as expected.


@pytest.fixture
def sample_education_config_data() -> dict:
    """Raw data for education vertical configuration."""
    return {
        "vertical_type": "EDUCATION",
        "offer_name": "AI Workshop",
        "target_audience_broad": "Mid-Career Professionals seeking AI skills",
        "value_proposition_primary": "Master AI tools in just 2 hours",
        "monetization_model": "TRIPWIRE_UPSELL",
    }


@pytest.fixture
def sample_saas_config_data() -> dict:
    """Raw data for SaaS vertical configuration."""
    return {
        "vertical_type": "SAAS",
        "offer_name": "CRM Tool",
        "target_audience_broad": "Sales VPs at mid-market companies",
        "value_proposition_primary": "Close more deals faster with AI-powered insights",
        "monetization_model": "DIRECT_SALE",
    }


@pytest.fixture
def sample_service_config_data() -> dict:
    """Raw data for service vertical configuration."""
    return {
        "vertical_type": "SERVICE",
        "offer_name": "Dental Implants",
        "target_audience_broad": "Adults 40+ seeking dental restoration",
        "value_proposition_primary": "Restore your smile with confidence",
        "monetization_model": "LEAD_GEN",
    }


@pytest.fixture
def sample_ecommerce_config_data() -> dict:
    """Raw data for e-commerce vertical configuration."""
    return {
        "vertical_type": "E_COMMERCE",
        "offer_name": "Organic Skincare Set",
        "target_audience_broad": "Health-conscious women 25-45",
        "value_proposition_primary": "Natural beauty without harmful chemicals",
        "monetization_model": "DIRECT_SALE",
    }


# Budget-related fixtures
@pytest.fixture
def standard_budget() -> int:
    """Standard Growth-Tier budget: ₹20,000."""
    return 20000


@pytest.fixture
def minimum_budget() -> int:
    """Minimum allowed budget: ₹10,000."""
    return 10000


@pytest.fixture
def standard_duration() -> int:
    """Standard campaign duration: 30 days."""
    return 30


@pytest.fixture
def growth_tier_duration() -> int:
    """Growth-Tier protocol duration: 60 days."""
    return 60
