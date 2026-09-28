from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base


class Courier(Base):
    __tablename__ = "couriers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    is_available = Column(Boolean, nullable=False, default=True)