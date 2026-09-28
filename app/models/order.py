from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    delivery_option_id = Column(Integer, ForeignKey("delivery_options.id"), nullable=False)
    courier_id = Column(Integer, ForeignKey("couriers.id"), nullable=True)
    delivery_address = Column(String)
    delivery_lat = Column(Float)
    delivery_lng = Column(Float)
    status = Column(String, nullable=False, default="created")  # created, cooking, delivering, delivered, cancelled
    payment_method = Column(String, nullable=False)  # online, cash
    payment_status = Column(String, nullable=False, default="pending")  # pending, paid, failed
    discount_applied = Column(Numeric(10, 2), nullable=False, default=0)
    bonus_points_used = Column(Integer, nullable=False, default=0)
    total_price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    restaurant = relationship("Restaurant")
    delivery_option = relationship("DeliveryOption")
    courier = relationship("Courier")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")