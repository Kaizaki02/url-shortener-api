"""Pydantic models: request validation and response shapes."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        # bcrypt only supports passwords up to 72 *bytes*.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password is too long (max 72 bytes)")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UrlCreate(BaseModel):
    target_url: HttpUrl
    custom_code: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_-]{4,20}$",
        description="Optional custom short code (4-20 letters, digits, - or _).",
    )


class UrlOut(BaseModel):
    code: str
    short_url: str
    target_url: str
    clicks: int
    created_at: datetime
