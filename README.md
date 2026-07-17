# paul.bovbel.com
Personal website deployment

![Deploy sites](https://github.com/paulbovbel/www.bovbel.com/workflows/Deploy%20sites/badge.svg)

## Local Development

```bash
nix develop
uv sync

uv run pytest test.py
uv run deploy-site --local --site paul
npm exec --yes serve -- sites/paul/build
```

To preview Rebecca's site locally:

```bash
uv run deploy-site --local --site rebecca
npm exec --yes serve -- sites/rebecca/build
```

## Repository Layout

Static site source lives under `sites/<site>/`:

```text
sites/paul/static/      paul.bovbel.com source files
sites/paul/generate.py  paul.bovbel.com generator
sites/rebecca/content/  rebecca.bovbel.com page content
sites/rebecca/static/   rebecca.bovbel.com static assets
sites/rebecca/templates/ rebecca.bovbel.com templates
sites/rebecca/generate.py rebecca.bovbel.com generator
bovbel_site/sites.py    shared site config and build helpers
bovbel_site/deploy.py   deployment CLI implementation
bovbel_site/infra/      CDK stacks
```

Sites are generated into `sites/<site>/build/` before local preview or deploy.

`deploy.py` maps CDK stacks to site sources:

```text
paul-bovbel-com      -> sites/paul/build/
rebecca-bovbel-com   -> sites/rebecca/build/
```

## Ship it

To provision the S3 bucket, CloudFront distribution, Route 53 records, ACM certificate, and deploy IAM role:

```bash
nix develop
uv sync

export AWS_PROFILE=personal-admin
cdk bootstrap aws://713134244406/us-east-1
cdk deploy paul-bovbel-com --outputs-file cdk-outputs.json
uv run deploy-site --stack paul-bovbel-com
```

To ship Rebecca's site after its stack is provisioned:

```bash
cdk deploy rebecca-bovbel-com --outputs-file cdk-outputs.json
uv run deploy-site --stack rebecca-bovbel-com
```

## Updating Dependencies

```bash
uv lock --upgrade
```
