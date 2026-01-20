#!/usr/bin/env python3
import requests
import pytest
import re
import io
from html.parser import HTMLParser
from urllib.parse import urlparse

import fitz  # PyMuPDF

REQUEST_TIMEOUT = 10

META_REFRESH_RE = re.compile(
    r'<meta\s+http-equiv=[\"\']?refresh[\"\']?\s+content=[\"\']?\s*\d+\s*;\s*URL=[\"\']?([^\"\'>\s]+)[\"\']+\s*/>',
    re.IGNORECASE,
)

URLS_200 = [
    "https://www.bovbel.com/",
]

URLS_PDF = [
    "https://www.bovbel.com/resume.pdf",
]

URLS_META_REFRESH = {
    "https://www.bovbel.com/resume": "https://www.bovbel.com/resume.pdf",
    "https://www.bovbel.com/resume/": "https://www.bovbel.com/resume.pdf",
    "https://www.bovbel.com/meet": "https://doodle.com/bp/paulbovbel/meet",
    "https://www.bovbel.com/meet/": "https://doodle.com/bp/paulbovbel/meet",
}

INDEX_URL = "https://www.bovbel.com/"
RESUME_URL = "https://www.bovbel.com/resume.pdf"


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


# Domains that block automated requests or require authentication
SKIP_DOMAINS = {
    "linkedin.com",
    "www.linkedin.com",
    "printables.com",
    "www.printables.com",
}


def should_skip_url(url):
    """Check if URL should be skipped based on domain blocklist."""
    parsed = urlparse(url)
    return parsed.netloc in SKIP_DOMAINS


def http_get(url, allow_redirects=False):
    """Make a GET request with consistent parameters."""
    return requests.get(url, allow_redirects=allow_redirects, timeout=REQUEST_TIMEOUT)


def http_head(url, allow_redirects=True):
    """Make a HEAD request with consistent parameters."""
    return requests.head(url, allow_redirects=allow_redirects, timeout=REQUEST_TIMEOUT)


def get_index_links():
    """Fetch index.html and extract all links."""
    r = http_get(INDEX_URL)
    r.raise_for_status()

    parser = LinkExtractor()
    parser.feed(r.text)

    links = []
    for link in parser.links:
        # Skip javascript and analytics
        if link.startswith(("javascript:", "#", "data:")):
            continue
        if "googletagmanager.com" in link or "gtag" in link:
            continue

        # Convert relative URLs to absolute
        if link.startswith("./"):
            link = INDEX_URL + link[2:]
        elif link.startswith("/"):
            link = INDEX_URL.rstrip("/") + link
        elif not link.startswith(("http://", "https://")):
            link = INDEX_URL + link

        # Skip blocklisted domains
        if should_skip_url(link):
            continue

        links.append(link)

    return links


def get_pdf_links(url):
    """Fetch PDF and extract all links."""
    r = http_get(url)
    r.raise_for_status()

    links = set()
    with fitz.open(stream=io.BytesIO(r.content), filetype="pdf") as doc:
        for page in doc:
            for link in page.get_links():
                uri = link.get("uri")
                if uri and uri.startswith(("http://", "https://")):
                    # Skip blocklisted domains
                    if not should_skip_url(uri):
                        links.add(uri)

    return list(links)


@pytest.mark.parametrize("url", URLS_200)
def test_returns_200(url):
    r = http_get(url)
    assert r.status_code == 200


@pytest.mark.parametrize("url", URLS_PDF)
def test_returns_200_pdf(url):
    r = http_get(url)
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith("application/pdf")


@pytest.mark.parametrize("url,target", URLS_META_REFRESH.items())
def test_meta_refresh_redirect(url, target):
    r = http_get(url)

    assert r.status_code == 200
    assert "text/html" in r.headers.get("Content-Type", "")

    match = META_REFRESH_RE.search(r.text)
    print(r.text)
    assert match, "No meta refresh tag found"

    assert match.group(1) == target


@pytest.fixture(scope="module")
def index_links():
    return get_index_links()


def test_index_has_links(index_links):
    """Ensure we found some links to test."""
    assert len(index_links) > 0, "No links found in index.html"


@pytest.mark.parametrize("url", get_index_links())
def test_index_link_valid(url):
    """Test that each link in index.html returns a successful response."""
    r = http_head(url)
    # Accept 200-399 range (success and redirects)
    assert r.status_code < 400, f"Link {url} returned {r.status_code}"


def test_resume_has_links():
    """Ensure we found some links in resume.pdf."""
    links = get_pdf_links(RESUME_URL)
    assert len(links) > 0, "No links found in resume.pdf"


@pytest.mark.parametrize("url", get_pdf_links(RESUME_URL))
def test_resume_link_valid(url):
    """Test that each link in resume.pdf returns a successful response."""
    r = http_head(url)
    # Accept 200-399 range (success and redirects)
    assert r.status_code < 400, f"Link {url} returned {r.status_code}"
