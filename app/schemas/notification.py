from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationFilters(BaseModel):
    unread: bool = False
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    body: str
    payload: dict
    is_read: bool
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    unread_count: int
    page: int
    size: int


class UnreadCountOut(BaseModel):
    count: int


class MarkAllReadOut(BaseModel):
    updated: int


class WsTicketOut(BaseModel):
    ticket: str
    expires_in: int
