#!/usr/bin/env python3
from aws_cdk import App

from domain import DomainStack
from mail import MailStack
from website import SiteConfig, WebsiteStack


ACCOUNT_ID = "713134244406"
ENV = {"account": ACCOUNT_ID, "region": "us-east-1"}


app = App()
# WebsiteStack(
#     app,
#     "dev-bovbel-com",
#     SiteConfig(
#         bucket_name="dev.bovbel.com",
#         domain_names=["dev.bovbel.com"],
#         role_name="dev-bovbel-com-deploy",
#         account_id=ACCOUNT_ID,
#     ),
#     env=ENV,
# )
WebsiteStack(
    app,
    "www-bovbel-com",
    SiteConfig(
        bucket_name="www.bovbel.com",
        domain_names=["bovbel.com", "www.bovbel.com", "paul.bovbel.com"],
        role_name="www-bovbel-com-deploy",
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
