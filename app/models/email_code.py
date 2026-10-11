from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class EmailCode(Base):
    __tablename__ = "email_codes"
    __table_args__ = (UniqueConstraint("user_id", "purpose", name="uq_email_code_user_purpose"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose = Column(String, nullable=False)  # verify_email, password_reset
    code_hash = Column(String, nullable=False)  # HMAC: the code itself is never stored
    attempts = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
