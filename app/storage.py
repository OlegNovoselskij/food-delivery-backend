import logging
from collections.abc import Iterable
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.exceptions import StorageUnavailable

logger = logging.getLogger(__name__)

_NOT_FOUND_CODES = {"404", "NoSuchKey", "NoSuchBucket", "NotFound"}


def _error_code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


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
    ) -> None:
        self._bucket = bucket

        client_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
        common = dict(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=client_config,
        )
        self._client = boto3.client("s3", endpoint_url=endpoint_url, **common)
        self._signer = boto3.client("s3", endpoint_url=public_endpoint_url, **common)

    def ensure_bucket(self) -> None:
        try:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError as error:
                if _error_code(error) not in _NOT_FOUND_CODES:
                    raise
                self._client.create_bucket(Bucket=self._bucket)
        except (BotoCoreError, ClientError) as error:
            logger.exception("Cannot prepare bucket %s", self._bucket)
            raise StorageUnavailable() from error

    def upload_url(self, key: str, content_type: str, expires_in: int) -> str:
        return self._signer.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )

    def download_url(self, key: str, expires_in: int, filename: str | None = None) -> str:
        params = {"Bucket": self._bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f"attachment; filename*=UTF-8''{quote(filename, safe='')}"
        return self._signer.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_in)

    def head(self, key: str) -> dict | None:
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key)
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
                self._client.delete_object(Bucket=self._bucket, Key=key)
            except (BotoCoreError, ClientError):
                logger.exception("Could not delete %s from storage", key)
