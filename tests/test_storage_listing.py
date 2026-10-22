from datetime import UTC, datetime

from botocore.stub import Stubber

from tests.test_storage_buckets import COVER_KEY, VIDEO_KEY, _storage


def test_listing_covers_the_private_and_the_public_bucket():
    storage = _storage()
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    with Stubber(storage._client) as stubber:
        for bucket, key in (("atrium-private", VIDEO_KEY), ("atrium-public", COVER_KEY)):
            stubber.add_response(
                "list_objects_v2",
                {"Contents": [{"Key": key, "Size": 10, "LastModified": stamp}]},
                {"Bucket": bucket, "Prefix": "courses/"},
            )
        found = storage.list_objects("courses/")
    assert [item["key"] for item in found] == [VIDEO_KEY, COVER_KEY]
    assert found[0] == {"key": VIDEO_KEY, "size": 10, "last_modified": stamp}
