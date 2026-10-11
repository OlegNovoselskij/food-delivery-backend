from sqlalchemy.orm import Session

from app.exceptions import EnrollmentNotActive, EnrollmentNotFound, LessonNotFound
from app.models.catalog import Lesson
from app.models.enrollment import Enrollment, LessonProgress
from app.models.user import User
from app.patterns.composite.course_tree import CourseNode, ProgressStats, build_course_tree
from app.patterns.observer.event_bus import event_bus
from app.patterns.observer.events import CourseCompleted
from app.patterns.states.enrollment_state import EnrollmentStateMachine
from app.repository import curriculum_repository, enrollment_repository, progress_repository
from app.schemas.enrollment import EnrollmentFilters
from app.services import enrollment_service


def _summary(stats: ProgressStats) -> dict:
    return {
        "percent": stats.percent,
        "lessons_total": stats.lessons_total,
        "lessons_completed": stats.lessons_done,
        "quizzes_total": stats.quizzes_total,
        "quizzes_passed": stats.quizzes_done,
        "minutes_total": stats.minutes_total,
        "minutes_completed": stats.minutes_done,
    }


def _course_progress(enrollment: Enrollment, tree: CourseNode) -> dict:
    next_lesson = tree.next_lesson()
    modules = []
    for module_node in tree.modules:
        quiz_node = module_node.quiz
        modules.append(
            {
                "id": module_node.module.id,
                "title": module_node.module.title,
                "position": module_node.module.position,
                "progress": _summary(module_node.stats()),
                "quiz": (
                    {"id": quiz_node.quiz.id, "title": quiz_node.quiz.title, "passed": quiz_node.passed}
                    if quiz_node
                    else None
                ),
                "lessons": [
                    {
                        "id": node.lesson.id,
                        "title": node.lesson.title,
                        "position": node.lesson.position,
                        "duration_minutes": node.lesson.duration_minutes,
                        "completed": node.completed,
                        "completed_at": node.completed_at,
                    }
                    for node in module_node.lessons
                ],
            }
        )
    return {
        "enrollment_id": enrollment.id,
        "course_id": enrollment.course_id,
        "enrollment_status": enrollment.status,
        "progress": _summary(tree.stats()),
        "next_lesson_id": next_lesson.id if next_lesson else None,
        "modules": modules,
    }


def _load_tree(db: Session, enrollment: Enrollment) -> CourseNode:
    course = curriculum_repository.get_program_course(db, enrollment.course_id)
    return build_course_tree(
        course,
        progress_repository.completed_map(db, enrollment.id),
        progress_repository.passed_quiz_ids(db, enrollment.id),
        progress_repository.ready_quiz_ids(db, enrollment.course_id),
    )


def complete_if_finished(db: Session, enrollment: Enrollment, tree: CourseNode | None = None) -> None:
    if enrollment.status != "active":
        return
    # autoflush is off: make pending changes (a passed attempt, a new progress row) visible to the queries below
    db.flush()
    if tree is None:
        tree = _load_tree(db, enrollment)
    if not tree.stats().is_complete:
        return

    EnrollmentStateMachine(enrollment).complete()
    event_bus.publish(
        db,
        CourseCompleted(
            enrollment_id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            course_title=enrollment.course.title,
        ),
    )


def _get_own_locked(db: Session, enrollment_id: int, user: User) -> Enrollment:
    # row lock: parallel requests for one enrollment run one after another
    enrollment = enrollment_repository.get_by_id_for_update(db, enrollment_id)
    if enrollment is None or enrollment.student_id != user.id:
        raise EnrollmentNotFound()  # 404 instead of 403: do not reveal that someone else's enrollment exists
    return enrollment


def _get_lesson_of_course(db: Session, lesson_id: int, course_id: int) -> Lesson:
    lesson = curriculum_repository.get_lesson(db, lesson_id)
    if lesson is None or lesson.module.course_id != course_id:
        raise LessonNotFound()
    return lesson


def mark_lesson(db: Session, enrollment_id: int, lesson_id: int, user: User) -> dict:
    enrollment = _get_own_locked(db, enrollment_id, user)
    lesson = _get_lesson_of_course(db, lesson_id, enrollment.course_id)

    if progress_repository.get_progress(db, enrollment.id, lesson.id) is not None:
        return _course_progress(enrollment, _load_tree(db, enrollment))

    if enrollment.status != "active":
        raise EnrollmentNotActive()

    progress_repository.add(db, LessonProgress(enrollment_id=enrollment.id, lesson_id=lesson.id))

    tree = _load_tree(db, enrollment)
    complete_if_finished(db, enrollment, tree)

    result = _course_progress(enrollment, tree)  # build the answer BEFORE commit expires the objects
    db.commit()
    return result


def unmark_lesson(db: Session, enrollment_id: int, lesson_id: int, user: User) -> dict:
    enrollment = _get_own_locked(db, enrollment_id, user)
    lesson = _get_lesson_of_course(db, lesson_id, enrollment.course_id)

    progress = progress_repository.get_progress(db, enrollment.id, lesson.id)
    if progress is not None:
        if enrollment.status != "active":
            raise EnrollmentNotActive()
        progress_repository.delete(db, progress)

    result = _course_progress(enrollment, _load_tree(db, enrollment))
    db.commit()
    return result


def get_progress(db: Session, enrollment_id: int, user: User) -> dict:
    enrollment = enrollment_service.get_one(db, enrollment_id, user)
    return _course_progress(enrollment, _load_tree(db, enrollment))


def history(db: Session, student: User, filters: EnrollmentFilters) -> list[dict]:
    enrollments = enrollment_repository.list_by_student(
        db, student.id, status=filters.status, course_id=filters.course_id
    )
    if not enrollments:
        return []

    enrollment_ids = [enrollment.id for enrollment in enrollments]
    course_ids = list({enrollment.course_id for enrollment in enrollments})

    done = progress_repository.completed_counts(db, enrollment_ids)
    passed = progress_repository.passed_quiz_counts(db, enrollment_ids)
    totals = progress_repository.course_totals(db, course_ids)

    items = []
    for enrollment in enrollments:
        lessons_done, minutes_done, last_activity = done.get(enrollment.id, (0, 0, None))
        lessons_total, minutes_total, quizzes_total = totals.get(enrollment.course_id, (0, 0, 0))
        stats = ProgressStats(
            lessons_total=lessons_total,
            lessons_done=lessons_done,
            quizzes_total=quizzes_total,
            quizzes_done=passed.get(enrollment.id, 0),
            minutes_total=minutes_total,
            minutes_done=minutes_done,
        )
        items.append({"enrollment": enrollment, "progress": _summary(stats), "last_activity_at": last_activity})

    items.sort(key=lambda item: item["last_activity_at"] or item["enrollment"].enrolled_at, reverse=True)
    return items
