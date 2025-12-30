"""
TASK-022: Implement Persona Generation with LLM
"""

from typing import List
from jinja2 import Template
from pydantic import BaseModel, Field
import instructor
from anthropic import Anthropic
from src.models.configuration import CampaignConfiguration
from pathlib import Path

# Configure instructor with the Anthropic client
# Note: The API key will be automatically picked up from the ANTHROPIC_API_KEY environment variable.
client = instructor.from_anthropic(Anthropic())


class PersonaSchema(BaseModel):
    name: str = Field(..., max_length=50)
    pain_point: str = Field(..., max_length=200)
    purchase_driver: str = Field(..., max_length=150)
    ad_group_name: str = Field(..., pattern=r"^persona_[a-z_]+$")


class PersonaListSchema(BaseModel):
    personas: List[PersonaSchema] = Field(..., min_length=3, max_length=3)


def generate_personas(config: CampaignConfiguration) -> PersonaListSchema:
    """
    Generates a list of three personas based on the campaign configuration.
    """
    template_path = (
        Path(__file__).parent.parent.parent
        / "prompts"
        / "setup"
        / "generate_personas.yaml"
    )

    with open(template_path, "r") as f:
        template_str = f.read()

    template = Template(template_str)
    prompt = template.render(config=config)

    # Generate the personas using the LLM and validate with the Pydantic schema
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        response_model=PersonaListSchema,
    )

    return response
