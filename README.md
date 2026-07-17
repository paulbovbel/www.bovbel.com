# www.bovbel.com
Personal website deployment

![Deploy www.bovbel.com](https://github.com/paulbovbel/www.bovbel.com/workflows/Deploy%20www.bovbel.com/badge.svg)

## Local Development

```bash
nix develop
uv sync

export RESUME_DOC_ID="your-google-doc-id"
uv run pytest test.py
uv run python deploy.py --local
npm exec --yes serve -- .local-site
```

## Ship it

To provision the S3 bucket, CloudFront distribution, Route 53 records, ACM certificate, and deploy IAM role:

```bash
nix develop
uv sync

export AWS_PROFILE=personal-admin
export RESUME_DOC_ID="your-google-doc-id"
cdk bootstrap aws://713134244406/us-east-1
cdk deploy www-bovbel-com --outputs-file cdk-outputs.json
uv run python deploy.py --stack www-bovbel-com
```

## Updating Dependencies

```bash
uv lock --upgrade
```
