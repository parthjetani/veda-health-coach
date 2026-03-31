from typing import Literal

from pydantic import BaseModel, field_validator


class AIResponse(BaseModel):
    type: Literal["product_check", "general_advice", "habit_advice", "unclear"]
    verdict: Literal["Safe", "Use with caution", "Avoid"] | None = None
    summary: str
    key_ingredients: list[str] = []
    explanation: str | None = None
    suggestion: str | None = None
    follow_up: str | None = None
    confidence: Literal["high", "medium", "low"]

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("summary must not be empty")
        return v.strip()

    @field_validator("key_ingredients", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        return v
