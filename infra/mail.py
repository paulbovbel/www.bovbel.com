from dataclasses import dataclass

from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_ses as ses
from constructs import Construct

from domain import DnsRecord, create_dns_records


SES_DKIM_HOSTED_ZONE = "dkim.amazonses.com"
SES_FEEDBACK_FORWARDING_ENABLED = True
SES_DKIM_SIGNING_ENABLED = True
SES_DKIM_KEY_LENGTH = "RSA_1024_BIT"
SES_MAIL_FROM_BEHAVIOR_ON_MX_FAILURE = "USE_DEFAULT_VALUE"


@dataclass(frozen=True)
class SesIdentityConfig:
    identity: str
    verification_token: str
    dkim_tokens: list[str]


BOVBEL_SES_IDENTITY = SesIdentityConfig(
    identity="bovbel.com",
    verification_token="TB9MtfQwEUGGe81yuUouh1ylup4kPVKgK99WJ/hhySg=",
    dkim_tokens=[
        "mmedxg26w4yioc3qrtfop52tt774h2t2",
        "sdjkflnepjiph7qgkry2qysfn6buitca",
        "wthyuuty2l32vrkx7mn5g3cnpbyq2nid",
    ],
)
VEDELL_SES_IDENTITY = SesIdentityConfig(
    identity="vedell.ca",
    verification_token="FTOTm7AsBd+gprO8ugwXG4m8UgBbT4iEugXhyoiJzSY=",
    dkim_tokens=[
        "e5cxkubx4r5bmcfppyff3c6jj7b4xjp5",
        "wsfktnaoyijp2nph5wr3kutuiauzw7g6",
        "vfbqinpkvfsxabddjubrhioy46ji4nmb",
    ],
)
SES_IDENTITIES = [BOVBEL_SES_IDENTITY, VEDELL_SES_IDENTITY]

GOOGLE_WORKSPACE_MX_RECORDS = [
    "10 ASPMX.L.GOOGLE.COM.",
    "20 ALT1.ASPMX.L.GOOGLE.COM.",
    "20 ALT2.ASPMX.L.GOOGLE.COM.",
    "30 ASPMX2.GOOGLEMAIL.COM.",
    "30 ASPMX3.GOOGLEMAIL.COM.",
    "30 ASPMX4.GOOGLEMAIL.COM.",
    "30 ASPMX5.GOOGLEMAIL.COM.",
]
GOOGLE_WORKSPACE_SPF = '"v=spf1 include:_spf.google.com ~all"'
DMARC_POLICY = '"v=DMARC1; p=none; rua=mailto:dmarc@bovbel.com; adkim=s; aspf=s"'
LEGACY_DKIM_PUBLIC_KEY = (
    '"v=DKIM1; k=rsa; '
    "p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/aDy338jFD4zjsmnUcgZZfHr+"
    "p5u3FVMrt1MBP0pNytLk19bs7qMKlEuYn8B8mE0VG6E1Mgi7a4xnb94ajoa11S98BF+"
    "tZITZWFTJYQsetmnIv0N9dvWLFQbaaRoveI2FlDwK5XXJeVAXeEjojMWnyDpzPguN/"
    '0P5z/8hDcmU+wIDAQAB"'
)


def ses_email_identity(scope: Construct, config: SesIdentityConfig):
    identity = ses.CfnEmailIdentity(
        scope,
        f"SesEmailIdentity{config.identity.replace('.', '')}",
        email_identity=config.identity,
        dkim_attributes=ses.CfnEmailIdentity.DkimAttributesProperty(
            signing_enabled=SES_DKIM_SIGNING_ENABLED,
        ),
        dkim_signing_attributes=ses.CfnEmailIdentity.DkimSigningAttributesProperty(
            next_signing_key_length=SES_DKIM_KEY_LENGTH,
        ),
        feedback_attributes=ses.CfnEmailIdentity.FeedbackAttributesProperty(
            email_forwarding_enabled=SES_FEEDBACK_FORWARDING_ENABLED,
        ),
        mail_from_attributes=ses.CfnEmailIdentity.MailFromAttributesProperty(
            behavior_on_mx_failure=SES_MAIL_FROM_BEHAVIOR_ON_MX_FAILURE,
        ),
    )
    identity.apply_removal_policy(RemovalPolicy.RETAIN)
    return identity


def mail_dns_records():
    config = BOVBEL_SES_IDENTITY
    records = [
        DnsRecord(
            id="ApexMxRecord",
            name=config.identity,
            type="MX",
            values=GOOGLE_WORKSPACE_MX_RECORDS,
        ),
        DnsRecord(
            id="ApexSpfRecord",
            name=config.identity,
            type="SPF",
            values=[GOOGLE_WORKSPACE_SPF],
        ),
        DnsRecord(
            id="ApexTxtRecord",
            name=config.identity,
            type="TXT",
            values=[GOOGLE_WORKSPACE_SPF],
        ),
        DnsRecord(
            id="SesVerificationTxtRecord",
            name=f"_amazonses.{config.identity}",
            type="TXT",
            values=[f'"{config.verification_token}"'],
        ),
        DnsRecord(
            id="DmarcTxtRecord",
            name=f"_dmarc.{config.identity}",
            type="TXT",
            values=[DMARC_POLICY],
        ),
        DnsRecord(
            id="LegacyDkimTxtRecord",
            name=f"bovbel._domainkey.{config.identity}",
            type="TXT",
            values=[LEGACY_DKIM_PUBLIC_KEY],
        ),
        DnsRecord(
            id="MailCnameRecord",
            name=f"mail.{config.identity}",
            type="CNAME",
            values=["ghs.googlehosted.com"],
        ),
    ]

    for index, token in enumerate(config.dkim_tokens, start=1):
        records.append(
            DnsRecord(
                id=f"SesDkimCnameRecord{index}",
                name=f"{token}._domainkey.{config.identity}",
                type="CNAME",
                values=[f"{token}.{SES_DKIM_HOSTED_ZONE}"],
            )
        )

    return records


class MailStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        for config in SES_IDENTITIES:
            ses_email_identity(self, config)

        create_dns_records(self, mail_dns_records())

        CfnOutput(self, "SesIdentities", value=",".join(config.identity for config in SES_IDENTITIES))
