#!/usr/bin/env python3
import io
import re
from dataclasses import replace
from functools import cache
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import pytest
import requests
from aws_cdk import App, assertions

from bovbel_site.infra.website import URL_REWRITE_FUNCTION_CODE, WebsiteStack
from bovbel_site.sites import SITES_BY_NAME, build_site


REQUEST_TIMEOUT = 10
PAUL_SITE = SITES_BY_NAME["paul"]
STATIC_DIR = PAUL_SITE.static_dir
RESUME_KEY = "resume.pdf"

INDEX_URL = f"https://{PAUL_SITE.domain_names[0]}/"
RESUME_URL = f"{INDEX_URL}{RESUME_KEY}"

META_REFRESH_RE = re.compile(
    r'<meta\s+http-equiv=["\']?refresh["\']?\s+content=["\']?\s*\d+\s*;\s*URL=["\']?([^"\'>\s]+)["\']+\s*/>',
    re.IGNORECASE,
)

REDIRECT_URLS = {
    url: target
    for name, target in PAUL_SITE.redirects.items()
    for url in (f"{INDEX_URL}{name}", f"{INDEX_URL}{name}/")
}

# Domains that block automated requests or require authentication.
SKIP_DOMAINS = {
    "linkedin.com",
    "www.linkedin.com",
    "printables.com",
    "www.printables.com",
    "wiki.ros.org",
}


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs_by_name = dict(attrs)
        for name in ("href", "src"):
            if name in attrs_by_name:
                self.links.append(attrs_by_name[name])


def http_get(url, allow_redirects=False):
    return requests.get(url, allow_redirects=allow_redirects, timeout=REQUEST_TIMEOUT)


def http_head(url):
    response = requests.head(url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
    if response.status_code == 405:
        response = http_get(url, allow_redirects=True)
    return response


@cache
def get_resume_pdf():
    response = requests.get(PAUL_SITE.external_resources[RESUME_KEY], timeout=30)
    response.raise_for_status()
    return response.content


def should_skip_url(url):
    return urlparse(url).netloc in SKIP_DOMAINS


def extract_html_links(html, base_url):
    parser = LinkExtractor()
    parser.feed(html)

    links = []
    for link in parser.links:
        if link.startswith(("javascript:", "#", "data:")):
            continue
        if "googletagmanager.com" in link or "gtag" in link:
            continue

        url = urljoin(base_url, link)
        if not should_skip_url(url):
            links.append(url)

    return links


def extract_pdf_links(content):
    import fitz

    links = set()
    with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
        for page in doc:
            for link in page.get_links():
                uri = link.get("uri")
                if uri and uri.startswith(("http://", "https://")) and not should_skip_url(uri):
                    links.add(uri)
    return sorted(links)


def is_local_url(url):
    return urlparse(url).netloc in PAUL_SITE.domain_names


def link_is_valid(url):
    if is_local_url(url):
        path = urlparse(url).path.lstrip("/")
        if path == RESUME_KEY:
            return get_resume_pdf().startswith(b"%PDF")
        return (STATIC_DIR / path).exists()

    return http_head(url).status_code < 400


def meta_refresh_target(html):
    match = META_REFRESH_RE.search(html)
    assert match, "No meta refresh tag found"
    return match.group(1)


@pytest.mark.pre_deploy
def test_paul_index_links_are_valid():
    links = extract_html_links((STATIC_DIR / "index.html").read_text(), INDEX_URL)

    assert links, "No links found in index.html"
    assert [url for url in links if not link_is_valid(url)] == []


@pytest.mark.pre_deploy
def test_paul_resume_pdf_links_are_valid():
    content = get_resume_pdf()
    links = extract_pdf_links(content)

    assert content.startswith(b"%PDF")
    assert links, "No links found in resume PDF"
    assert [url for url in links if not link_is_valid(url)] == []


@pytest.mark.pre_deploy
def test_paul_redirect_pages_are_generated(tmp_path):
    site = replace(PAUL_SITE, output_dir=tmp_path / "build")
    build_site(site)

    for name, target in PAUL_SITE.redirects.items():
        for key in (f"{name}.html", f"{name}/index.html"):
            path = site.output_dir / key
            assert path.exists()
            assert meta_refresh_target(path.read_text()) == target


@pytest.mark.pre_deploy
def test_cloudfront_rewrites_directory_urls(tmp_path):
    assert "uri + 'index.html'" in URL_REWRITE_FUNCTION_CODE
    assert "uri + '/index.html'" in URL_REWRITE_FUNCTION_CODE

    output_dir = tmp_path / "build"
    output_dir.mkdir()
    (output_dir / "index.html").write_text("home")
    site = replace(PAUL_SITE, output_dir=output_dir)

    app = App()
    stack = WebsiteStack(
        app,
        site,
        account_id="123456789012",
        env={"account": "123456789012", "region": "us-east-1"},
    )
    resources = assertions.Template.from_stack(stack).to_json()["Resources"]

    assert any(
        resource["Type"] == "AWS::CloudFront::Function"
        and "index.html" in resource["Properties"]["FunctionCode"]
        for resource in resources.values()
    )
    assert any(resource["Type"] == "Custom::CDKBucketDeployment" for resource in resources.values())

    distributions = [
        resource for resource in resources.values() if resource["Type"] == "AWS::CloudFront::Distribution"
    ]
    function_associations = distributions[0]["Properties"]["DistributionConfig"]["DefaultCacheBehavior"][
        "FunctionAssociations"
    ]
    assert function_associations[0]["EventType"] == "viewer-request"


@pytest.mark.post_deploy
@pytest.mark.parametrize("url,target", REDIRECT_URLS.items())
def test_live_meta_refresh_redirect(url, target):
    response = http_get(url)

    assert response.status_code == 200
    assert "text/html" in response.headers.get("Content-Type", "")
    assert meta_refresh_target(response.text) == target
