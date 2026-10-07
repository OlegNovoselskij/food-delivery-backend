from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from typing import Literal


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    surname: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    phone: str | None = Field(default=None, max_length=20)
    role: Literal["student", "teacher"] = "student"
    bio: str | None = Field(default=None, max_length=1000)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        if len(v.encode()) > 72:  # кирилиця це 2 байти на символ
            raise ValueError("Password is too long (max 72 bytes)")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    surname: str
    email: EmailStr
    phone: str | None
    role: str
    bio: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    surname: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    bio: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def required_fields_not_null(self):
        for field in ("name", "surname"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

