import csv
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.user import User

# a text cell starting with one of these would be executed as a formula by Excel
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass
class ReportResult:
    rows: list[dict]
    meta: dict = field(default_factory=dict)


def _csv_cell(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value  # CSV injection: user-controlled text must stay text
    return value


class Report(ABC):
    name: str
    columns: tuple[str, ...] = ()

    def run(self, db: Session, user: User, params) -> ReportResult:
        self.authorize(db, user, params)
        return self.finalize(self.fetch(db, user, params), params)

    @abstractmethod
    def authorize(self, db: Session, user: User, params) -> None: ...

    @abstractmethod
    def fetch(self, db: Session, user: User, params) -> ReportResult: ...

    def finalize(self, result: ReportResult, params) -> ReportResult:
        return result

    def to_json(self, result: ReportResult, params) -> dict:
        return {"items": result.rows}

    def to_csv(self, result: ReportResult) -> str:
        buffer = io.StringIO()
        buffer.write("﻿")  # BOM: Excel opens UTF-8 (Cyrillic) correctly
        writer = csv.writer(buffer)
        writer.writerow(self.columns)
        for row in result.rows:
            writer.writerow([_csv_cell(row.get(column)) for column in self.columns])
        return buffer.getvalue()
