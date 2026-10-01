import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Language = Literal["en", "ur", "roman"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(StrictModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=200)

    @field_validator("email")
    @classmethod
    def email_format(cls, value):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Use a valid email address")
        return value.casefold()


class Register(Login):
    name: str = Field(min_length=2, max_length=100)
    language: Language = "en"


class Preferences(StrictModel):
    language: Language


class AttemptCreate(StrictModel):
    case_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")
    language: Language = "en"


class Draft(StrictModel):
    profile: str = Field(default="", max_length=8000)
    observations: str = Field(default="", max_length=8000)
    goals: str = Field(default="", max_length=8000)
    rationale: str = Field(default="", max_length=8000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)


class Plan(Draft):
    profile: str = Field(min_length=10, max_length=8000)
    observations: str = Field(min_length=10, max_length=8000)
    goals: str = Field(min_length=10, max_length=8000)
    rationale: str = Field(min_length=10, max_length=8000)


class MessageCreate(StrictModel):
    text: str = Field(min_length=1, max_length=3000)


class AnalysisCreate(StrictModel):
    asset_id: str = Field(min_length=1, max_length=100)


class Review(StrictModel):
    comment: str = Field(min_length=10, max_length=5000)
    scores: dict[str, int] = Field(default_factory=dict, max_length=4)


class Publish(StrictModel):
    review_note: str = Field(min_length=20, max_length=5000)


class CaseInput(StrictModel):
    case: dict


class ConsentInput(StrictModel):
    granted: bool


class RoleChange(StrictModel):
    role: Literal["student", "educator"]
