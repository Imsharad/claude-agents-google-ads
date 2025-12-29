"""
TASK-026: Implement Text-Only Upsell Script Generator
"""

import yaml
from jinja2 import Template
from pydantic import BaseModel, Field
from src.models.configuration import CampaignConfiguration
from pathlib import Path


class UpsellScript(BaseModel):
    hook: str = Field(..., max_length=100)
    transition: str = Field(..., max_length=300)
    cta: str = Field(..., max_length=50)
    urgency_element: str = Field(..., max_length=100)


def generate_upsell_script(config: CampaignConfiguration) -> UpsellScript:
    """
    Generates an upsell script based on the campaign configuration.
    """
    # Use pathlib to construct a robust path to the template file
    template_path = (
        Path(__file__).parent.parent.parent
        / "prompts"
        / "setup"
        / "generate_upsell_script.yaml"
    )

    with open(template_path, "r") as f:
        template_str = f.read()

    template = Template(template_str)
    rendered_script_str = template.render(config=config)

    # The rendered output is a string, which needs to be parsed as YAML
    # and then loaded into the Pydantic model.
    # We need to filter out the comments before parsing.
    lines = [
        line
        for line in rendered_script_str.strip().split("\n")
        if not line.strip().startswith("#")
    ]

    script_data = yaml.safe_load("\n".join(lines))

    return UpsellScript(**script_data)
