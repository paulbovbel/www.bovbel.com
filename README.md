# paul.bovbel.com
Personal website deployment

![Deploy sites](https://github.com/paulbovbel/www.bovbel.com/workflows/Deploy%20sites/badge.svg)

## Local Development

```bash
nix develop
uv sync

uv run pytest tests
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
bovbel_site/websites/   site config, builds, local preview, and WebsiteStack
bovbel_site/dns/        DNS records and DomainStack
bovbel_site/mail/       manually deployed MailStack
bovbel_site/shared/     domain/account config, deploy roles, and DNS helpers
bovbel_site/app.py      CDK application composing the stacks
```

Sites are generated into `sites/<site>/build/` before local preview or CDK deploy.

Site config in `bovbel_site/websites/sites.py` can define external resources, redirects,
and optional Lambda Function URL behaviors. The website stack publishes each
Lambda behind the site's CloudFront distribution at the requested path pattern.

CDK deploys each generated site build directory to its S3 bucket:

```text
paul-bovbel-com      -> sites/paul/build/
rebecca-bovbel-com   -> sites/rebecca/build/
```

## CI and validation

The **Deploy sites** workflow always runs full **CI** validation: local tests,
both site builds, artifact checks, and CDK synthesis. On `master`, three explicit
jobs deploy Paul, Rebecca, and DNS through the shared `deploy-stack.yml` workflow.
`dorny/paths-filter` skips deployment jobs for unchanged components; it does not
select tests or builds. Pull requests run only CI, without uploading the cloud
assembly. The **CI** check can be made required in branch protection settings.

- Nix and uv downloads are cached. Python is pinned in `.python-version`, and CI
  uses `uv sync --locked`.
- Local tests run without network access. Both sites have post-deploy smoke tests;
  Rebecca's checkout smoke test submits an empty cart and creates no payment link.
- Each site is built once. The generated files are tested, then included
  in a CDK cloud assembly. Deployment jobs consume that assembly without rebuilding
  or fetching the resume again.
- Paul and Rebecca source changes deploy that site. Common assets, build helpers,
  and website infrastructure deploy both sites. DNS record changes deploy only
  DNS; shared domain constants live in `bovbel_site/shared/config.py`.
  Shared configuration, dependencies, tests, and workflow changes deploy all three.
  The filters are defined in `deploy.yml`; update them when adding source locations.
- Modules are grouped by deployment scope, so new modules inside an existing
  component directory automatically match its filter. Components may import
  `shared`, but should not import each other. Generic DNS helpers live in
  `shared/dns.py`, while DNS and mail each own their record definitions.
- Documentation-only changes still get full CI but skip deployment. Mail is
  synthesized for validation and remains manually deployed.
- Production runs are serialized without cancelling an active deployment. PR
  checks cancel superseded runs.
- Pytest failures appear directly in job logs; no separate test-report artifacts
  or reporting action are needed.

Manual and scheduled runs deploy all three stacks. Use **Run workflow** on `master`
after a cancelled or superseded production run, or **Re-run jobs** to retry a
failed run. Push filtering compares against the previous push, not the last
successful deployment. A weekly Tuesday run at 21:17 UTC refreshes Paul's
externally maintained resume. **External links** runs separately at 21:47 UTC Tuesdays or
manually, checking deduplicated third-party URLs with six workers. Failures are
reported there without blocking deployment.

Local equivalents (inside `nix develop`):

```bash
uv sync --locked
actionlint
uv run pytest tests                         # offline local tests
uv run build-site --site paul               # downloads the current resume once
uv run pytest tests -m build_artifact --site paul
cdk synth --no-lookups -c stacks=paul-bovbel-com -c prebuilt=true
uv run pytest tests -m external             # third-party link checks
uv run pytest tests -m post_deploy --site rebecca
```

For DNS-only synthesis, use `cdk synth --no-lookups -c stacks=bovbel-com-dns`.
The `stacks` context accepts comma-separated stack names. Without `prebuilt=true`,
selected site stacks build their assets automatically for local CDK use.

## Ship it

To provision the S3 bucket, CloudFront distribution, Route 53 records, ACM certificate, and deploy IAM role:

```bash
nix develop
uv sync

export AWS_PROFILE=personal-admin
cdk bootstrap aws://713134244406/us-east-1
cdk deploy --profile personal-admin \
  bovbel-com-dns \
  bovbel-com-mail \
  paul-bovbel-com \
  rebecca-bovbel-com
```

Run the CDK deploy with `personal-admin` after changing deployment permissions;
subsequent GitHub Actions runs deploy the DNS and site stacks through CDK.

## Updating Dependencies

Dependabot checks GitHub Actions and Python (`pyproject.toml` / `uv.lock`)
dependencies weekly, grouping version updates into one PR per ecosystem.
Actionlint is available in `nix develop` and runs as part of CI.

For a manual Python dependency refresh:

```bash
uv lock --upgrade
```
