#!/bin/bash
set -eu

echo "Downloading resume..."
curl -L "https://docs.google.com/document/d/$RESUME_DOC_ID/export?format=pdf" \
    -o static/resume.pdf

echo "Syncing to S3..."
aws s3 sync static s3://www.bovbel.com/
aws s3 cp static/meet.html s3://www.bovbel.com/meet  # can't do this in a posix filesystem...
aws s3 cp static/resume.html s3://www.bovbel.com/resume

echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id E3EDUX8NQFYNJF \
    --paths '/*'
