import shutil
from functools import cache
from pathlib import Path

import requests


SITE_DIR = Path(__file__).parent
STATIC_DIR = SITE_DIR / "static"
RESUME_DOC_ID = "1sXhQBVv2Xy5NoTsg4JvHLNmKrbC5PgRNghsUXqPWh0A"
RESUME_KEY = "resume.pdf"
REDIRECTS = {
    "meet": "https://doodle.com/bp/paulbovbel/meet",
    "resume": "https://paul.bovbel.com/resume.pdf",
}

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
  <title>Paul Bovbel - {title}</title>
  <meta http-equiv="refresh" content="0;URL={target}" />
</head>
<body>
  <p>Redirecting to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""


@cache
def get_resume_pdf():
    url = f"https://docs.google.com/document/d/{RESUME_DOC_ID}/export?format=pdf"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content


def redirect_keys(name):
    yield f"{name}.html"
    yield name
    yield f"{name}/"
    yield f"{name}/index.html"


def build(output_dir):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(STATIC_DIR, output_dir)

    (output_dir / RESUME_KEY).write_bytes(get_resume_pdf())

    for name, target in REDIRECTS.items():
        html = REDIRECT_TEMPLATE.format(title=name.capitalize(), target=target)
        for key in redirect_keys(name):
            path = output_dir / key
            if key.endswith("/") or key == name:
                path = path / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html)


if __name__ == "__main__":
    build(SITE_DIR / "build")
