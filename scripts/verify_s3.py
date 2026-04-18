#!/usr/bin/env python3
"""Verify S3-compatible storage connectivity and bucket setup.

Creates the bucket and prefix directories, then tests upload/download/delete.
Works with both MinIO (local dev) and AWS S3 (production).
"""

import os
import sys

import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "grins-platform-files")
ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
REGION = os.getenv("S3_REGION", "us-east-1")
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

PREFIXES = [
    "customer-photos/",
    "customer-documents/",
    "lead-attachments/",
    "media-library/",
    "receipts/",
]


def main() -> int:
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name=REGION,
    )

    # 1. Create bucket if not exists
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"✅ Bucket '{BUCKET_NAME}' already exists")
    except ClientError:
        s3.create_bucket(Bucket=BUCKET_NAME)
        print(f"✅ Created bucket '{BUCKET_NAME}'")

    # 2. Create prefix directories (empty objects)
    for prefix in PREFIXES:
        s3.put_object(Bucket=BUCKET_NAME, Key=prefix, Body=b"")
        print(f"✅ Created prefix '{prefix}'")

    # 3. Upload test file
    test_key = "test-verification.txt"
    test_content = b"S3 connectivity verification"
    s3.put_object(Bucket=BUCKET_NAME, Key=test_key, Body=test_content)
    print(f"✅ Uploaded test file '{test_key}'")

    # 4. Generate pre-signed URL
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": test_key},
        ExpiresIn=3600,
    )
    print(f"✅ Generated pre-signed URL: {url[:80]}...")

    # 5. Download and verify
    resp = s3.get_object(Bucket=BUCKET_NAME, Key=test_key)
    downloaded = resp["Body"].read()
    assert downloaded == test_content, "Downloaded content mismatch!"
    print("✅ Downloaded and verified test file content")

    # 6. Delete test file
    s3.delete_object(Bucket=BUCKET_NAME, Key=test_key)
    print(f"✅ Deleted test file '{test_key}'")

    print("\n🎉 All S3 verification checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
