# paul.bovbel.com
Personal website deployment

![Deploy sites](https://github.com/paulbovbel/www.bovbel.com/workflows/Deploy%20sites/badge.svg)

## Local Development

```bash
nix develop
uv sync

uv run pytest test.py
uv run deploy-site --site paul
uv run deploy-site --serve --site paul
```

To preview Rebecca's site locally:

```bash
export SQUARE_ACCESS_TOKEN=...
uv run deploy-site --site rebecca
uv run deploy-site --serve --site rebecca
```

The dev server builds and serves `sites/rebecca/build`, then dispatches
`/api/catalog` and `/api/checkout` to the local Lambda handlers.

Rebecca's gallery is loaded from `/api/catalog`, which reads Square catalog items
at request time. The generated gallery stores Square variation IDs in a
client-side cart, then posts them to `/api/checkout`. In AWS, the Lambdas read
the Square access token from the Secrets Manager secret named
`rebecca/square/access-token`; locally, `SQUARE_ACCESS_TOKEN` is used when set.
The secret can be either the raw token or JSON with an `access_token` field. Set
`SQUARE_ENVIRONMENT=sandbox` to read from the Square sandbox; production is used
by default. Set `SQUARE_LOCATION_ID` to choose the checkout location; otherwise
the first active location is used.

## Repository Layout

Static site source lives under `sites/<site>/`:

```text
sites/paul/static/      paul.bovbel.com source files
sites/paul/generate.py  paul.bovbel.com generator
sites/common/           shared static files copied into every site
sites/rebecca/static/   rebecca.bovbel.com static assets
sites/rebecca/api/      rebecca.bovbel.com Lambda handlers
sites/rebecca/dev_server.py rebecca.bovbel.com local API/static server
bovbel_site/sites.py    shared site config and build helpers
bovbel_site/deploy.py   deployment CLI implementation
bovbel_site/infra/      CDK stacks
```

Sites are generated into `sites/<site>/build/` before local preview or deploy.

A site generator can also export optional Lambda Function URL behaviors for CDK
by defining `lambda_functions`, a list of `bovbel_site.sites.LambdaBehavior`
values. The website stack publishes each function behind the site's CloudFront
distribution at the requested path pattern.

`bovbel_site/deploy.py` maps CDK stacks to site sources:

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
cdk deploy --profile personal-admin paul-bovbel-com rebecca-bovbel-com --outputs-file cdk-outputs.json

uv run deploy-site --profile personal-admin --stack paul-bovbel-com
uv run deploy-site --profile personal-admin --stack rebecca-bovbel-com
```

## Updating Dependencies

```bash
uv lock --upgrade
```
