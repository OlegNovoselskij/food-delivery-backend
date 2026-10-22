import os

_BASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/fooddelivery")
SERVER_URL = _BASE_URL.rsplit("/", 1)[0]
TEST_DATABASE_NAME = "fooddelivery_test"
os.environ["DATABASE_URL"] = f"{SERVER_URL}/{TEST_DATABASE_NAME}"
os.environ["APP_ENV"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"

from collections.abc import Iterator
from datetime import UTC, datetime

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app import redis_client
from app.database import Base, SessionLocal, engine
from app.dependency import get_storage
from app.main import app
from tests.helpers import create_category, create_user


class FakeStorage:
    """In-memory replacement of S3Storage: tests "upload" a file by calling put()."""

    def __init__(self) -> None:
        self.objects: dict[str, dict] = {}
        self.signed_sizes: dict[str, int | None] = {}

    def ensure_bucket(self) -> None:
        pass

    def ensure_public_read(self, key_pattern: str) -> None:
        pass

    def public_url(self, key: str) -> str:
        return f"https://storage.test/public/{key}"

    def upload_url(self, key: str, content_type: str, expires_in: int, size: int | None = None) -> str:
        self.signed_sizes[key] = size
        return f"https://storage.test/upload/{key}"

    def download_url(self, key: str, expires_in: int, filename: str | None = None) -> str:
        return f"https://storage.test/download/{key}"

    def head(self, key: str) -> dict | None:
        item = self.objects.get(key)
        return {"size": item["size"], "content_type": item["content_type"]} if item else None

    def list_objects(self, prefix: str) -> list[dict]:
        return [
            {"key": key, "size": item["size"], "last_modified": item["last_modified"]}
            for key, item in self.objects.items()
            if key.startswith(prefix)
        ]

    def delete_many(self, keys) -> None:
        for key in keys:
            if key:
                self.objects.pop(key, None)

    def is_reachable(self) -> bool:
        return True

    def put(self, key: str, size: int, content_type: str, last_modified: datetime | None = None) -> None:
        self.objects[key] = {
            "size": size,
            "content_type": content_type,
            "last_modified": last_modified or datetime.now(UTC),
        }


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    server = create_engine(f"{SERVER_URL}/postgres", isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DATABASE_NAME}
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))
    server.dispose()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    yield
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def fake_valkey(monkeypatch: pytest.MonkeyPatch) -> Iterator[fakeredis.FakeRedis]:
    client = fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)
    monkeypatch.setattr(redis_client, "get_redis", lambda: client)
    redis_client._down_until = 0.0
    yield client
    redis_client._down_until = 0.0
    client.flushall()


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def client(storage: FakeStorage) -> Iterator[TestClient]:
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db() -> Iterator:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def category(db):
    return create_category(db)


@pytest.fixture
def teacher(db):
    return create_user(db, "teacher", email="teacher@example.com")


@pytest.fixture
def student(db):
    return create_user(db, "student", email="student@example.com")


@pytest.fixture
def admin(db):
    return create_user(db, "admin", email="admin@example.com")
