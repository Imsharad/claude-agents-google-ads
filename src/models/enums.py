from enum import Enum


class VerticalType(str, Enum):
    """Enum for the different vertical types of campaigns."""

    EDUCATION = "EDUCATION"
    SAAS = "SAAS"
    SERVICE = "SERVICE"
    E_COMMERCE = "E_COMMERCE"


class MonetizationModel(str, Enum):
    """Enum for the different monetization models of campaigns."""

    TRIPWIRE_UPSELL = "TRIPWIRE_UPSELL"
    DIRECT_SALE = "DIRECT_SALE"
    LEAD_GEN = "LEAD_GEN"
    BOOK_CALL = "BOOK_CALL"
