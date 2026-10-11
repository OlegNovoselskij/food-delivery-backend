import time

import jwt
from sqlalchemy import text

from app import security
from app.models.email_outbox import EmailOutbox
from app.models.user import User
from tests.helpers import API, PASSWORD, create_user, last_code

AUTH = f"{API}/auth"
EMAIL = "new@example.com"


def register(client, email: str = EMAIL):
    return client.post(f"{AUTH}/register", json={"name": "New", "surname": "User", "email": email})


def confirm(client, code: str, password: str = PASSWORD, email: str = EMAIL):
    return client.post(f"{AUTH}/verify-email", json={"email": email, "code": code, "password": password})


def login(client, password: str, email: str = EMAIL):
    return client.post(f"{AUTH}/login", json={"email": email, "password": password})


def test_registration_creates_an_inactive_account_and_sends_a_code(client, db):
    assert register(client).status_code == 202
    user = db.query(User).filter(User.email == EMAIL).one()
    assert user.email_verified is False and user.password_hash is None
    assert len(last_code(db, EMAIL)) == 6


def test_login_is_impossible_until_the_registration_is_confirmed(client, db):
    register(client)
    assert login(client, PASSWORD).status_code == 401


def test_the_code_sets_the_password_and_returns_a_token(client, db):
    register(client)
    response = confirm(client, last_code(db, EMAIL))
    assert response.status_code == 200
    me = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert me.json()["email_verified"] is True
    assert login(client, PASSWORD).status_code == 200
    assert confirm(client, last_code(db, EMAIL)).status_code == 400


def test_five_wrong_codes_destroy_the_code(client, db):
    register(client)
    right = last_code(db, EMAIL)
    wrong = "000000" if right != "000000" else "111111"
    for _ in range(5):
        assert confirm(client, wrong).status_code == 400
    assert confirm(client, right).status_code == 400


def test_a_weak_password_does_not_use_up_the_code(client, db):
    register(client)
    code = last_code(db, EMAIL)
    assert confirm(client, code, password="short").status_code == 422
    assert confirm(client, code).status_code == 200


def test_a_confirmed_address_cannot_be_registered_again(client, db):
    create_user(db, email="taken@example.com")
    assert register(client, "taken@example.com").status_code == 409


def test_codes_are_not_resent_during_the_cooldown(client, db):
    register(client)
    assert client.post(f"{AUTH}/resend-code", json={"email": EMAIL}).status_code == 202
    assert db.query(EmailOutbox).count() == 1

    db.execute(text("UPDATE email_codes SET created_at = now() - interval '2 minutes'"))
    db.commit()
    client.post(f"{AUTH}/resend-code", json={"email": EMAIL})
    assert db.query(EmailOutbox).count() == 2


def test_forgot_password_never_reveals_whether_an_account_exists(client, db):
    create_user(db, email="known@example.com")
    known = client.post(f"{AUTH}/forgot-password", json={"email": "known@example.com"})
    unknown = client.post(f"{AUTH}/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert db.query(EmailOutbox).count() == 1


def test_password_reset_logs_the_user_out_everywhere(client, db):
    user = create_user(db, email="reset@example.com")
    now = int(time.time())
    old_token = jwt.encode(
        {"sub": str(user.id), "role": user.role, "iat": now - 120, "exp": now + 3600},
        security.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    headers = {"Authorization": f"Bearer {old_token}"}
    assert client.get(f"{API}/users/me", headers=headers).status_code == 200

    client.post(f"{AUTH}/forgot-password", json={"email": "reset@example.com"})
    code = last_code(db, "reset@example.com")
    reset = client.post(
        f"{AUTH}/reset-password",
        json={"email": "reset@example.com", "code": code, "new_password": "NewPassword456!"},
    )
    assert reset.status_code == 200

    assert login(client, PASSWORD, "reset@example.com").status_code == 401
    assert login(client, "NewPassword456!", "reset@example.com").status_code == 200
    assert client.get(f"{API}/users/me", headers=headers).status_code == 401


def test_login_is_locked_after_repeated_failures(client, db):
    create_user(db, email="lock@example.com")
    for _ in range(5):
        assert login(client, "wrong-password", "lock@example.com").status_code == 401
    locked = login(client, PASSWORD, "lock@example.com")
    assert locked.status_code == 429 and "Retry-After" in locked.headers
