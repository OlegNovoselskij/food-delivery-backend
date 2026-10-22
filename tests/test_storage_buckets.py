from urllib.parse import parse_qs, urlparse

from app import config
from app.storage import S3Storage, is_public_key

COVER_KEY = "courses/7/cover/0123456789abcdef0123456789abcdef.png"
VIDEO_KEY = "courses/7/lessons/3/video/0123456789abcdef0123456789abcdef.mp4"


def _storage(**overrides) -> S3Storage:
    params = dict(
        endpoint_url="https://acct.r2.cloudflarestorage.com",
        public_endpoint_url="https://acct.r2.cloudflarestorage.com",
        access_key="key",
        secret_key="secret",
        bucket="atrium-private",
        region="auto",
        public_bucket="atrium-public",
        public_base_url="https://pub-test.r2.dev",
        auto_setup=False,
    )
    params.update(overrides)
    return S3Storage(**params)


def test_only_covers_are_public_keys():
    assert is_public_key(COVER_KEY)
    assert not is_public_key(VIDEO_KEY)
    assert not is_public_key("courses/7/lessons/3/material/cover/x.pdf")


def test_cover_upload_goes_to_public_bucket():
    url = _storage().upload_url(COVER_KEY, "image/png", 60)
    assert urlparse(url).path.startswith("/atrium-public/courses/7/cover/")


def test_video_upload_and_download_go_to_private_bucket():
    storage = _storage()
    assert urlparse(storage.upload_url(VIDEO_KEY, "video/mp4", 60)).path.startswith("/atrium-private/")
    assert urlparse(storage.download_url(VIDEO_KEY, 60)).path.startswith("/atrium-private/")


def test_public_url_uses_base_url_without_bucket():
    assert _storage().public_url(COVER_KEY) == f"https://pub-test.r2.dev/{COVER_KEY}"


def test_public_url_falls_back_to_path_style():
    storage = _storage(public_base_url="", public_bucket="courses", bucket="courses")
    assert storage.public_url(COVER_KEY) == f"https://acct.r2.cloudflarestorage.com/courses/{COVER_KEY}"


def test_setup_is_skipped_when_auto_setup_is_off():
    storage = _storage()
    storage.ensure_bucket()
    storage.ensure_public_read("courses/*/cover/*")


def _signed_headers(url: str) -> str:
    return parse_qs(urlparse(url).query)["X-Amz-SignedHeaders"][0]


def test_the_declared_size_is_signed_into_the_upload_url():
    assert "content-length" in _signed_headers(_storage().upload_url(COVER_KEY, "image/png", 60, size=1000))
    assert "content-length" not in _signed_headers(_storage().upload_url(COVER_KEY, "image/png", 60))


def test_the_size_is_not_signed_when_the_option_is_off(monkeypatch):
    monkeypatch.setattr(config, "S3_SIGN_CONTENT_LENGTH", False)
    assert "content-length" not in _signed_headers(_storage().upload_url(COVER_KEY, "image/png", 60, size=1000))
