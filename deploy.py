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

    for file_path in STATIC_DIR.rglob("*"):
        if file_path.is_file():
            key = str(file_path.relative_to(STATIC_DIR))
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

        for key in [f"{name}.html", name, f"{name}/index.html"]:
            print(f"  Uploading {key}")
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=key,
                Body=html.encode("utf-8"),
                ContentType="text/html",
            )


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
        invalidate_cloudfront()
    elif args.command == "all":
        download_resume()
        upload_static()
        upload_redirects()
        invalidate_cloudfront()

    print("Done!")


if __name__ == "__main__":
    main()
