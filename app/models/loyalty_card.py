from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class LoyaltyCard(Base):
    __tablename__ = "loyalty_cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    card_type = Column(String, nullable=False, default="regular")  # regular, gold, social
    bonus_points = Column(Integer, nullable=False, default=0)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")