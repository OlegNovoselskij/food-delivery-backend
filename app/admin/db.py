from starlette.concurrency import run_in_threadpool

from app.cache import catalog_cache
from app.database import SessionLocal


async def run_in_db(fn, *args, **kwargs):
    def runner():
        with SessionLocal() as db:
            return fn(db, *args, **kwargs)

    return await run_in_threadpool(runner)


async def invalidate_catalog() -> None:
    await run_in_threadpool(catalog_cache.invalidate)
