"""S3 upload error type for PhotoService.

Distinguishes retryable transient failures (network, throttling) from
misconfiguration failures (missing credentials, wrong region). API
endpoints catch and map: retryable=True → HTTP 502, retryable=False → 503.
"""

from __future__ import annotations


class S3UploadError(Exception):
    """Raised when an S3 put_object call fails.

    Attributes:
        retryable: True if the failure is transient (caller may retry);
            False if the failure is structural (missing creds, etc).
    """

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable
