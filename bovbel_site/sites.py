import mimetypes
import runpy
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).parent.parent
SITES_DIR = ROOT_DIR / "sites"


@dataclass(frozen=True)
class StaticSite:
    name: str
    title: str
    stack_name: str
    bucket_name: str
    domain_names: list[str]
    role_name: str
    output_dir: Path
    generator_script: Path


STATIC_SITES = [
    StaticSite(
        name="paul",
        title="Paul Bovbel",
        stack_name="paul-bovbel-com",
        bucket_name="paul.bovbel.com",
        domain_names=["paul.bovbel.com", "www.bovbel.com", "bovbel.com"],
        role_name="paul-bovbel-com-deploy",
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
        output_dir=SITES_DIR / "rebecca" / "build",
        generator_script=SITES_DIR / "rebecca" / "generate.py",
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
    namespace = runpy.run_path(str(site.generator_script))
    namespace["build"](site.output_dir)


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
