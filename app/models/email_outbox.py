from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    __table_args__ = (Index("ix_email_outbox_due", "status", "next_attempt_at"),)

    id = Column(Integer, primary_key=True)
    to_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    text_body = Column(Text)  # cleared after a successful send: the body may contain one-time codes
    html_body = Column(Text)
    status = Column(String, nullable=False, default="pending")  # pending, sent, failed
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_error = Column(String)
    dedupe_key = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True))
