
import pytest
from src.generators.upsell_generator import generate_upsell_script, UpsellScript
from src.models.configuration import CampaignConfiguration
from src.models.enums import MonetizationModel, VerticalType

@pytest.fixture
def base_config():
    return CampaignConfiguration(
        vertical_type=VerticalType.SAAS,
        offer_name="AI Copywriter Pro",
        target_audience_broad="Marketing agencies",
        value_proposition_primary="write ad copy 10x faster",
        monetization_model=MonetizationModel.DIRECT_SALE,
    )

def test_tripwire_upsell_script(base_config):
    base_config.monetization_model = MonetizationModel.TRIPWIRE_UPSELL
    script = generate_upsell_script(base_config)
    assert isinstance(script, UpsellScript)
    assert "Now that you've secured the AI Copywriter Pro" in script.hook
    assert "upcoming live webinar" in script.transition
    assert script.cta == "Register for the Free Training"
    assert "Limited spots are available" in script.urgency_element

def test_direct_sale_script(base_config):
    base_config.monetization_model = MonetizationModel.DIRECT_SALE
    script = generate_upsell_script(base_config)
    assert isinstance(script, UpsellScript)
    assert "Interested in how AI Copywriter Pro" in script.hook
    assert "achieve write ad copy 10x faster" in script.transition
    assert script.cta == "Book a 15-Minute Demo"
    assert "calendars fill up quickly" in script.urgency_element

def test_lead_gen_script(base_config):
    base_config.monetization_model = MonetizationModel.LEAD_GEN
    script = generate_upsell_script(base_config)
    assert isinstance(script, UpsellScript)
    assert "Thanks for downloading the guide to AI Copywriter Pro" in script.hook
    assert "build a custom action plan" in script.transition
    assert script.cta == "Claim Your Free Consultation"
    assert "only offer a handful" in script.urgency_element

def test_book_call_script(base_config):
    base_config.monetization_model = MonetizationModel.BOOK_CALL
    script = generate_upsell_script(base_config)
    assert isinstance(script, UpsellScript)
    assert "Ready to take the next step" in script.hook
    assert "The fastest way to get clarity" in script.transition
    assert script.cta == "Pick a Time on My Calendar"
    assert "My calendar is open" in script.urgency_element

def test_fallback_script(base_config):
    base_config.monetization_model = "INVALID_MODEL" # type: ignore
    script = generate_upsell_script(base_config)
    assert isinstance(script, UpsellScript)
    assert "Take the next step" in script.hook
    assert "achieve write ad copy 10x faster" in script.transition
    assert script.cta == "Learn More"
    assert "special offer is available" in script.urgency_element
