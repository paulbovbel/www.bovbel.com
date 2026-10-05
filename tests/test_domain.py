import pytest
from aws_cdk import App, assertions

from bovbel_site.dns.stack import DNS_DEPLOY_ROLE_NAME, DomainStack


@pytest.mark.pre_deploy
def test_domain_stack_has_dns_record_and_deploy_role():
    app = App()
    stack = DomainStack(
        app,
        "bovbel-com-dns",
        account_id="123456789012",
        env={"account": "123456789012", "region": "us-east-1"},
    )
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Route53::RecordSet",
        {
            "Name": "nix-config.bovbel.com.",
            "ResourceRecords": ["paulbovbel.github.io"],
            "Type": "CNAME",
        },
    )
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": DNS_DEPLOY_ROLE_NAME,
            "AssumeRolePolicyDocument": {
                "Statement": [
                    assertions.Match.object_like(
                        {
                            "Condition": {
                                "StringEquals": {
                                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                                },
                                "StringLike": {
                                    "token.actions.githubusercontent.com:sub": (
                                        "repo:paulbovbel/www.bovbel.com:ref:refs/heads/master"
                                    )
                                },
                            }
                        }
                    )
                ]
            },
        },
    )
