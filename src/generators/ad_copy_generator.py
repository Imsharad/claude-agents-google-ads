"""
TASK-023: Implement Polarity Ad Copy Generator
"""

from typing import List, Literal
from jinja2 import Template
from pydantic import BaseModel, Field, field_validator
import instructor
from anthropic import Anthropic
import yaml
from pathlib import Path
from src.models.configuration import CampaignConfiguration
from src.generators.persona_generator import PersonaSchema

# Configure instructor with the Anthropic client
client = instructor.from_anthropic(Anthropic())

# Keyword blocklist for policy pre-checks
KEYWORD_BLOCKLIST = ["guarantee", "free", "100%", "risk-free"]


class AdCopySchema(BaseModel):
    """Pydantic model for a single ad copy variation."""

    headlines: List[str] = Field(..., min_length=3, max_length=15)
    descriptions: List[str] = Field(..., min_length=2, max_length=4)

    @field_validator("headlines")
    @classmethod
    def validate_headlines(cls, headlines):
        for h in headlines:
            if len(h) > 30:
                raise ValueError("Headline must be 30 characters or less.")
            if any(blocked in h.lower() for blocked in KEYWORD_BLOCKLIST):
                raise ValueError(f"Ad copy contains a blocked keyword: {h}")
        return headlines

    @field_validator("descriptions")
    @classmethod
    def validate_descriptions(cls, descriptions):
        for d in descriptions:
            if len(d) > 90:
                raise ValueError("Description must be 90 characters or less.")
            if any(blocked in d.lower() for blocked in KEYWORD_BLOCKLIST):
                raise ValueError(f"Ad copy contains a blocked keyword: {d}")
        return descriptions


class AdVariation(BaseModel):
    """Represents a single ad variation with a specific angle."""

    angle: Literal["PULL", "PUSH"]
    copy: AdCopySchema


def generate_polarity_ads(
    persona: PersonaSchema, config: CampaignConfiguration, max_retries: int = 3
) -> List[AdVariation]:
    """
    Generates two ad variations (Pull and Push) for a given persona.
    Includes a retry mechanism to handle validation errors from the LLM.
    """
    template_path = (
        Path(__file__).parent.parent.parent
        / "prompts"
        / "setup"
        / "generate_polarity_ads.yaml"
    )
    with open(template_path, "r") as f:
        templates = yaml.safe_load(f)

    ad_variations: List[AdVariation] = []

    for angle in ["PULL", "PUSH"]:
        template_str = templates[f"{angle.lower()}_template"]
        template = Template(template_str)

        prompt = template.render(
            persona=persona, config=config, keyword_blocklist=KEYWORD_BLOCKLIST
        )

        for attempt in range(max_retries):
            try:
                ad_copy = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                    response_model=AdCopySchema,
                )
                ad_variations.append(AdVariation(angle=angle, copy=ad_copy))
                break  # Success, exit retry loop
            except Exception as e:
                print(f"Validation failed on attempt {attempt + 1} for {angle} ad: {e}")
                if attempt + 1 == max_retries:
                    raise  # Re-raise the exception if all retries fail

    return ad_variations
