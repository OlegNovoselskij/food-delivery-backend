from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import limit_by_user, require_role
from app.models.user import User
from app.patterns.template.report import Report, ReportResult
from app.reports import admin as admin_reports
from app.reports import teacher as teacher_reports
from app.schemas.report import (
    BreakdownOut,
    CourseReportParams,
    CourseStatsOut,
    CourseStatsParams,
    FunnelOut,
    GrowthOut,
    GrowthParams,
    OverviewOut,
    QuestionsParams,
    QuestionsQuery,
    QuestionStatsOut,
    QuizStatsOut,
    ReportFormat,
    ReportParams,
    RevenueBreakdownParams,
    RevenueSeriesOut,
    RevenueSeriesParams,
    StudentsOut,
    StudentsParams,
    StudentsQuery,
    TeacherDashboardParams,
    TeacherRankingOut,
    TeacherRankingParams,
)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(limit_by_user("reports", limit=30, window_seconds=60))],
)

admin_only = require_role("admin")
staff_only = require_role("teacher", "admin")


def _respond(report: Report, result: ReportResult, params: ReportParams):
    if params.format == "csv":
        return Response(
            content=report.to_csv(result),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{report.name}.csv"'},
        )
    return report.to_json(result, params)


def _run(report: Report, db: Session, user: User, params: ReportParams):
    return _respond(report, report.run(db, user, params), params)


@router.get("/admin/overview", response_model=OverviewOut)
def admin_overview(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return _run(admin_reports.platform_overview, db, user, ReportParams())


@router.get("/admin/courses", response_model=CourseStatsOut)
def admin_courses(
    params: Annotated[CourseStatsParams, Query()], user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    return _run(admin_reports.course_popularity, db, user, params)


@router.get("/admin/teachers", response_model=TeacherRankingOut)
def admin_teachers(
    params: Annotated[TeacherRankingParams, Query()], user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    return _run(admin_reports.teacher_ranking, db, user, params)


@router.get("/admin/revenue", response_model=RevenueSeriesOut)
def admin_revenue(
    params: Annotated[RevenueSeriesParams, Query()], user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    return _run(admin_reports.revenue_series, db, user, params)


@router.get("/admin/revenue/breakdown", response_model=BreakdownOut)
def admin_revenue_breakdown(
    params: Annotated[RevenueBreakdownParams, Query()], user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    return _run(admin_reports.revenue_breakdown, db, user, params)


@router.get("/admin/users/growth", response_model=GrowthOut)
def admin_user_growth(
    params: Annotated[GrowthParams, Query()], user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    return _run(admin_reports.user_growth, db, user, params)


@router.get("/teacher/dashboard", response_model=CourseStatsOut)
def teacher_dashboard(
    params: Annotated[TeacherDashboardParams, Query()], user: User = Depends(staff_only), db: Session = Depends(get_db)
):
    return _run(teacher_reports.teacher_dashboard, db, user, params)


@router.get("/teacher/courses/{course_id}/funnel", response_model=FunnelOut)
def lesson_funnel(
    course_id: int,
    report_format: ReportFormat = Query("json", alias="format"),
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    params = CourseReportParams(course_id=course_id, format=report_format)
    return _run(teacher_reports.lesson_funnel, db, user, params)


@router.get("/teacher/courses/{course_id}/quizzes", response_model=QuizStatsOut)
def quiz_stats(
    course_id: int,
    report_format: ReportFormat = Query("json", alias="format"),
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    params = CourseReportParams(course_id=course_id, format=report_format)
    return _run(teacher_reports.quiz_stats, db, user, params)


@router.get("/teacher/courses/{course_id}/questions", response_model=QuestionStatsOut)
def question_stats(
    course_id: int,
    query: Annotated[QuestionsQuery, Query()],
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    params = QuestionsParams(course_id=course_id, **query.model_dump())
    return _run(teacher_reports.question_stats, db, user, params)


@router.get("/teacher/courses/{course_id}/students", response_model=StudentsOut)
def course_students(
    course_id: int,
    query: Annotated[StudentsQuery, Query()],
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    params = StudentsParams(course_id=course_id, **query.model_dump())
    return _run(teacher_reports.course_students, db, user, params)
