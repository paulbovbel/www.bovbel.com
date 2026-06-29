#!/usr/bin/env python3
import argparse
import os
import boto3
import requests
import mimetypes
from pathlib import Path

BUCKET_NAME = "www.bovbel.com"
DISTRIBUTION_ID = "E3EDUX8NQFYNJF"
STATIC_DIR = Path(__file__).parent / "static"

REDIRECTS = {
    "meet": "https://doodle.com/bp/paulbovbel/meet",
    "resume": "https://www.bovbel.com/resume.pdf",
}

REDIRECT_TEMPLATE = """\
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-57Q5PWFEVM"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-57Q5PWFEVM');
  </script>
  <title>Paul Bovbel - {title}</title>
  <meta http-equiv="refresh" content="0;URL={target}" />
</head>
<body>
  <p>Redirecting to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""


def static_files():
    """Return deployable static files and their S3 keys."""
    for file_path in STATIC_DIR.rglob("*"):
        if file_path.is_file():
            yield file_path, file_path.relative_to(STATIC_DIR).as_posix()


def redirect_keys(name):
    """Return S3 keys generated for a redirect."""
    return [f"{name}.html", name, f"{name}/index.html"]


def expected_s3_keys():
    """Return every S3 key that should exist after deploy."""
    keys = {key for _, key in static_files()}
    for name in REDIRECTS:
        keys.update(redirect_keys(name))
    return keys


def download_resume():
    """Download resume PDF from Google Docs."""
    print("Downloading resume...")
    resume_doc_id = os.environ["RESUME_DOC_ID"]
    url = f"https://docs.google.com/document/d/{resume_doc_id}/export?format=pdf"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    resume_path = STATIC_DIR / "resume.pdf"
    resume_path.write_bytes(response.content)
    print(f"Resume saved to {resume_path}")


def upload_static():
    """Sync static files to S3 bucket."""
    print("Syncing static files to S3...")
    s3 = boto3.client("s3")

    for file_path, key in static_files():
        content_type, _ = mimetypes.guess_type(str(file_path))
        extra_args = {"ContentType": content_type} if content_type else {}

        print(f"  Uploading {key}")
        s3.upload_file(str(file_path), BUCKET_NAME, key, ExtraArgs=extra_args)


def upload_redirects():
    """Generate and upload redirect pages."""
    print("Uploading redirect pages...")
    s3 = boto3.client("s3")

    for name, target in REDIRECTS.items():
        title = name.capitalize()
        html = REDIRECT_TEMPLATE.format(title=title, target=target)

        for key in redirect_keys(name):
            print(f"  Uploading {key}")
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=key,
                Body=html.encode("utf-8"),
                ContentType="text/html",
            )


def delete_stale_objects():
    """Delete S3 objects that are not generated from the local source."""
    print("Deleting stale S3 objects...")
    s3 = boto3.client("s3")
    expected_keys = expected_s3_keys()
    stale_objects = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key not in expected_keys:
                stale_objects.append({"Key": key})
                print(f"  Deleting {key}")

                if len(stale_objects) == 1000:
                    s3.delete_objects(Bucket=BUCKET_NAME, Delete={"Objects": stale_objects})
                    stale_objects = []

    if stale_objects:
        s3.delete_objects(Bucket=BUCKET_NAME, Delete={"Objects": stale_objects})


def invalidate_cloudfront():
    """Invalidate CloudFront cache."""
    print("Invalidating CloudFront cache...")
    cloudfront = boto3.client("cloudfront")

    response = cloudfront.create_invalidation(
        DistributionId=DISTRIBUTION_ID,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(hash(os.urandom(16))),
        },
    )
    print(f"  Invalidation ID: {response['Invalidation']['Id']}")


def main():
    parser = argparse.ArgumentParser(description="Deploy www.bovbel.com")
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["download-resume", "upload", "all"],
        help="Command to run (default: all)",
    )
    args = parser.parse_args()

    if args.command == "download-resume":
        download_resume()
    elif args.command == "upload":
        upload_static()
        upload_redirects()
        delete_stale_objects()
        invalidate_cloudfront()
    elif args.command == "all":
        download_resume()
        upload_static()
        upload_redirects()
        delete_stale_objects()
        invalidate_cloudfront()

    print("Done!")


if __name__ == "__main__":
    main()
