from decimal import Decimal

from app.exceptions import ReportAccessDenied
from app.patterns.template.report import Report, ReportResult
from app.reports.common import COURSE_COLUMNS, course_row, course_totals, fill_series, to_float
from app.repository import report_repository


class AdminReport(Report):
    def authorize(self, db, user, params) -> None:
        if user.role != "admin":
            raise ReportAccessDenied()


class PlatformOverviewReport(AdminReport):
    name = "platform-overview"

    def fetch(self, db, user, params) -> ReportResult:
        return ReportResult(rows=[], meta=report_repository.platform_totals(db))

    def to_json(self, result, params) -> dict:
        return result.meta


class CoursePopularityReport(AdminReport):
    name = "course-popularity"
    columns = COURSE_COLUMNS

    def fetch(self, db, user, params) -> ReportResult:
        rows = report_repository.course_stats(
            db,
            teacher_id=None,
            include_drafts=False,
            category_id=params.category_id,
            date_from=params.date_from,
            date_to=params.date_to,
            sort=params.sort,
            limit=params.limit,
        )
        return ReportResult([course_row(row) for row in rows])

    def to_json(self, result, params) -> dict:
        return {"items": result.rows, "totals": course_totals(result.rows)}


class TeacherRankingReport(AdminReport):
    name = "teacher-ranking"
    columns = ("teacher_id", "name", "courses", "students", "completed", "rating_avg", "reviews_count", "revenue")

    def fetch(self, db, user, params) -> ReportResult:
        rows = report_repository.teacher_ranking(
            db, date_from=params.date_from, date_to=params.date_to, sort=params.sort, limit=params.limit
        )
        items = []
        for row in rows:
            data = row._asdict()
            data["rating_avg"] = to_float(data["rating_avg"])
            items.append(data)
        return ReportResult(items)


class RevenueSeriesReport(AdminReport):
    name = "revenue-series"
    columns = ("period", "revenue", "refunded", "payments")

    def fetch(self, db, user, params) -> ReportResult:
        return ReportResult(
            report_repository.revenue_series(
                db,
                date_from=params.date_from,
                date_to=params.date_to,
                group_by=params.group_by,
                course_id=params.course_id,
                teacher_id=params.teacher_id,
                category_id=params.category_id,
            )
        )

    def finalize(self, result, params) -> ReportResult:
        empty = {"revenue": Decimal("0"), "refunded": Decimal("0"), "payments": 0}
        rows = fill_series(result.rows, params.date_from, params.date_to, params.group_by, empty)
        totals = {
            "revenue": sum((Decimal(row["revenue"]) for row in rows), Decimal("0")),
            "refunded": sum((Decimal(row["refunded"]) for row in rows), Decimal("0")),
            "payments": sum(row["payments"] for row in rows),
        }
        return ReportResult(rows, {"totals": totals})

    def to_json(self, result, params) -> dict:
        return {
            "group_by": params.group_by,
            "date_from": params.date_from,
            "date_to": params.date_to,
            "items": result.rows,
            "totals": result.meta["totals"],
        }


class RevenueBreakdownReport(AdminReport):
    name = "revenue-breakdown"
    columns = ("id", "name", "revenue", "refunded", "payments")

    def fetch(self, db, user, params) -> ReportResult:
        rows = report_repository.revenue_breakdown(
            db, by=params.by, date_from=params.date_from, date_to=params.date_to, limit=params.limit
        )
        return ReportResult([row._asdict() for row in rows])

    def to_json(self, result, params) -> dict:
        total = sum((Decimal(row["revenue"]) for row in result.rows), Decimal("0"))
        return {"by": params.by, "items": result.rows, "total_revenue": total}


class UserGrowthReport(AdminReport):
    name = "user-growth"
    columns = ("period", "students", "teachers", "total")

    def fetch(self, db, user, params) -> ReportResult:
        return ReportResult(
            report_repository.user_growth(
                db, date_from=params.date_from, date_to=params.date_to, group_by=params.group_by
            )
        )

    def finalize(self, result, params) -> ReportResult:
        empty = {"students": 0, "teachers": 0, "total": 0}
        rows = fill_series(result.rows, params.date_from, params.date_to, params.group_by, empty)
        totals = {key: sum(row[key] for row in rows) for key in ("students", "teachers", "total")}
        return ReportResult(rows, {"totals": totals})

    def to_json(self, result, params) -> dict:
        return {
            "group_by": params.group_by,
            "date_from": params.date_from,
            "date_to": params.date_to,
            "items": result.rows,
            "totals": result.meta["totals"],
        }


platform_overview = PlatformOverviewReport()
course_popularity = CoursePopularityReport()
teacher_ranking = TeacherRankingReport()
revenue_series = RevenueSeriesReport()
revenue_breakdown = RevenueBreakdownReport()
user_growth = UserGrowthReport()
