from aws_cdk import core, aws_ec2


class BakeryStack(core.Stack):
    def __init__(
        self, scope: core.Construct, construct_id: str, identifier: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = aws_ec2.Vpc(
            self,
            id=f"bakery-vpc-{identifier}",
            cidr="10.0.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True,
            nat_gateways=0,
            subnet_configuration=[
                aws_ec2.SubnetConfiguration(
                    name="PublicSubnet1",
                    subnet_type=aws_ec2.SubnetType.PUBLIC
                )
            ],
            max_azs=3
        )
