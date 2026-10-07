from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), unique=True, nullable=False)
    title = Column(String, nullable=False)
    passing_score = Column(Integer, nullable=False, default=60)  # відсотків

    module = relationship("Module", back_populates="quiz")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan", order_by="Question.position")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    question_type = Column(String, nullable=False, default="single_choice")  # single_choice, multiple_choice, open_text
    points = Column(Integer, nullable=False, default=1)
    position = Column(Integer, nullable=False, default=0)

    quiz = relationship("Quiz", back_populates="questions")
    options = relationship("AnswerOption", back_populates="question", cascade="all, delete-orphan")


class AnswerOption(Base):
    __tablename__ = "answer_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)

    question = relationship("Question", back_populates="options")