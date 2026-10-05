#!/usr/bin/env python3
from aws_cdk import App

from bovbel_site.dns.stack import DomainStack
from bovbel_site.mail.stack import MailStack
from bovbel_site.shared.config import ACCOUNT_ID, ENV
from bovbel_site.websites.stack import WebsiteStack
from bovbel_site.websites.sites import STATIC_SITES, build_site


app = App()
# CDK stack selectors alone do not prevent the app from constructing other stacks.
# Explicit context keeps DNS-only synthesis independent of site assets/downloads.
requested = app.node.try_get_context("stacks")
known = {
    *(site.stack_name for site in STATIC_SITES), "bovbel-com-dns", "bovbel-com-mail"
}
selected = set(requested.split(",")) if requested else known
if selected - known:
    raise ValueError(f"Unknown stacks: {sorted(selected - known)}")

for site in STATIC_SITES:
    if site.stack_name not in selected:
        continue
    if app.node.try_get_context("prebuilt") == "true":
        if not (site.output_dir / "index.html").is_file():
            raise ValueError(f"Build {site.name} before synthesizing with prebuilt=true")
    else:
        build_site(site)
    WebsiteStack(
        app,
        site,
        account_id=ACCOUNT_ID,
        env=ENV,
    )
if "bovbel-com-dns" in selected:
    DomainStack(app, "bovbel-com-dns", account_id=ACCOUNT_ID, env=ENV)
if "bovbel-com-mail" in selected:
    MailStack(app, "bovbel-com-mail", env=ENV)
app.synth()
