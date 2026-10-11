from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
        Index("ix_enrollments_course_status", "course_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="pending_payment", index=True)  # pending_payment, active, completed, cancelled
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    student = relationship("User")
    course = relationship("Course", back_populates="enrollments")
    payments = relationship(
        "Payment", back_populates="enrollment", cascade="all, delete-orphan", order_by="Payment.id"
    )
    progress = relationship("LessonProgress", back_populates="enrollment", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="enrollment", cascade="all, delete-orphan")
    certificate = relationship("Certificate", back_populates="enrollment", uselist=False, cascade="all, delete-orphan")

    @property
    def payment(self) -> "Payment | None":
        return self.payments[-1] if self.payments else None


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_status_created", "status", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, succeeded, failed, refunded
    transaction_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    enrollment = relationship("Enrollment", back_populates="payments")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("enrollment_id", "lesson_id", name="uq_progress_enrollment_lesson"),)

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    enrollment = relationship("Enrollment", back_populates="progress")
    lesson = relationship("Lesson")


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), unique=True, nullable=False)
    certificate_number = Column(String, unique=True, nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())

    enrollment = relationship("Enrollment", back_populates="certificate")