from aws_cdk import CfnOutput, DefaultStackSynthesizer, Duration, RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct

from bovbel_site.infra.domain import APEX_DOMAIN_NAME, HOSTED_ZONE_ID
from bovbel_site.sites import LambdaBehavior, StaticSite


GITHUB_REPOSITORY = "paulbovbel/www.bovbel.com"
GITHUB_BRANCH = "master"
URL_REWRITE_FUNCTION_CODE = """
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    if (uri.slice(-1) === '/') {
        request.uri = uri + 'index.html';
    } else if (uri.split('/').pop().indexOf('.') === -1) {
        request.uri = uri + '/index.html';
    }

    return request;
}
""".strip()


def construct_id(value):
    return "".join(character for character in value if character.isalnum())


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

        additional_behaviors = self.lambda_behaviors(site)
        url_rewrite_function = cloudfront.Function(
            self,
            "UrlRewriteFunction",
            code=cloudfront.FunctionCode.from_inline(URL_REWRITE_FUNCTION_CODE),
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
                function_associations=[
                    cloudfront.FunctionAssociation(
                        event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                        function=url_rewrite_function,
                    )
                ],
            ),
            enable_ipv6=True,
            http_version=cloudfront.HttpVersion.HTTP2,
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            web_acl_id=web_acl.attr_arn,
            additional_behaviors=additional_behaviors or None,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=404,
                    response_page_path="/404.html",
                    ttl=Duration.minutes(5),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=404,
                    response_page_path="/404.html",
                    ttl=Duration.minutes(5),
                ),
            ],
        )

        s3deploy.BucketDeployment(
            self,
            "WebsiteDeployment",
            sources=[s3deploy.Source.asset(str(site.output_dir))],
            destination_bucket=bucket,
            distribution=distribution,
            distribution_paths=["/*"],
            prune=True,
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
                actions=["sts:AssumeRole"],
                resources=[
                    f"arn:aws:iam::{self.account}:role/cdk-{DefaultStackSynthesizer.DEFAULT_QUALIFIER}-*"
                    f"{self.account}-{self.region}"
                ],
            )
        )
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/cdk-bootstrap/"
                    f"{DefaultStackSynthesizer.DEFAULT_QUALIFIER}/version"
                ],
            )
        )

        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "DomainNames", value=",".join(site.domain_names))
        CfnOutput(self, "DistributionId", value=distribution.distribution_id)
        CfnOutput(self, "DistributionDomainName", value=distribution.distribution_domain_name)
        CfnOutput(self, "DeployRoleArn", value=deploy_role.role_arn)
        CfnOutput(self, "HostedZoneId", value=HOSTED_ZONE_ID)

    def lambda_behaviors(self, site):
        return {
            config.path_pattern: self.lambda_behavior(config)
            for config in site.lambda_functions
        }

    def lambda_behavior(self, config: LambdaBehavior):
        function = lambda_.Function(
            self,
            config.id,
            runtime=getattr(lambda_.Runtime, config.runtime),
            handler=config.handler,
            code=lambda_.Code.from_asset(str(config.asset_path)),
            timeout=Duration.seconds(config.timeout_seconds),
            environment=config.environment,
        )

        for secret_name in config.secret_names:
            secret = secretsmanager.Secret.from_secret_name_v2(
                self,
                f"{config.id}{construct_id(secret_name)}Secret",
                secret_name,
            )
            secret.grant_read(function)

        function_url = function.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
        )
        return cloudfront.BehaviorOptions(
            origin=origins.FunctionUrlOrigin(function_url),
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        )
