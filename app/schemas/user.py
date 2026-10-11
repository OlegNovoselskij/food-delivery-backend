from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, model_validator


def _fits_bcrypt(value: str) -> str:
    if len(value.encode()) > 72:  # Cyrillic characters take 2 bytes each
        raise ValueError("Password is too long (max 72 bytes)")
    return value


def _normalize_code(value: Any) -> Any:
    # people type "482 913" or "482-913": keep only the ASCII digits
    return "".join(ch for ch in value if ch in "0123456789") if isinstance(value, str) else value


Password = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(_fits_bcrypt)]
Code = Annotated[str, BeforeValidator(_normalize_code), Field(pattern=r"^[0-9]{6}$")]


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    surname: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    bio: str | None = Field(default=None, max_length=1000)
    role: Literal["student", "teacher"] = "student"


class VerifyRegistrationRequest(BaseModel):
    email: EmailStr
    code: Code
    password: Password


class ResendCodeRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: Code
    new_password: Password


class MessageOut(BaseModel):
    message: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    surname: str
    email: EmailStr
    phone: str | None
    bio: str | None = None
    role: str
    email_verified: bool


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


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=8192)  # the ID token (JWT) issued by Google
    role: Literal["student", "teacher"] = "student"  # used only when a NEW account is created


class NonceOut(BaseModel):
    nonce: str
