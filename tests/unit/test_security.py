import jwt
import pytest

from app import security


def test_password_roundtrip():
    stored = security.hash_password("Secret123!")
    assert security.verify_password("Secret123!", stored)
    assert not security.verify_password("wrong", stored)


def test_an_account_without_a_password_never_authenticates():
    assert security.verify_password("anything", None) is False


def test_passwords_over_the_bcrypt_limit_are_rejected():
    stored = security.hash_password("Secret123!")
    assert security.verify_password("x" * 80, stored) is False


def test_access_token_carries_identity_and_issue_time():
    payload = security.decode_access_token(security.create_access_token(5, "teacher"))
    assert payload["sub"] == "5" and payload["role"] == "teacher" and "iat" in payload


def test_tickets_cannot_be_used_as_access_tokens():
    ticket = security.create_upload_ticket(
        user_id=1, kind="video", lesson_id=2, key="k", content_type="video/mp4", filename="a.mp4"
    )
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(ticket)
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token(security.create_ws_ticket(1))


def test_access_tokens_cannot_be_used_as_tickets():
    with pytest.raises(jwt.PyJWTError):
        security.decode_upload_ticket(security.create_access_token(1, "student"))
    with pytest.raises(jwt.PyJWTError):
        security.decode_ws_ticket(security.create_access_token(1, "student"))


def test_a_code_is_bound_to_its_user_and_purpose():
    stored = security.hash_code(1, "verify_email", "123456")
    assert security.codes_match(stored, 1, "verify_email", "123456")
    assert not security.codes_match(stored, 2, "verify_email", "123456")
    assert not security.codes_match(stored, 1, "password_reset", "123456")
    assert not security.codes_match(stored, 1, "verify_email", "654321")


def test_generated_codes_have_six_digits():
    assert all(len(code) == 6 and code.isdigit() for code in (security.generate_code() for _ in range(100)))
