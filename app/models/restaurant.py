from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    cuisine_type = Column(String, nullable=False, index=True)
    address = Column(String, nullable=False)
    lat = Column(Float)
    lng = Column(Float)
    rating = Column(Float, default=0)
    avg_delivery_minutes = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")
    menu_items = relationship("MenuItem", back_populates="restaurant", cascade="all, delete-orphan")
    discount_rule = relationship("DiscountRule", back_populates="restaurant", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="restaurant", cascade="all, delete-orphan")