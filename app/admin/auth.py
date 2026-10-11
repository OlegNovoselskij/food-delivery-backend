from sqladmin.authentication import AuthenticationBackend
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from app import config, rate_limit
from app.admin.db import run_in_db
from app.exceptions import RateLimitExceeded
from app.repository import user_repository
from app.security import verify_password


def _admin_id_for_credentials(db, email: str, password: str) -> int | None:
    user = user_repository.get_by_email(db, email)
    if user is None or user.role != "admin" or not verify_password(password, user.password_hash):
        return None  # the same answer for "no such user", "not an admin" and "wrong password"
    return user.id


def _is_admin(db, user_id: int) -> bool:
    user = user_repository.get_by_id(db, user_id)
    return user is not None and user.role == "admin"


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str) -> None:
        super().__init__(secret_key)
        # SQLAdmin has no CSRF tokens and runs its actions over GET, so SameSite=Strict is the protection
        self.middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=secret_key,
                session_cookie="admin_session",
                path="/admin",
                max_age=config.ADMIN_SESSION_HOURS * 3600,
                same_site="strict",
                https_only=config.ADMIN_COOKIE_SECURE,
            )
        ]

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = str(form.get("username", "")).strip().lower()
        password = str(form.get("password", ""))
        if not email or not password:
            return False

        client_ip = request.client.host if request.client else "unknown"
        guard = rate_limit.login_client_key(client_ip, email)
        try:
            await run_in_threadpool(rate_limit.ensure_login_allowed, guard)
        except RateLimitExceeded:
            return False

        admin_id = await run_in_db(_admin_id_for_credentials, email, password)
        if admin_id is None:
            await run_in_threadpool(rate_limit.register_login_failure, guard)
            return False

        await run_in_threadpool(rate_limit.clear_login_failures, guard)
        request.session.clear()
        request.session["admin_id"] = admin_id
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        admin_id = request.session.get("admin_id")
        if not isinstance(admin_id, int):
            return False
        # checked in the database on every request: a demoted or deleted admin loses access immediately
        if not await run_in_db(_is_admin, admin_id):
            request.session.clear()
            return False
        return True
