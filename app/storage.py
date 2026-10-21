import json
import logging
import re
from collections.abc import Iterable
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app import config
from app.exceptions import StorageUnavailable

logger = logging.getLogger(__name__)

_NOT_FOUND_CODES = {"404", "NoSuchKey", "NoSuchBucket", "NotFound"}
_PUBLIC_KEY_PATTERN = re.compile(r"courses/\d+/cover/[0-9a-f]{32}\.(?:jpg|png|webp)")
_ANSWERED_CODES = _NOT_FOUND_CODES | {"403", "AccessDenied"}  # the storage replied, so it is reachable


def _error_code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def is_public_key(key: str) -> bool:
    return _PUBLIC_KEY_PATTERN.fullmatch(key) is not None


class S3Storage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        public_endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str,
        public_bucket: str | None = None,
        public_base_url: str | None = None,
        auto_setup: bool | None = None,
    ) -> None:
        self._bucket = bucket
        self._public_bucket = public_bucket or config.S3_PUBLIC_BUCKET or bucket
        self._public_endpoint_url = public_endpoint_url
        self._public_base_url = (config.S3_PUBLIC_BASE_URL if public_base_url is None else public_base_url).rstrip("/")
        self._auto_setup = config.S3_AUTO_SETUP if auto_setup is None else auto_setup

        client_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            connect_timeout=5,
            read_timeout=15,
            retries={"max_attempts": 2},
        )
        common = dict(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=client_config,
        )
        self._client = boto3.client("s3", endpoint_url=endpoint_url, **common)
        self._signer = boto3.client("s3", endpoint_url=public_endpoint_url, **common)

    def _bucket_for(self, key: str) -> str:
        return self._public_bucket if is_public_key(key) else self._bucket

    def is_reachable(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as error:
            return _error_code(error) in _ANSWERED_CODES
        except BotoCoreError:
            return False
        return True

    def ensure_bucket(self) -> None:
        if not self._auto_setup:
            return  # production buckets are created by hand in the provider dashboard
        try:
            for bucket in {self._bucket, self._public_bucket}:
                try:
                    self._client.head_bucket(Bucket=bucket)
                except ClientError as error:
                    if _error_code(error) not in _NOT_FOUND_CODES:
                        raise
                    self._client.create_bucket(Bucket=bucket)
        except (BotoCoreError, ClientError) as error:
            logger.exception("Cannot prepare buckets")
            raise StorageUnavailable() from error

    def ensure_public_read(self, key_pattern: str) -> None:
        if not self._auto_setup:
            return  # production: the public bucket is exposed through the provider (r2.dev), not a bucket policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self._public_bucket}/{key_pattern}"],
                }
            ],
        }
        try:
            self._client.put_bucket_policy(Bucket=self._public_bucket, Policy=json.dumps(policy))
        except (BotoCoreError, ClientError) as error:
            logger.exception("Cannot publish %s in bucket %s", key_pattern, self._public_bucket)
            raise StorageUnavailable() from error

    def public_url(self, key: str) -> str:
        quoted = quote(key, safe="/")
        if self._public_base_url:
            return f"{self._public_base_url}/{quoted}"
        return f"{self._public_endpoint_url.rstrip('/')}/{self._public_bucket}/{quoted}"

    def upload_url(self, key: str, content_type: str, expires_in: int) -> str:
        return self._signer.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket_for(key), "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )

    def download_url(self, key: str, expires_in: int, filename: str | None = None) -> str:
        params = {"Bucket": self._bucket_for(key), "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f"attachment; filename*=UTF-8''{quote(filename, safe='')}"
        return self._signer.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_in)

    def head(self, key: str) -> dict | None:
        try:
            response = self._client.head_object(Bucket=self._bucket_for(key), Key=key)
        except ClientError as error:
            if _error_code(error) in _NOT_FOUND_CODES:
                return None
            logger.exception("head_object failed for %s", key)
            raise StorageUnavailable() from error
        except BotoCoreError as error:
            logger.exception("head_object failed for %s", key)
            raise StorageUnavailable() from error
        return {"size": response["ContentLength"], "content_type": response.get("ContentType")}

    def delete_many(self, keys: Iterable[str | None]) -> None:
        for key in keys:
            if not key:
                continue
            try:
                self._client.delete_object(Bucket=self._bucket_for(key), Key=key)
            except (BotoCoreError, ClientError):
                logger.exception("Could not delete %s from storage", key)
