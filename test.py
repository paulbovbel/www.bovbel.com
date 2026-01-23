#!/usr/bin/env python3
import requests
import pytest
import re
import io
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import fitz  # PyMuPDF

REQUEST_TIMEOUT = 10
STATIC_DIR = Path(__file__).parent / "static"

INDEX_URL = "https://www.bovbel.com/"
RESUME_URL = "https://www.bovbel.com/resume.pdf"

META_REFRESH_RE = re.compile(
    r'<meta\s+http-equiv=[\"\']?refresh[\"\']?\s+content=[\"\']?\s*\d+\s*;\s*URL=[\"\']?([^\"\'>\s]+)[\"\']+\s*/>',
    re.IGNORECASE,
)

URLS_META_REFRESH = {
    "https://www.bovbel.com/resume": "https://www.bovbel.com/resume.pdf",
    "https://www.bovbel.com/resume/": "https://www.bovbel.com/resume.pdf",
    "https://www.bovbel.com/meet": "https://doodle.com/bp/paulbovbel/meet",
    "https://www.bovbel.com/meet/": "https://doodle.com/bp/paulbovbel/meet",
}

# Domains that block automated requests or require authentication
SKIP_DOMAINS = {
    "linkedin.com",
    "www.linkedin.com",
    "printables.com",
    "www.printables.com",
}


def http_get(url, allow_redirects=False):
    """Make a GET request with consistent parameters."""
    return requests.get(url, allow_redirects=allow_redirects, timeout=REQUEST_TIMEOUT)


def http_head(url, allow_redirects=True):
    """Make a HEAD request with consistent parameters."""
    return requests.head(url, allow_redirects=allow_redirects, timeout=REQUEST_TIMEOUT)


def should_skip_url(url):
    """Check if URL should be skipped based on domain blocklist."""
    parsed = urlparse(url)
    return parsed.netloc in SKIP_DOMAINS


class LinkExtractor(HTMLParser):
    """Extract all href and src attributes from HTML."""

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if "href" in attrs_dict:
            self.links.append(attrs_dict["href"])
        if "src" in attrs_dict:
            self.links.append(attrs_dict["src"])


def extract_html_links(html, base_url):
    """Extract and normalize links from HTML content."""
    parser = LinkExtractor()
    parser.feed(html)

    links = []
    for link in parser.links:
        if link.startswith(("javascript:", "#", "data:")):
            continue
        if "googletagmanager.com" in link or "gtag" in link:
            continue

        if link.startswith("./"):
            link = base_url + link[2:]
        elif link.startswith("/"):
            link = base_url.rstrip("/") + link
        elif not link.startswith(("http://", "https://")):
            link = base_url + link

        if not should_skip_url(link):
            links.append(link)

    return links


def extract_pdf_links(content):
    """Extract links from PDF content."""
    links = set()
    with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
        for page in doc:
            for link in page.get_links():
                uri = link.get("uri")
                if uri and uri.startswith(("http://", "https://")):
                    if not should_skip_url(uri):
                        links.add(uri)
    return list(links)


# =============================================================================
# Pre-deploy tests (local files)
# =============================================================================


def get_local_index_links():
    """Extract links from local index.html."""
    index_path = STATIC_DIR / "index.html"
    html = index_path.read_text()
    return extract_html_links(html, INDEX_URL)


def get_local_resume_links():
    """Extract links from local resume.pdf."""
    resume_path = STATIC_DIR / "resume.pdf"
    content = resume_path.read_bytes()
    return extract_pdf_links(content)


@pytest.mark.pre_deploy
def test_local_index_exists():
    """Ensure index.html exists."""
    assert (STATIC_DIR / "index.html").exists()


@pytest.mark.pre_deploy
def test_local_resume_exists():
    """Ensure resume.pdf exists."""
    assert (STATIC_DIR / "resume.pdf").exists()


@pytest.mark.pre_deploy
def test_local_index_has_links():
    """Ensure we found some links in local index.html."""
    links = get_local_index_links()
    assert len(links) > 0, "No links found in index.html"


@pytest.mark.pre_deploy
@pytest.mark.parametrize("url", get_local_index_links() if (STATIC_DIR / "index.html").exists() else [])
def test_local_index_link_valid(url):
    """Test that each link in local index.html is reachable."""
    r = http_head(url)
    assert r.status_code < 400, f"Link {url} returned {r.status_code}"


@pytest.mark.pre_deploy
def test_local_resume_has_links():
    """Ensure we found some links in local resume.pdf."""
    links = get_local_resume_links()
    assert len(links) > 0, "No links found in resume.pdf"


@pytest.mark.pre_deploy
@pytest.mark.parametrize("url", get_local_resume_links() if (STATIC_DIR / "resume.pdf").exists() else [])
def test_local_resume_link_valid(url):
    """Test that each link in local resume.pdf is reachable."""
    r = http_head(url)
    assert r.status_code < 400, f"Link {url} returned {r.status_code}"


# =============================================================================
# Post-deploy tests (live site)
# =============================================================================

@pytest.mark.post_deploy
@pytest.mark.parametrize("url,target", URLS_META_REFRESH.items())
def test_live_meta_refresh_redirect(url, target):
    """Test that meta refresh redirects work correctly."""
    r = http_get(url)

    assert r.status_code == 200
    assert "text/html" in r.headers.get("Content-Type", "")

    match = META_REFRESH_RE.search(r.text)
    assert match, "No meta refresh tag found"
    assert match.group(1) == target
