#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

import boto3

from bovbel_site.sites import (
    SITES_BY_NAME,
    build_site,
    content_type_args,
    generate_site,
    site_files,
    site_for_stack,
)


CDK_OUTPUTS = Path(__file__).parent.parent / "cdk-outputs.json"


def upload_objects(site, s3, bucket_name):
    """Upload generated site files to S3."""
    files = list(site_files(site))
    print(f"Uploading {len(files)} objects to S3...")

    for file_path, key in files:
        print(f"  Uploading {key}")
        s3.upload_file(
            str(file_path),
            bucket_name,
            key,
            ExtraArgs=content_type_args(file_path),
        )

    print(f"  Uploaded {len(files)} files")


def delete_objects(s3, bucket_name, objects):
    """Delete a batch of S3 objects and log the result."""
    response = s3.delete_objects(Bucket=bucket_name, Delete={"Objects": objects})

    for item in response.get("Deleted", []):
        print(f"  Deleted {item['Key']}")
    for error in response.get("Errors", []):
        print(f"  Failed to delete {error['Key']}: {error['Code']} {error['Message']}")


def delete_stale_objects(site, s3, bucket_name):
    """Delete S3 objects that are not generated from the local source."""
    print("Deleting stale S3 objects...")
    expected_keys = {key for _, key in site_files(site)}
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


def upload(site, bucket_name, distribution_id):
    """Upload site content and invalidate CloudFront."""
    generate_site(site)
    s3 = boto3.client("s3")
    cloudfront = boto3.client("cloudfront")

    upload_objects(site, s3, bucket_name)
    delete_stale_objects(site, s3, bucket_name)
    invalidate_cloudfront(cloudfront, distribution_id)


def main():
    parser = argparse.ArgumentParser(description="Deploy a static site")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Build the site's generated output directory instead of deploying",
    )
    parser.add_argument(
        "--stack",
        help="Read BucketName and DistributionId from cdk-outputs.json for this stack",
    )
    parser.add_argument(
        "--site",
        choices=sorted(SITES_BY_NAME),
        help="Static site to build locally; deploy infers this from --stack when omitted",
    )
    args = parser.parse_args()

    if args.local:
        build_site(SITES_BY_NAME[args.site or "paul"])
        return

    if not args.stack:
        parser.error("--stack is required unless --local is used")

    site = SITES_BY_NAME[args.site] if args.site else site_for_stack(args.stack)
    outputs = cdk_outputs(args.stack)
    bucket_name = outputs["BucketName"]
    distribution_id = outputs["DistributionId"]

    upload(site, bucket_name, distribution_id)
    print("Done!")


if __name__ == "__main__":
    main()
