#!/bin/bash
set -u
set -e

echo "Creating venv..."
python3 -m venv venv
venv/bin/pip install -r requirements.txt

if [ ! -f "secret/token.json" ]; then
    echo "Pulling secret token...   "
    mkdir -p secret
    echo $GOOGLE_TOKEN > secret/token.json
fi

echo "Pulling resume..."
venv/bin/python get_resume.py

echo "Syncing to s3 bucket..."
aws s3 sync static s3://www.bovbel.com/

echo "Invalidating cache..."
aws cloudfront create-invalidation \
    --distribution-id E3EDUX8NQFYNJF \
    --paths '/*'
