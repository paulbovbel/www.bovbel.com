from dataclasses import dataclass

from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_route53 as route53
from constructs import Construct


APEX_DOMAIN_NAME = "bovbel.com"
HOSTED_ZONE_ID = "ZJMZZCLW5S6T9"
# bovbel.com is registered in Route53 Domains and delegated to this public hosted zone.
HOSTED_ZONE_NAME_SERVERS = [
    "ns-565.awsdns-06.net",
    "ns-1257.awsdns-29.org",
    "ns-276.awsdns-34.com",
    "ns-1980.awsdns-55.co.uk",
]


@dataclass(frozen=True)
class DnsRecord:
    id: str
    name: str
    type: str
    values: list[str]
    ttl: int = 300


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
]


def create_dns_record(scope: Construct, record: DnsRecord):
    resource = route53.CfnRecordSet(
        scope,
        record.id,
        hosted_zone_id=HOSTED_ZONE_ID,
        name=f"{record.name}.",
        type=record.type,
        ttl=str(record.ttl),
        resource_records=record.values,
    )

    resource.apply_removal_policy(RemovalPolicy.RETAIN)
    return resource


def create_dns_records(scope: Construct, records: list[DnsRecord]):
    return [create_dns_record(scope, record) for record in records]


class DomainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        create_dns_records(self, DOMAIN_DNS_RECORDS)

        CfnOutput(self, "DomainName", value=APEX_DOMAIN_NAME)
        CfnOutput(self, "HostedZoneId", value=HOSTED_ZONE_ID)
