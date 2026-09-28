from sqlalchemy import Column, Integer, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), unique=True, nullable=False)
    min_orders = Column(Integer, nullable=False)
    period_days = Column(Integer, nullable=False)
    discount_percent = Column(Numeric(5, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    restaurant = relationship("Restaurant", back_populates="discount_rule")