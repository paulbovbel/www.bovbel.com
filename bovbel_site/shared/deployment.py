from aws_cdk import DefaultStackSynthesizer, Stack
from aws_cdk import aws_iam as iam


GITHUB_REPOSITORY = "paulbovbel/www.bovbel.com"
GITHUB_BRANCH = "master"


def create_github_deploy_role(scope: Stack, account_id: str, role_name: str):
    oidc_provider_arn = f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com"
    deploy_role = iam.Role(
        scope,
        "DeployRole",
        role_name=role_name,
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
                f"arn:aws:iam::{scope.account}:role/cdk-{DefaultStackSynthesizer.DEFAULT_QUALIFIER}-*"
                f"{scope.account}-{scope.region}"
            ],
        )
    )
    deploy_role.add_to_policy(
        iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[
                f"arn:aws:ssm:{scope.region}:{scope.account}:parameter/cdk-bootstrap/"
                f"{DefaultStackSynthesizer.DEFAULT_QUALIFIER}/version"
            ],
        )
    )
    return deploy_role
