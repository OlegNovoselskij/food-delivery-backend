from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.catalog import Course, Lesson, Module
from app.models.quiz import Quiz


@dataclass(frozen=True)
class ProgressStats:
    lessons_total: int = 0
    lessons_done: int = 0
    quizzes_total: int = 0
    quizzes_done: int = 0
    minutes_total: int = 0
    minutes_done: int = 0

    def __add__(self, other: "ProgressStats") -> "ProgressStats":
        return ProgressStats(
            lessons_total=self.lessons_total + other.lessons_total,
            lessons_done=self.lessons_done + other.lessons_done,
            quizzes_total=self.quizzes_total + other.quizzes_total,
            quizzes_done=self.quizzes_done + other.quizzes_done,
            minutes_total=self.minutes_total + other.minutes_total,
            minutes_done=self.minutes_done + other.minutes_done,
        )

    @property
    def items_total(self) -> int:
        return self.lessons_total + self.quizzes_total

    @property
    def items_done(self) -> int:
        return self.lessons_done + self.quizzes_done

    @property
    def percent(self) -> int:
        # integer division: 100 is reachable only when everything is done
        return self.items_done * 100 // self.items_total if self.items_total else 0

    @property
    def is_complete(self) -> bool:
        return self.items_total > 0 and self.items_done == self.items_total


class ProgressNode(ABC):
    @abstractmethod
    def stats(self) -> ProgressStats: ...


class LessonNode(ProgressNode):
    def __init__(self, lesson: Lesson, completed_at: datetime | None) -> None:
        self.lesson = lesson
        self.completed_at = completed_at

    @property
    def completed(self) -> bool:
        return self.completed_at is not None

    def stats(self) -> ProgressStats:
        minutes = self.lesson.duration_minutes or 0
        return ProgressStats(
            lessons_total=1,
            lessons_done=int(self.completed),
            minutes_total=minutes,
            minutes_done=minutes if self.completed else 0,
        )


class QuizNode(ProgressNode):
    def __init__(self, quiz: Quiz, passed: bool) -> None:
        self.quiz = quiz
        self.passed = passed

    def stats(self) -> ProgressStats:
        return ProgressStats(quizzes_total=1, quizzes_done=int(self.passed))


class CompositeNode(ProgressNode):
    def __init__(self) -> None:
        self.children: list[ProgressNode] = []

    def add(self, child: ProgressNode) -> None:
        self.children.append(child)

    def stats(self) -> ProgressStats:
        return sum((child.stats() for child in self.children), ProgressStats())


class ModuleNode(CompositeNode):
    def __init__(self, module: Module) -> None:
        super().__init__()
        self.module = module

    @property
    def lessons(self) -> list[LessonNode]:
        return [child for child in self.children if isinstance(child, LessonNode)]

    @property
    def quiz(self) -> QuizNode | None:
        return next((child for child in self.children if isinstance(child, QuizNode)), None)


class CourseNode(CompositeNode):
    def __init__(self, course: Course) -> None:
        super().__init__()
        self.course = course

    @property
    def modules(self) -> list[ModuleNode]:
        return [child for child in self.children if isinstance(child, ModuleNode)]

    def next_lesson(self) -> Lesson | None:
        for module in self.modules:
            for lesson_node in module.lessons:
                if not lesson_node.completed:
                    return lesson_node.lesson
        return None


def build_course_tree(
    course: Course, completed: dict[int, datetime], passed_quiz_ids: set[int]
) -> CourseNode:
    tree = CourseNode(course)
    for module in course.modules:
        module_node = ModuleNode(module)
        for lesson in module.lessons:
            module_node.add(LessonNode(lesson, completed.get(lesson.id)))
        if module.quiz is not None:
            module_node.add(QuizNode(module.quiz, module.quiz.id in passed_quiz_ids))
        tree.add(module_node)
    return tree
