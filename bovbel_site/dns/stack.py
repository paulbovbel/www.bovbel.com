from aws_cdk import CfnOutput, Stack
from constructs import Construct

from bovbel_site.shared.config import APEX_DOMAIN_NAME, HOSTED_ZONE_ID
from bovbel_site.shared.deployment import create_github_deploy_role
from bovbel_site.shared.dns import DnsRecord, create_dns_records


DNS_DEPLOY_ROLE_NAME = "bovbel-com-dns-deploy"
# bovbel.com is registered in Route53 Domains and delegated to this public hosted zone.
HOSTED_ZONE_NAME_SERVERS = [
    "ns-565.awsdns-06.net",
    "ns-1257.awsdns-29.org",
    "ns-276.awsdns-34.com",
    "ns-1980.awsdns-55.co.uk",
]


DOMAIN_DNS_RECORDS = [
    DnsRecord(
        id="CalCnameRecord",
        name="cal.bovbel.com",
        type="CNAME",
        values=["ghs.googlehosted.com"],
    ),
    DnsRecord(
        id="DriveCnameRecord",
        name="drive.bovbel.com",
        type="CNAME",
        values=["ghs.googlehosted.com"],
    ),
    DnsRecord(
        id="FirefoxSyncARecord",
        name="firefox-sync.bovbel.com",
        type="A",
        values=["100.84.167.37"],
    ),
    DnsRecord(
        id="FranklinARecord",
        name="franklin.bovbel.com",
        type="A",
        ttl=3600,
        values=["100.87.17.74"],
    ),
    DnsRecord(
        id="HomeAssistantCnameRecord",
        name="homeassistant.bovbel.com",
        type="CNAME",
        values=["s8bl8plici16s4h043gl5tfrb2spka7d.ui.nabu.casa"],
    ),
    DnsRecord(
        id="HomeAssistantAcmeChallengeCnameRecord",
        name="_acme-challenge.homeassistant.bovbel.com",
        type="CNAME",
        values=["_acme-challenge.s8bl8plici16s4h043gl5tfrb2spka7d.ui.nabu.casa"],
    ),
    DnsRecord(
        id="NixConfigCnameRecord",
        name="nix-config.bovbel.com",
        type="CNAME",
        values=["paulbovbel.github.io"],
    ),
]


class DomainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, account_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        create_dns_records(self, DOMAIN_DNS_RECORDS)
        deploy_role = create_github_deploy_role(self, account_id, DNS_DEPLOY_ROLE_NAME)

        CfnOutput(self, "DomainName", value=APEX_DOMAIN_NAME)
        CfnOutput(self, "DeployRoleArn", value=deploy_role.role_arn)
        CfnOutput(self, "HostedZoneId", value=HOSTED_ZONE_ID)
