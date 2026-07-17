import html
import tomllib
from pathlib import Path

from bovbel_site.build import prepare_output


SITE_DIR = Path(__file__).parent
CONTENT_DIR = SITE_DIR / "content"
STATIC_DIR = SITE_DIR / "static"
TEMPLATE_DIR = SITE_DIR / "templates"


def render(template, context):
    for key, value in context.items():
        template = template.replace("{{ " + key + " }}", value)
    return template


def output_path(output_dir, slug):
    return output_dir / "index.html" if not slug else output_dir / slug / "index.html"


def build(output_dir):
    prepare_output(output_dir, STATIC_DIR)

    pages = tomllib.loads((CONTENT_DIR / "pages.toml").read_text())
    template = (TEMPLATE_DIR / "page.html").read_text()

    for page in pages["page"]:
        body = (CONTENT_DIR / page["body"]).read_text()
        document = render(
            template,
            {
                "title": html.escape(page["title"]),
                "description": html.escape(page["description"]),
                "body": body,
            },
        )

        path = output_path(output_dir, page.get("slug", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(document)


if __name__ == "__main__":
    build(SITE_DIR / "build")
