from pydantic import BaseModel, Field
from src.models.enums import MonetizationModel, VerticalType


class CampaignConfiguration(BaseModel):
    """
    Pydantic model for campaign configuration payload.
    """

    vertical_type: VerticalType
    offer_name: str = Field(..., max_length=200)
    target_audience_broad: str = Field(..., max_length=200)
    value_proposition_primary: str = Field(..., max_length=200)
    monetization_model: MonetizationModel
