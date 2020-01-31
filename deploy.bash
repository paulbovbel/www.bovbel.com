#!/bin/bash
aws s3 sync . \
    --include "doc" \
    # --include resume \
    # --include index \
    # --include robots.txt \
    # --include favicon.ico \
s3://www.bovbel.com/
