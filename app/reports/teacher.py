from datetime import datetime, timedelta, timezone

from app.exceptions import CourseNotFound, ReportAccessDenied
from app.patterns.composite.course_tree import ProgressStats
from app.patterns.template.report import Report, ReportResult
from app.reports.common import COURSE_COLUMNS, course_row, course_totals, percent, to_float
from app.repository import course_repository, progress_repository, report_repository
from app.services.access import can_manage_course

CSV_STUDENTS_LIMIT = 5000


class TeacherReport(Report):
    def authorize(self, db, user, params) -> None:
        if user.role not in ("teacher", "admin"):
            raise ReportAccessDenied()
        requested = getattr(params, "teacher_id", None)
        if user.role == "teacher" and requested not in (None, user.id):
            raise ReportAccessDenied()

    @staticmethod
    def teacher_scope(user, params) -> int | None:
        return user.id if user.role == "teacher" else getattr(params, "teacher_id", None)


class CourseScopedReport(TeacherReport):
    def authorize(self, db, user, params) -> None:
        super().authorize(db, user, params)
        course = course_repository.get_by_id(db, params.course_id)
        if course is None or not can_manage_course(course, user):
            raise CourseNotFound()


class TeacherDashboardReport(TeacherReport):
    name = "teacher-dashboard"
    columns = COURSE_COLUMNS

    def fetch(self, db, user, params) -> ReportResult:
        rows = report_repository.course_stats(
            db,
            teacher_id=self.teacher_scope(user, params),
            include_drafts=True,
            category_id=None,
            date_from=params.date_from,
            date_to=params.date_to,
            sort="students",
            limit=200,
        )
        return ReportResult([course_row(row) for row in rows])

    def to_json(self, result, params) -> dict:
        return {"items": result.rows, "totals": course_totals(result.rows)}


class LessonFunnelReport(CourseScopedReport):
    name = "lesson-funnel"
    columns = (
        "module_position", "module_title", "position", "lesson_id", "title",
        "completed", "completed_percent", "drop_off_percent", "biggest_drop",
    )

    def fetch(self, db, user, params) -> ReportResult:
        students = report_repository.funnel_students(db, params.course_id)
        items, previous = [], None
        for row in report_repository.funnel_rows(db, params.course_id):
            data = row._asdict()
            data["completed_percent"] = percent(data["completed"], students) or 0.0
            drop = 0.0
            if previous and data["completed"] < previous:
                drop = round((previous - data["completed"]) * 100 / previous, 1)
            data["drop_off_percent"] = drop
            data["biggest_drop"] = False
            previous = data["completed"]
            items.append(data)

        worst = max(items, key=lambda item: item["drop_off_percent"], default=None)
        if worst is not None and worst["drop_off_percent"] > 0:
            worst["biggest_drop"] = True
        return ReportResult(items, {"students": students})

    def to_json(self, result, params) -> dict:
        return {"course_id": params.course_id, "students": result.meta["students"], "items": result.rows}


class QuizStatsReport(CourseScopedReport):
    name = "quiz-stats"
    columns = (
        "quiz_id", "title", "module_title", "passing_score", "attempts",
        "students", "passed_students", "pass_rate", "avg_score", "pending_review",
    )

    def fetch(self, db, user, params) -> ReportResult:
        items = []
        for row in report_repository.quiz_stats(db, params.course_id):
            data = row._asdict()
            data["pass_rate"] = percent(data["passed_students"], data["students"])
            average = to_float(data["avg_score"])
            data["avg_score"] = round(average, 1) if average is not None else None
            items.append(data)
        return ReportResult(items)

    def to_json(self, result, params) -> dict:
        return {"course_id": params.course_id, "items": result.rows}


class QuestionStatsReport(CourseScopedReport):
    name = "question-stats"
    columns = ("question_id", "text", "question_type", "quiz_title", "answered", "correct", "correct_percent")

    def fetch(self, db, user, params) -> ReportResult:
        items = []
        for row in report_repository.question_stats(db, params.course_id, params.min_answers):
            data = row._asdict()
            data["correct_percent"] = percent(data["correct"], data["answered"]) or 0.0
            items.append(data)
        items.sort(key=lambda item: (item["correct_percent"], -item["answered"]))  # the hardest first
        return ReportResult(items[: params.limit])

    def to_json(self, result, params) -> dict:
        return {"course_id": params.course_id, "items": result.rows}


class CourseStudentsReport(CourseScopedReport):
    name = "course-students"
    columns = (
        "enrollment_id", "student_id", "name", "status", "enrolled_at", "progress_percent",
        "lessons_completed", "lessons_total", "quizzes_passed", "quizzes_total",
        "last_activity_at", "days_inactive",
    )

    def fetch(self, db, user, params) -> ReportResult:
        now = datetime.now(timezone.utc)
        inactive_before = now - timedelta(days=params.inactive_days) if params.inactive_days else None
        export = params.format == "csv"

        rows, total = report_repository.course_students(
            db,
            params.course_id,
            status=params.status,
            inactive_before=inactive_before,
            offset=0 if export else (params.page - 1) * params.size,
            limit=CSV_STUDENTS_LIMIT if export else params.size,
        )
        ids = [row.enrollment_id for row in rows]
        done = progress_repository.completed_counts(db, ids) if ids else {}
        passed = progress_repository.passed_quiz_counts(db, ids) if ids else {}
        lessons_total, _minutes, quizzes_total = progress_repository.course_totals(db, [params.course_id]).get(
            params.course_id, (0, 0, 0)
        )

        items = []
        for row in rows:
            lessons_done = done.get(row.enrollment_id, (0, 0, None))[0]
            quizzes_done = passed.get(row.enrollment_id, 0)
            stats = ProgressStats(
                lessons_total=lessons_total,
                lessons_done=lessons_done,
                quizzes_total=quizzes_total,
                quizzes_done=quizzes_done,
            )
            items.append(
                {
                    "enrollment_id": row.enrollment_id,
                    "student_id": row.student_id,
                    "name": row.name,
                    "status": row.status,
                    "enrolled_at": row.enrolled_at,
                    "progress_percent": stats.percent,
                    "lessons_completed": lessons_done,
                    "lessons_total": lessons_total,
                    "quizzes_passed": quizzes_done,
                    "quizzes_total": quizzes_total,
                    "last_activity_at": row.last_activity_at,
                    "days_inactive": max(0, (now - row.last_activity_at).days),
                }
            )
        return ReportResult(items, {"total": total})

    def to_json(self, result, params) -> dict:
        return {
            "course_id": params.course_id,
            "total": result.meta["total"],
            "page": params.page,
            "size": params.size,
            "items": result.rows,
        }


teacher_dashboard = TeacherDashboardReport()
lesson_funnel = LessonFunnelReport()
quiz_stats = QuizStatsReport()
question_stats = QuestionStatsReport()
course_students = CourseStudentsReport()
