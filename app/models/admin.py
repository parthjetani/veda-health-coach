from typing import Literal

from pydantic import BaseModel


# -- Flagged Ingredient (structured) --

class FlaggedIngredient(BaseModel):
    name: str
    reason: str | None = None
    risk: Literal["high", "medium", "low"] | None = None


# -- Health Items --

class HealthItemCreate(BaseModel):
    item_name: str
    brand: str | None = None
    category: Literal["food", "supplement", "personal_care", "household", "other"] | None = None
    ingredients: list[str] = []
    flagged_ingredients: list[FlaggedIngredient] = []
    risk_level: Literal["high", "medium", "low"] | None = None
    recommendation: str | None = None
    alternative_brand: str | None = None
    aliases: list[str] = []
    confidence_source: Literal["verified", "inferred", "community"] = "verified"
    barcode: str | None = None
    ewg_rating: str | None = None
    notes: str | None = None


class HealthItemUpdate(BaseModel):
    item_name: str | None = None
    brand: str | None = None
    category: Literal["food", "supplement", "personal_care", "household", "other"] | None = None
    ingredients: list[str] | None = None
    flagged_ingredients: list[FlaggedIngredient] | None = None
    risk_level: Literal["high", "medium", "low"] | None = None
    recommendation: str | None = None
    alternative_brand: str | None = None
    aliases: list[str] | None = None
    confidence_source: Literal["verified", "inferred", "community"] | None = None
    barcode: str | None = None
    ewg_rating: str | None = None
    notes: str | None = None


# -- Pagination --

class PaginatedResponse(BaseModel):
    data: list[dict]
    total: int
    page: int
    per_page: int
    pages: int
