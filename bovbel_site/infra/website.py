from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct

from bovbel_site.infra.domain import APEX_DOMAIN_NAME, HOSTED_ZONE_ID
from bovbel_site.sites import StaticSite


GITHUB_REPOSITORY = "paulbovbel/www.bovbel.com"
GITHUB_BRANCH = "master"


class WebsiteStack(Stack):
    def __init__(self, scope: Construct, site: StaticSite, account_id: str, **kwargs):
        super().__init__(scope, site.stack_name, **kwargs)

        zone = route53.HostedZone.from_hosted_zone_attributes(
            self,
            "HostedZone",
            hosted_zone_id=HOSTED_ZONE_ID,
            zone_name=APEX_DOMAIN_NAME,
        )

        bucket = s3.Bucket(
            self,
            "WebsiteBucket",
            bucket_name=site.bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        web_acl = wafv2.CfnWebACL(
            self,
            "WebAcl",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            scope="CLOUDFRONT",
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=f"{site.stack_name}-web-acl",
                sampled_requests_enabled=True,
            ),
        )
        # TODO(pbovbel) cdk does not currently expose pricing plan

        certificate = acm.Certificate(
            self,
            "Certificate",
            domain_name=site.domain_names[0],
            subject_alternative_names=site.domain_names[1:],
            validation=acm.CertificateValidation.from_dns(zone),
        )

        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_root_object="index.html",
            domain_names=site.domain_names,
            certificate=certificate,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            enable_ipv6=True,
            http_version=cloudfront.HttpVersion.HTTP2,
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            web_acl_id=web_acl.attr_arn,
        )

        for index, domain_name in enumerate(site.domain_names):
            target = route53.RecordTarget.from_alias(targets.CloudFrontTarget(distribution))
            route53.ARecord(
                self,
                f"AliasARecord{index}",
                zone=zone,
                record_name=domain_name,
                target=target,
            )
            route53.AaaaRecord(
                self,
                f"AliasAaaaRecord{index}",
                zone=zone,
                record_name=domain_name,
                target=target,
            )

        oidc_provider_arn = f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com"
        deploy_role = iam.Role(
            self,
            "DeployRole",
            role_name=site.role_name,
            assumed_by=iam.FederatedPrincipal(
                oidc_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                        "token.actions.githubusercontent.com:job_workflow_ref": (
                            f"{GITHUB_REPOSITORY}/.github/workflows/deploy.yml@refs/heads/{GITHUB_BRANCH}"
                        ),
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": (
                            f"repo:{GITHUB_REPOSITORY}:ref:refs/heads/{GITHUB_BRANCH}"
                        ),
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
        )
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:ListBucket"],
                resources=[bucket.bucket_arn],
            )
        )
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject", "s3:DeleteObject"],
                resources=[bucket.arn_for_objects("*")],
            )
        )
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudfront:CreateInvalidation"],
                resources=[
                    f"arn:aws:cloudfront::{self.account}:distribution/{distribution.distribution_id}"
                ],
            )
        )

        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "DomainNames", value=",".join(site.domain_names))
        CfnOutput(self, "DistributionId", value=distribution.distribution_id)
        CfnOutput(self, "DistributionDomainName", value=distribution.distribution_domain_name)
        CfnOutput(self, "DeployRoleArn", value=deploy_role.role_arn)
        CfnOutput(self, "HostedZoneId", value=HOSTED_ZONE_ID)
