import argparse
import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal
from app.dependency import get_storage
from app.repository import media_repository
from app.storage import S3Storage

STORAGE_PREFIX = "courses/"


def find_orphans(db: Session, storage: S3Storage, *, now: datetime, grace_seconds: int) -> list[dict]:
    # a file confirmed while the listing runs is young: the grace period (longer than a ticket lives) protects it
    referenced = media_repository.referenced_storage_keys(db)
    return [
        item
        for item in storage.list_objects(STORAGE_PREFIX)
        if item["key"] not in referenced and (now - item["last_modified"]).total_seconds() > grace_seconds
    ]


def cleanup(db: Session, storage: S3Storage, *, dry_run: bool, now: datetime | None = None) -> dict:
    orphans = find_orphans(db, storage, now=now or datetime.now(UTC), grace_seconds=config.STORAGE_ORPHAN_GRACE_SECONDS)
    for item in orphans:
        print(f"{'would delete' if dry_run else 'delete'} {item['key']} ({item['size']} bytes)")
    if not dry_run:
        storage.delete_many(item["key"] for item in orphans)
    return {"found": len(orphans), "deleted": 0 if dry_run else len(orphans), "bytes": sum(i["size"] for i in orphans)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete storage objects that no database row refers to.")
    parser.add_argument("--dry-run", action="store_true", help="only print what would be deleted")
    args = parser.parse_args()

    started = time.monotonic()
    storage = get_storage()
    with SessionLocal() as db:
        summary = cleanup(db, storage, dry_run=args.dry_run)
    print(
        f"orphans found: {summary['found']}, deleted: {summary['deleted']}, bytes: {summary['bytes']}"
        f"{' (dry run)' if args.dry_run else ''}, took {time.monotonic() - started:.1f}s"
    )


if __name__ == "__main__":
    main()
