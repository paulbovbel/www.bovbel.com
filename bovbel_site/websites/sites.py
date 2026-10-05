import shutil
from dataclasses import dataclass, field
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[2]
SITES_DIR = ROOT_DIR / "sites"
COMMON_STATIC_DIR = SITES_DIR / "common"
RESUME_URL = "https://docs.google.com/document/d/1sXhQBVv2Xy5NoTsg4JvHLNmKrbC5PgRNghsUXqPWh0A/export?format=pdf"
REDIRECT_TEMPLATE = """\
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-57Q5PWFEVM"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-57Q5PWFEVM');
  </script>
  <title>{title} - {name}</title>
  <meta http-equiv="refresh" content="0;URL={target}" />
</head>
<body>
  <p>Redirecting to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""


@dataclass(frozen=True)
class LambdaBehavior:
    id: str
    path_pattern: str
    asset_path: Path
    handler: str = "index.handler"
    runtime: str = "PYTHON_3_13"
    timeout_seconds: int = 30
    environment: dict[str, str] | None = None
    secret_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StaticSite:
    name: str
    title: str
    stack_name: str
    bucket_name: str
    domain_names: list[str]
    role_name: str
    static_dir: Path
    output_dir: Path
    redirects: dict[str, str] = field(default_factory=dict)
    external_resources: dict[str, str] = field(default_factory=dict)
    lambda_functions: list[LambdaBehavior] = field(default_factory=list)


STATIC_SITES = [
    StaticSite(
        name="paul",
        title="Paul Bovbel",
        stack_name="paul-bovbel-com",
        bucket_name="paul.bovbel.com",
        domain_names=["paul.bovbel.com", "www.bovbel.com", "bovbel.com"],
        role_name="paul-bovbel-com-deploy",
        static_dir=SITES_DIR / "paul" / "static",
        output_dir=SITES_DIR / "paul" / "build",
        redirects={
            "meet": "https://doodle.com/bp/paulbovbel/meet",
            "resume": "https://paul.bovbel.com/resume.pdf",
        },
        external_resources={"resume.pdf": RESUME_URL},
    ),
    StaticSite(
        name="rebecca",
        title="Rebecca Bovbel",
        stack_name="rebecca-bovbel-com",
        bucket_name="rebecca.bovbel.com",
        domain_names=["rebecca.bovbel.com"],
        role_name="rebecca-bovbel-com-deploy",
        static_dir=SITES_DIR / "rebecca" / "static",
        output_dir=SITES_DIR / "rebecca" / "build",
        lambda_functions=[
            LambdaBehavior(
                id="CatalogFunction",
                path_pattern="api/catalog",
                asset_path=SITES_DIR / "rebecca" / "api",
                handler="catalog.handler",
                environment={
                    "SQUARE_ACCESS_TOKEN_SECRET_NAME": "rebecca/square/access-token",
                    "SQUARE_API_VERSION": "2026-07-16",
                },
                secret_names=["rebecca/square/access-token"],
            ),
            LambdaBehavior(
                id="CheckoutFunction",
                path_pattern="api/checkout",
                asset_path=SITES_DIR / "rebecca" / "api",
                handler="checkout.handler",
                environment={
                    "SQUARE_ACCESS_TOKEN_SECRET_NAME": "rebecca/square/access-token",
                    "SQUARE_API_VERSION": "2026-07-16",
                },
                secret_names=["rebecca/square/access-token"],
            ),
        ],
    ),
]

SITES_BY_NAME = {site.name: site for site in STATIC_SITES}
SITES_BY_STACK = {site.stack_name: site for site in STATIC_SITES}


def site_for_stack(stack_name):
    if stack_name not in SITES_BY_STACK:
        stacks = ", ".join(sorted(SITES_BY_STACK))
        raise SystemExit(f"No site mapping for stack {stack_name!r}. Known site stacks: {stacks}")

    return SITES_BY_STACK[stack_name]


def prepare_output(output_dir, static_dir=None):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    if COMMON_STATIC_DIR.exists():
        shutil.copytree(COMMON_STATIC_DIR, output_dir, dirs_exist_ok=True)

    if static_dir and static_dir.exists():
        shutil.copytree(static_dir, output_dir, dirs_exist_ok=True)


def build_site(site):
    prepare_output(site.output_dir, site.static_dir)

    for key, url in site.external_resources.items():
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        path = site.output_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)

    for name, target in site.redirects.items():
        html = REDIRECT_TEMPLATE.format(title=site.title, name=name.capitalize(), target=target)
        for key in (f"{name}.html", f"{name}/index.html"):
            path = site.output_dir / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html)
