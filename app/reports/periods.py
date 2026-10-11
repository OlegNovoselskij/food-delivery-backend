from datetime import date, timedelta

STEP_DAYS = {"day": 1, "week": 7, "month": 28}
MAX_BUCKETS = 400


def bucket_start(day: date, group_by: str) -> date:
    if group_by == "week":
        return day - timedelta(days=day.weekday())
    if group_by == "month":
        return day.replace(day=1)
    return day


def next_bucket(start: date, group_by: str) -> date:
    if group_by == "day":
        return start + timedelta(days=1)
    if group_by == "week":
        return start + timedelta(days=7)
    return (start.replace(day=28) + timedelta(days=4)).replace(day=1)


def period_starts(date_from: date, date_to: date, group_by: str) -> list[date]:
    starts = []
    current = bucket_start(date_from, group_by)
    while current <= date_to:
        starts.append(current)
        current = next_bucket(current, group_by)
    return starts
