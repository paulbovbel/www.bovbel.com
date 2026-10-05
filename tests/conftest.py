import urllib.request

import pytest
import requests


def pytest_addoption(parser):
    parser.addoption("--site", choices=["paul", "rebecca"], help="Site for artifact/live checks")


@pytest.fixture(autouse=True)
def no_unexpected_network(request, monkeypatch):
    if request.node.get_closest_marker("external") or request.node.get_closest_marker("post_deploy"):
        return

    def blocked(*args, **kwargs):
        raise AssertionError("Local tests must mock network access")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)


@pytest.fixture
def selected_site(request):
    site = request.config.getoption("--site")
    if not site:
        pytest.fail("Artifact and post-deploy tests require --site")
    return site
