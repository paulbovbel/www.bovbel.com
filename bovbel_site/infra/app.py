#!/usr/bin/env python3
from aws_cdk import App

from bovbel_site.infra.domain import DomainStack
from bovbel_site.infra.mail import MailStack
from bovbel_site.infra.website import WebsiteStack
from bovbel_site.sites import STATIC_SITES


ACCOUNT_ID = "713134244406"
ENV = {"account": ACCOUNT_ID, "region": "us-east-1"}


app = App()
for site in STATIC_SITES:
    WebsiteStack(
        app,
        site,
        account_id=ACCOUNT_ID,
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
