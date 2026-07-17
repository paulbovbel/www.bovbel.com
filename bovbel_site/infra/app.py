#!/usr/bin/env python3
from aws_cdk import App

from bovbel_site.infra.domain import DomainStack
from bovbel_site.infra.mail import MailStack
from bovbel_site.infra.website import SiteConfig, WebsiteStack
from bovbel_site.sites import STATIC_SITES


ACCOUNT_ID = "713134244406"
ENV = {"account": ACCOUNT_ID, "region": "us-east-1"}


app = App()
for site in STATIC_SITES:
    WebsiteStack(
        app,
        site.stack_name,
        SiteConfig(
            bucket_name=site.bucket_name,
            domain_names=site.domain_names,
            role_name=site.role_name,
            account_id=ACCOUNT_ID,
        ),
        env=ENV,
    )
DomainStack(
    app,
    "bovbel-com-dns",
    env=ENV,
)
MailStack(
    app,
    "bovbel-com-mail",
    env=ENV,
)
app.synth()
