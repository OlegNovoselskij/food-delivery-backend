from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="in_progress")  # in_progress, pending_review, graded
    score = Column(Integer)  # percent, filled when graded
    points_earned = Column(Integer)
    points_total = Column(Integer)
    passed = Column(Boolean)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True))

    enrollment = relationship("Enrollment", back_populates="attempts")
    quiz = relationship("Quiz")
    answers = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),)

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    selected_option_ids = Column(ARRAY(Integer), nullable=False, default=list)
    text_answer = Column(Text)
    is_correct = Column(Boolean)  # null while an open answer waits for the teacher
    points_awarded = Column(Integer)  # null while an open answer waits for the teacher
    teacher_comment = Column(Text)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question")
