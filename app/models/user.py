from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import expression, func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String)  # null until the registration is confirmed
    phone = Column(String)
    bio = Column(Text)
    role = Column(String, nullable=False, default="student")  # student, teacher, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    email_verified = Column(Boolean, nullable=False, default=False, server_default=expression.false())
    password_changed_at = Column(DateTime(timezone=True))  # tokens issued before this moment stop working

    def __str__(self) -> str:
        return f"{self.name} {self.surname} <{self.email}>"
