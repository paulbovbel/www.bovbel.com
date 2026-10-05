from dataclasses import dataclass

from aws_cdk import RemovalPolicy
from aws_cdk import aws_route53 as route53
from constructs import Construct

from bovbel_site.shared.config import HOSTED_ZONE_ID


@dataclass(frozen=True)
class DnsRecord:
    id: str
    name: str
    type: str
    values: list[str]
    ttl: int = 300


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
