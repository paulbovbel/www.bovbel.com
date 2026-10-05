import json
import runpy
import subprocess
import sys
from dataclasses import replace

import pytest
from aws_cdk import App

from bovbel_site.websites import sites
from bovbel_site.websites.stack import WebsiteStack


@pytest.mark.pre_deploy
def test_dns_synthesis_does_not_build_sites(tmp_path, monkeypatch):
    def unexpected_build(site):
        pytest.fail(f"DNS synthesis tried to build {site.name}")

    monkeypatch.setattr(sites, "build_site", unexpected_build)
    monkeypatch.setattr("aws_cdk.App", lambda: App(
        context={"stacks": "bovbel-com-dns"}, outdir=str(tmp_path)
    ))
    runpy.run_module("bovbel_site.app", run_name="__main__")
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    stacks = [key for key, value in manifest["artifacts"].items() if value["type"] == "aws:cloudformation:stack"]
    assert stacks == ["bovbel-com-dns"]


@pytest.mark.pre_deploy
def test_lambda_assets_contain_only_importable_api_code(tmp_path):
    output = tmp_path / "site"
    output.mkdir()
    (output / "index.html").write_text("home")
    site = replace(sites.SITES_BY_NAME["rebecca"], output_dir=output)
    assembly = tmp_path / "assembly"
    app = App(outdir=str(assembly))
    WebsiteStack(app, site, account_id="123456789012", env={"account": "123456789012", "region": "us-east-1"})
    app.synth()
    api_assets = [asset for asset in assembly.glob("asset.*") if (asset / "catalog.py").is_file()]
    assert len(api_assets) == 1
    asset = api_assets[0]
    assert {path.name for path in asset.iterdir()} == {"__init__.py", "catalog.py", "checkout.py", "common.py"}
    subprocess.run(
        [sys.executable, "-c", "import catalog, checkout; assert callable(catalog.handler); assert callable(checkout.handler)"],
        cwd=asset, check=True,
    )
