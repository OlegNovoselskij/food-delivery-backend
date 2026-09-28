from sqlalchemy import Column, Integer, String, Numeric
from app.database import Base


class DeliveryOption(Base):
    __tablename__ = "delivery_options"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # standard, express, pickup
    base_fee = Column(Numeric(10, 2), nullable=False, default=0)
    estimated_minutes = Column(Integer)