# paul.bovbel.com
Personal website deployment

![Deploy sites](https://github.com/paulbovbel/www.bovbel.com/workflows/Deploy%20sites/badge.svg)

## Local Development

```bash
nix develop
uv sync

uv run pytest test.py
uv run serve-site --site paul
```

To preview Rebecca's site locally:

```bash
export SQUARE_ACCESS_TOKEN=...
uv run serve-site --site rebecca
```

`serve-site` builds and serves `sites/rebecca/build`, then dispatches
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
sites/common/           shared static files copied into every site
sites/rebecca/static/   rebecca.bovbel.com static assets
sites/rebecca/api/      rebecca.bovbel.com Lambda handlers
bovbel_site/sites.py    shared site config and build helpers
bovbel_site/local.py    local build and preview CLIs
bovbel_site/infra/      CDK stacks
```

Sites are generated into `sites/<site>/build/` before local preview or CDK deploy.

Site config in `bovbel_site/sites.py` can define external resources, redirects,
and optional Lambda Function URL behaviors. The website stack publishes each
Lambda behind the site's CloudFront distribution at the requested path pattern.

CDK deploys each generated site build directory to its S3 bucket:

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
cdk deploy --profile personal-admin paul-bovbel-com rebecca-bovbel-com
```

Run the CDK deploy with `personal-admin` after changing deployment permissions;
subsequent GitHub Actions runs deploy site contents through CDK.

## Updating Dependencies

```bash
uv lock --upgrade
```
