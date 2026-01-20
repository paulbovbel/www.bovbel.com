#!/bin/bash
set -eu

echo "Downloading resume..."
curl -L "https://docs.google.com/document/d/$RESUME_DOC_ID/export?format=pdf" \
    -o static/resume.pdf

echo "Syncing to S3..."
aws s3 sync static s3://www.bovbel.com/

echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id E3EDUX8NQFYNJF \
    --paths '/*'
