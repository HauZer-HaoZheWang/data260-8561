from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class TrialCreate(BaseModel):
    brief_title: str = Field(min_length=1, max_length=500)
    sponsor: str = Field(min_length=1, max_length=255)


class TrialUpdate(BaseModel):
    brief_title: str = Field(min_length=1, max_length=500)
    sponsor: str = Field(min_length=1, max_length=255)


class TrialOut(BaseModel):
    id: int
    brief_title: str
    sponsor: str

    model_config = ConfigDict(from_attributes=True)
