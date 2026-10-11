import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.database import Base

ROOT = Path(__file__).resolve().parents[2]
SERVER_URL = os.environ["DATABASE_URL"].rsplit("/", 1)[0]
SCRATCH = "fooddelivery_migration_test"


def test_migrations_build_the_whole_schema_from_scratch():
    server = create_engine(f"{SERVER_URL}/postgres", isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{SCRATCH}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{SCRATCH}"'))
    url = f"{SERVER_URL}/{SCRATCH}"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env={**os.environ, "DATABASE_URL": url},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        engine = create_engine(url)
        assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
        engine.dispose()
    finally:
        with server.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{SCRATCH}" WITH (FORCE)'))
        server.dispose()
