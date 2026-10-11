from decimal import Decimal

from app.reports.periods import period_starts

COURSE_COLUMNS = (
    "course_id",
    "title",
    "status",
    "category",
    "teacher_name",
    "students",
    "completed",
    "completion_rate",
    "rating_avg",
    "reviews_count",
    "revenue",
)


def percent(part: int, whole: int) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def to_float(value) -> float | None:
    return round(float(value), 2) if value is not None else None


def course_row(row) -> dict:
    data = row._asdict()
    data["completion_rate"] = percent(data["completed"], data["students"])
    data["rating_avg"] = to_float(data["rating_avg"])
    return data


def course_totals(rows: list[dict]) -> dict:
    return {
        "students": sum(row["students"] for row in rows),
        "completed": sum(row["completed"] for row in rows),
        "revenue": sum((Decimal(row["revenue"]) for row in rows), Decimal("0")),
    }


def fill_series(rows: list[dict], date_from, date_to, group_by: str, empty: dict) -> list[dict]:
    by_period = {row["period"]: row for row in rows}
    return [by_period.get(start, {"period": start, **empty}) for start in period_starts(date_from, date_to, group_by)]
