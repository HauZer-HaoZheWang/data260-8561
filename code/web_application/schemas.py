from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    username: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default="reader", pattern="^(reader|writer|moderator)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    username: str | None = None
    role: str = "reader"

    model_config = ConfigDict(from_attributes=True)


class SponsorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_name: str = Field(min_length=1, max_length=255)
    email: EmailStr


class SponsorUpdate(SponsorCreate):
    pass


class SponsorOut(SponsorCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrialCreate(BaseModel):
    brief_title: str = Field(min_length=1, max_length=500)
    nct_code: str = Field(pattern=r"^NCT\d{8}$")
    participant_count: int = Field(default=0, ge=0)
    sponsor_id: int = Field(gt=0)


class TrialUpdate(BaseModel):
    brief_title: str = Field(min_length=1, max_length=500)
    nct_code: str = Field(pattern=r"^NCT\d{8}$")
    participant_count: int = Field(ge=0)
    sponsor_id: int = Field(gt=0)


class TrialOut(BaseModel):
    id: int
    brief_title: str
    nct_code: str
    participant_count: int
    sponsor_id: int
    sponsor: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
