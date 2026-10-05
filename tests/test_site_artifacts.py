import pytest
import requests

from bovbel_site.websites.sites import SITES_BY_NAME


@pytest.mark.build_artifact
def test_built_pages(selected_site):
    site = SITES_BY_NAME[selected_site]
    for name in ("index.html", "404.html"):
        assert "<html" in (site.output_dir / name).read_text().lower()


@pytest.mark.post_deploy
def test_live_home_and_not_found(selected_site):
    domain = SITES_BY_NAME[selected_site].domain_names[0]
    home = requests.get(f"https://{domain}/", timeout=15)
    assert home.status_code == 200
    assert "text/html" in home.headers.get("content-type", "")
    missing = requests.get(f"https://{domain}/__ci_missing_page__", timeout=15)
    assert missing.status_code == 404


@pytest.mark.post_deploy
def test_live_rebecca_api(selected_site):
    if selected_site != "rebecca":
        pytest.skip("Rebecca-only API")
    catalog = requests.get("https://rebecca.bovbel.com/api/catalog", timeout=40)
    assert catalog.status_code == 200
    assert isinstance(catalog.json()["items"], list)
    # An empty cart validates routing and rejection without creating a payment link.
    checkout = requests.post("https://rebecca.bovbel.com/api/checkout", json={"items": []}, timeout=15)
    assert checkout.status_code == 400
    assert checkout.json()["error"] == "Cart is empty"
