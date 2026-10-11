import logging
from collections.abc import Callable

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_KEY = "after_commit_hooks"


def run_after_commit(db: Session, hook: Callable[[], None]) -> None:
    db.info.setdefault(_KEY, []).append(hook)


@event.listens_for(Session, "after_commit")
def _run_hooks(session: Session) -> None:
    for hook in session.info.pop(_KEY, []):
        try:
            hook()
        except Exception:
            logger.exception("An after-commit hook failed")


@event.listens_for(Session, "after_rollback")
def _drop_hooks(session: Session) -> None:
    session.info.pop(_KEY, None)
