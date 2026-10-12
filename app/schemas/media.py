from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app import config

Filename = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class VideoUploadRequest(BaseModel):
    filename: Filename
    content_type: str
    size: int = Field(gt=0, le=config.VIDEO_MAX_BYTES)

    @field_validator("content_type")
    @classmethod
    def allowed_type(cls, value: str) -> str:
        if value not in config.VIDEO_TYPES:
            raise ValueError(f"Unsupported video type. Allowed: {', '.join(config.VIDEO_TYPES)}")
        return value


class MaterialUploadRequest(BaseModel):
    filename: Filename
    content_type: str
    size: int = Field(gt=0, le=config.MATERIAL_MAX_BYTES)

    @field_validator("content_type")
    @classmethod
    def allowed_type(cls, value: str) -> str:
        if value not in config.MATERIAL_TYPES:
            raise ValueError("Unsupported file type for materials")
        return value


class CoverUploadRequest(BaseModel):
    filename: Filename
    content_type: str
    size: int = Field(gt=0, le=config.COVER_MAX_BYTES)

    @field_validator("content_type")
    @classmethod
    def allowed_type(cls, value: str) -> str:
        if value not in config.COVER_TYPES:
            raise ValueError(f"Unsupported image type. Allowed: {', '.join(config.COVER_TYPES)}")
        return value


class ConfirmVideoRequest(BaseModel):
    upload_ticket: str = Field(min_length=1)


class ConfirmCoverRequest(BaseModel):
    upload_ticket: str = Field(min_length=1)


class ConfirmMaterialRequest(BaseModel):
    upload_ticket: str = Field(min_length=1)
    title: Title


class UploadInstructions(BaseModel):
    upload_url: str
    method: Literal["PUT"] = "PUT"
    headers: dict[str, str]
    upload_ticket: str
    expires_in: int


class SignedUrl(BaseModel):
    url: str
    expires_in: int
