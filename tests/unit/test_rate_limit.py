import pytest
import redis.exceptions

from app import rate_limit, redis_client
from app.exceptions import RateLimitExceeded


def test_requests_over_the_limit_are_rejected():
    for _ in range(3):
        rate_limit.hit("rl:test", 3, 60)
    with pytest.raises(RateLimitExceeded) as error:
        rate_limit.hit("rl:test", 3, 60)
    assert 0 < error.value.retry_after <= 60


def test_the_window_is_never_extended(fake_valkey):
    rate_limit.hit("rl:window", 10, 60)
    first = fake_valkey.ttl("rl:window")
    rate_limit.hit("rl:window", 10, 60)
    assert fake_valkey.ttl("rl:window") <= first


def test_login_lockout_counts_only_failures():
    key = rate_limit.login_client_key("1.2.3.4", "user@example.com")
    for _ in range(5):
        rate_limit.register_login_failure(key)
    with pytest.raises(RateLimitExceeded):
        rate_limit.ensure_login_allowed(key)
    rate_limit.clear_login_failures(key)
    rate_limit.ensure_login_allowed(key)


def test_a_broken_valkey_never_blocks_requests(monkeypatch):
    def broken():
        raise redis.exceptions.ConnectionError("down")

    monkeypatch.setattr(redis_client, "get_redis", broken)
    rate_limit.hit("rl:x", 1, 60)
    rate_limit.hit("rl:x", 1, 60)
    assert redis_client.is_down()
