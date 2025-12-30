from pydantic import BaseModel


class Persona(BaseModel):
    """
    Pydantic model for persona.
    """

    name: str
    description: str
