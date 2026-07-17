#!/usr/bin/env python3
import argparse
import json
import mimetypes
import shutil
from functools import cache
import os
from pathlib import Path

import boto3
import requests

STATIC_DIR = Path(__file__).parent / "static"
LOCAL_SITE_DIR = Path(__file__).parent / ".local-site"
CDK_OUTPUTS = Path(__file__).parent / "cdk-outputs.json"
RESUME_KEY = "resume.pdf"

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
        key = file_path.relative_to(STATIC_DIR).as_posix()
        if file_path.is_file() and key != RESUME_KEY:
            yield file_path, key


def redirect_keys(name):
    """Return S3 keys generated for a redirect."""
    yield f"{name}.html"
    yield name
    yield f"{name}/"
    yield f"{name}/index.html"


def content_type_args(file_path):
    content_type, _ = mimetypes.guess_type(str(file_path))
    return {"ContentType": content_type} if content_type else {}


def expected_s3_keys():
    """Return every S3 key that should exist after deploy."""
    keys = {RESUME_KEY, *(key for _, key in static_files())}
    for name in REDIRECTS:
        keys.update(redirect_keys(name))
    return keys


def redirect_uploads():
    """Return upload args for generated redirect pages."""
    for name, target in REDIRECTS.items():
        html = REDIRECT_TEMPLATE.format(title=name.capitalize(), target=target)

        for key in redirect_keys(name):
            yield key, html.encode("utf-8")


def generated_files():
    """Return generated file keys, bodies, and content types."""
    yield RESUME_KEY, get_resume_pdf(), "application/pdf"

    for key, body in redirect_uploads():
        yield key, body, "text/html"


def local_path_for_key(output_dir, key):
    """Return the local filesystem path that best emulates a deployed key."""
    if key.endswith("/"):
        return output_dir / key / "index.html"

    if key in REDIRECTS:
        return output_dir / key / "index.html"

    return output_dir / key


@cache
def get_resume_pdf():
    """Return resume PDF bytes from Google Docs."""
    resume_doc_id = os.environ.get("RESUME_DOC_ID")
    if not resume_doc_id:
        raise SystemExit("RESUME_DOC_ID must be set to export resume.pdf from Google Docs")

    url = f"https://docs.google.com/document/d/{resume_doc_id}/export?format=pdf"

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content


def upload_objects(s3, bucket_name):
    """Upload static files and generated redirects to S3."""
    static = list(static_files())
    generated = list(generated_files())
    print(f"Uploading {len(static) + len(generated)} objects to S3...")

    for file_path, key in static:
        print(f"  Uploading {key}")
        s3.upload_file(
            str(file_path),
            bucket_name,
            key,
            ExtraArgs=content_type_args(file_path),
        )

    for key, body, content_type in generated:
        print(f"  Uploading {key}")
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    print(f"  Uploaded {len(static)} static files and {len(generated)} generated files")


def delete_objects(s3, bucket_name, objects):
    """Delete a batch of S3 objects and log the result."""
    response = s3.delete_objects(Bucket=bucket_name, Delete={"Objects": objects})

    for item in response.get("Deleted", []):
        print(f"  Deleted {item['Key']}")
    for error in response.get("Errors", []):
        print(f"  Failed to delete {error['Key']}: {error['Code']} {error['Message']}")


def delete_stale_objects(s3, bucket_name):
    """Delete S3 objects that are not generated from the local source."""
    print("Deleting stale S3 objects...")
    expected_keys = expected_s3_keys()
    stale_objects = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key not in expected_keys:
                stale_objects.append({"Key": key})

                if len(stale_objects) == 1000:
                    delete_objects(s3, bucket_name, stale_objects)
                    stale_objects = []

    if stale_objects:
        delete_objects(s3, bucket_name, stale_objects)


def invalidate_cloudfront(cloudfront, distribution_id):
    """Invalidate CloudFront cache."""
    print("Invalidating CloudFront cache...")

    response = cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(hash(os.urandom(16))),
        },
    )
    print(f"  Invalidation ID: {response['Invalidation']['Id']}")


def cdk_outputs(stack_name):
    if not CDK_OUTPUTS.exists():
        raise SystemExit(
            f"{CDK_OUTPUTS.name} not found. Run `cdk deploy {stack_name} --outputs-file {CDK_OUTPUTS.name}` first."
        )

    outputs = json.loads(CDK_OUTPUTS.read_text())
    if stack_name not in outputs:
        stacks = ", ".join(sorted(outputs)) or "none"
        raise SystemExit(f"Stack {stack_name!r} not found in {CDK_OUTPUTS.name}. Available stacks: {stacks}")

    stack_outputs = outputs[stack_name]
    required = {"BucketName", "DistributionId"}
    missing = required - stack_outputs.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise SystemExit(f"Stack {stack_name!r} is missing outputs: {names}")

    return stack_outputs


def upload(bucket_name, distribution_id):
    """Upload site content and invalidate CloudFront."""
    s3 = boto3.client("s3")
    cloudfront = boto3.client("cloudfront")

    upload_objects(s3, bucket_name)
    delete_stale_objects(s3, bucket_name)
    invalidate_cloudfront(cloudfront, distribution_id)


def build_local_site(output_dir=LOCAL_SITE_DIR):
    """Build a local static directory that mirrors generated deploy assets."""
    if output_dir.exists():
        shutil.rmtree(output_dir)

    shutil.copytree(STATIC_DIR, output_dir)
    for key, body, _ in generated_files():
        file_path = local_path_for_key(output_dir, key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(body)

    print(f"Built local site in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Deploy www.bovbel.com")
    parser.add_argument(
        "--local",
        action="store_true",
        help=f"Build {LOCAL_SITE_DIR.name}/ for local static serving instead of deploying",
    )
    parser.add_argument(
        "--stack",
        help="Read BucketName and DistributionId from cdk-outputs.json for this stack",
    )
    args = parser.parse_args()

    if args.local:
        build_local_site()
        return

    if not args.stack:
        parser.error("--stack is required unless --local is used")

    outputs = cdk_outputs(args.stack)
    bucket_name = outputs["BucketName"]
    distribution_id = outputs["DistributionId"]

    upload(bucket_name, distribution_id)
    print("Done!")


if __name__ == "__main__":
    main()
