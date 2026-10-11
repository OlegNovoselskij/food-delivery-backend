from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    courses = relationship("Course", back_populates="category")

    def __str__(self) -> str:
        return self.name


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    level = Column(String, nullable=False, default="beginner", index=True)  # beginner, intermediate, advanced
    price = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(String, nullable=False, default="draft", index=True)  # draft, published, archived
    cover_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    teacher = relationship("User")
    category = relationship("Category", back_populates="courses")
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan", order_by="Module.position")
    reviews = relationship("Review", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course")

    def __str__(self) -> str:
        return self.title


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan", order_by="Lesson.position")
    quiz = relationship("Quiz", back_populates="module", uselist=False, cascade="all, delete-orphan")

    @property
    def has_quiz(self) -> bool:
        return self.quiz is not None


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    lesson_type = Column(String, nullable=False, default="video")  # video, article
    video_key = Column(String)
    video_size = Column(BigInteger)
    content = Column(Text)
    duration_minutes = Column(Integer)
    position = Column(Integer, nullable=False, default=0)
    is_preview = Column(Boolean, nullable=False, default=False)

    module = relationship("Module", back_populates="lessons")
    materials = relationship("LessonMaterial", back_populates="lesson", cascade="all, delete-orphan")

    @property
    def has_video(self) -> bool:
        return self.video_key is not None


class LessonMaterial(Base):
    __tablename__ = "lesson_materials"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    file_key = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    content_type = Column(String)
    size_bytes = Column(BigInteger)

    lesson = relationship("Lesson", back_populates="materials")
