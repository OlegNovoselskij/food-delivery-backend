from datetime import UTC, datetime
from types import SimpleNamespace

from app.patterns.composite.course_tree import build_course_tree

NOW = datetime.now(UTC)


def lesson(lesson_id: int, minutes: int = 10):
    return SimpleNamespace(id=lesson_id, title=f"Lesson {lesson_id}", duration_minutes=minutes)


def course(with_quiz: bool = True):
    quiz = SimpleNamespace(id=100, title="Quiz") if with_quiz else None
    first = SimpleNamespace(id=1, title="One", lessons=[lesson(1), lesson(2)], quiz=quiz)
    second = SimpleNamespace(id=2, title="Two", lessons=[lesson(3)], quiz=None)
    return SimpleNamespace(id=1, modules=[first, second])


def test_progress_counts_lessons_and_ready_quizzes():
    stats = build_course_tree(course(), {1: NOW}, set(), {100}).stats()
    assert (stats.lessons_total, stats.quizzes_total, stats.items_total) == (3, 1, 4)
    assert stats.percent == 25 and stats.minutes_done == 10


def test_quizzes_without_questions_do_not_count():
    stats = build_course_tree(course(), {}, set(), set()).stats()
    assert stats.quizzes_total == 0 and stats.items_total == 3


def test_100_percent_is_reachable_only_when_everything_is_done():
    lessons_done = {1: NOW, 2: NOW, 3: NOW}
    assert build_course_tree(course(), lessons_done, set(), {100}).stats().percent == 75
    finished = build_course_tree(course(), lessons_done, {100}, {100}).stats()
    assert finished.percent == 100 and finished.is_complete


def test_percent_rounds_down():
    stats = build_course_tree(course(with_quiz=False), {1: NOW, 2: NOW}, set(), set()).stats()
    assert stats.percent == 66


def test_next_lesson_is_the_first_unfinished_one():
    assert build_course_tree(course(), {1: NOW, 3: NOW}, set(), {100}).next_lesson().id == 2
    done = {1: NOW, 2: NOW, 3: NOW}
    assert build_course_tree(course(with_quiz=False), done, set(), set()).next_lesson() is None
