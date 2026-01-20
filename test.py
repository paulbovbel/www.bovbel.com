#!/usr/bin/env python3
import requests
import pytest
import re

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


@pytest.mark.parametrize("url", URLS_200)
def test_returns_200(url):
    r = requests.get(url, allow_redirects=False, timeout=5)
    assert r.status_code == 200


@pytest.mark.parametrize("url", URLS_PDF)
def test_returns_200_pdf(url):
    r = requests.get(url, allow_redirects=False, timeout=5)
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith("application/pdf")


@pytest.mark.parametrize("url,target", URLS_META_REFRESH.items())
def test_meta_refresh_redirect(url, target):
    r = requests.get(url, allow_redirects=False, timeout=5)

    assert r.status_code == 200
    assert "text/html" in r.headers.get("Content-Type", "")

    match = META_REFRESH_RE.search(r.text)
    print(r.text)
    assert match, "No meta refresh tag found"

    assert match.group(1) == target
