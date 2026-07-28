import mimetypes
import runpy
from dataclasses import dataclass, field
from pathlib import Path

from bovbel_site.build import prepare_output


ROOT_DIR = Path(__file__).parent.parent
SITES_DIR = ROOT_DIR / "sites"


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
    generator_script: Path | None = None
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
        generator_script=SITES_DIR / "paul" / "generate.py",
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
                asset_path=SITES_DIR / "rebecca",
                handler="api.catalog.handler",
                environment={
                    "SQUARE_ACCESS_TOKEN_SECRET_NAME": "rebecca/square/access-token",
                    "SQUARE_API_VERSION": "2026-07-16",
                },
                secret_names=["rebecca/square/access-token"],
            ),
            LambdaBehavior(
                id="CheckoutFunction",
                path_pattern="api/checkout",
                asset_path=SITES_DIR / "rebecca",
                handler="api.checkout.handler",
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


def generate_site(site):
    if site.generator_script:
        namespace = runpy.run_path(str(site.generator_script))
        namespace["build"](site.output_dir)
        return

    prepare_output(site.output_dir, site.static_dir)


def site_files(site):
    for file_path in site.output_dir.rglob("*"):
        if file_path.is_file():
            yield file_path, file_path.relative_to(site.output_dir).as_posix()


def content_type_args(file_path):
    content_type, _ = mimetypes.guess_type(str(file_path))
    return {"ContentType": content_type} if content_type else {}


def build_site(site):
    generate_site(site)
    print(f"Built site in {site.output_dir}")
