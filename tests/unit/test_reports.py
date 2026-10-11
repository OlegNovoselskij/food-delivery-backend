from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.patterns.template.report import ReportResult, _csv_cell
from app.reports.admin import course_popularity
from app.reports.periods import bucket_start, next_bucket, period_starts
from app.schemas.report import SeriesParams


@pytest.mark.parametrize("value", ["=1+1", "+1", "-1", "@SUM(A1)"])
def test_csv_cells_that_look_like_formulas_are_neutralised(value):
    assert _csv_cell(value) == "'" + value


def test_csv_cell_formats_other_values():
    assert _csv_cell(None) == ""
    assert _csv_cell(Decimal("49.90")) == "49.90"
    assert _csv_cell(date(2026, 1, 2)) == "2026-01-02"
    assert _csv_cell("Python") == "Python"


def test_csv_starts_with_a_bom_so_excel_reads_utf8():
    output = course_popularity.to_csv(ReportResult(rows=[{"course_id": 1, "title": "=cmd|' /C calc'!A0"}]))
    assert output.startswith("﻿") and "'=cmd" in output


def test_period_buckets():
    assert bucket_start(date(2026, 10, 14), "week") == date(2026, 10, 12)
    assert next_bucket(date(2026, 12, 1), "month") == date(2027, 1, 1)
    assert period_starts(date(2026, 1, 15), date(2026, 3, 2), "month") == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
    ]
    assert period_starts(date(2026, 10, 12), date(2026, 10, 25), "week") == [date(2026, 10, 12), date(2026, 10, 19)]


def test_series_parameters_are_validated():
    with pytest.raises(ValidationError):
        SeriesParams(group_by="day", date_from=date(2020, 1, 1), date_to=date(2026, 1, 1))
    with pytest.raises(ValidationError):
        SeriesParams(date_from=date(2026, 2, 1), date_to=date(2026, 1, 1))
    assert SeriesParams().group_by == "month"
