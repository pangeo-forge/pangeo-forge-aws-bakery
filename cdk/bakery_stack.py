import os

from aws_cdk import (
    aws_ec2,
    aws_ecr,
    aws_ecs,
    aws_ecs_patterns,
    aws_iam,
    aws_s3,
    aws_secretsmanager,
    core,
)


class BakeryStack(core.Stack):
    def __init__(
        self, scope: core.Construct, construct_id: str, identifier: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        bucket = aws_s3.Bucket(
            self,
            id=f"flow-storage-bucket-{identifier}",
            auto_delete_objects=True,
            removal_policy=core.RemovalPolicy.DESTROY,
        )
        cache_bucket = aws_s3.Bucket(
            self,
            id=f"flow-cache-bucket-{identifier}",
            auto_delete_objects=True,
            removal_policy=core.RemovalPolicy.DESTROY,
        )
        vpc = aws_ec2.Vpc(
            self,
            id=f"bakery-vpc-{identifier}",
            cidr="10.0.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True,
            nat_gateways=0,
            subnet_configuration=[
                aws_ec2.SubnetConfiguration(
                    name="PublicSubnet1", subnet_type=aws_ec2.SubnetType.PUBLIC
                )
            ],
            max_azs=3,
        )
        security_group = aws_ec2.SecurityGroup(
            self,
            id="security-group-{identifier}",
            vpc=vpc,
        )
        security_group.add_ingress_rule(
            aws_ec2.Peer.any_ipv4(), aws_ec2.Port.tcp_range(8786, 8787)
        )
        security_group.add_ingress_rule(
            aws_ec2.Peer.any_ipv6(), aws_ec2.Port.tcp_range(8786, 8787)
        )
        security_group.add_ingress_rule(security_group, aws_ec2.Port.all_tcp())
        cluster = aws_ecs.Cluster(
            self,
            id=f"bakery-cluster-{identifier}",
            vpc=vpc,
        )

        ecs_task_role = aws_iam.Role(
            self,
            id=f"prefect-ecs-task-role-{identifier}",
            assumed_by=aws_iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
        )
        ecs_task_role.add_to_policy(
            aws_iam.PolicyStatement(
                resources=["*"],
                actions=[
                    "iam:ListRoleTags",
                ],
            )
        )
        ecs_task_role.add_to_policy(
            aws_iam.PolicyStatement(
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:dask-ecs*"
                ],
                actions=[
                    "logs:GetLogEvents",
                ],
            )
        )
        bucket.grant_read_write(ecs_task_role)
        cache_bucket.grant_read_write(ecs_task_role)

        ecs_task_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                managed_policy_name="AmazonECS_FullAccess"
            )
        )

        prefect_ecs_agent_task_definition = aws_ecs.FargateTaskDefinition(
            self,
            id=f"prefect-ecs-agent-task-definition-{identifier}",
            cpu=512,
            memory_limit_mib=2048,
            task_role=ecs_task_role,
        )

        runner_token_secret = aws_ecs.Secret.from_secrets_manager(
            secret=aws_secretsmanager.Secret.from_secret_arn(
                self,
                id=f"prefect-cloud-runner-token-{identifier}",
                secret_arn=os.environ["RUNNER_TOKEN_SECRET_ARN"],
            ),
            field="RUNNER_TOKEN",
        )

        prefect_ecs_agent_task_definition.add_container(
            id=f"prefect-ecs-agent-task-container-{identifier}",
            image=aws_ecs.ContainerImage.from_ecr_repository(
                aws_ecr.Repository.from_repository_name(
                    self,
                    id=f"pangeo-forge-aws-bakery-agent-repo-{identifier}",
                    repository_name="pangeo-forge-aws-bakery-agent",
                )
            ),
            port_mappings=[aws_ecs.PortMapping(container_port=8080, host_port=8080)],
            logging=aws_ecs.LogDriver.aws_logs(stream_prefix="ecs-agent"),
            environment={
                "PREFECT__CLOUD__AGENT__LABELS": os.environ["PREFECT_AGENT_LABELS"]
            },
            secrets={"PREFECT__CLOUD__AGENT__AUTH_TOKEN": runner_token_secret},
            command=[
                "--cluster",
                cluster.cluster_arn,
                "--task-role-arn",
                ecs_task_role.role_arn,
            ],
        )

        prefect_ecs_agent_service = (
            aws_ecs_patterns.ApplicationLoadBalancedFargateService(
                self,
                id=f"prefect-ecs-agent-service-{identifier}",
                assign_public_ip=True,
                platform_version=aws_ecs.FargatePlatformVersion.LATEST,
                desired_count=1,
                task_definition=prefect_ecs_agent_task_definition,
                cluster=cluster,
                propagate_tags=aws_ecs.PropagatedTagSource.SERVICE,
            )
        )

        prefect_ecs_agent_service.target_group.configure_health_check(
            path="/api/health", port="8080"
        )

        ecs_task_execution_role = aws_iam.Role(
            self,
            "taskExecutionRole",
            assumed_by=aws_iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
            ],
        )

        core.CfnOutput(
            self,
            id=f"prefect-task-role-arn-output-{identifier}",
            export_name=f"prefect-task-role-arn-output-{identifier}",
            value=ecs_task_role.role_arn,
        )

        core.CfnOutput(
            self,
            id=f"prefect-cluster-arn-output-{identifier}",
            export_name=f"prefect-cluster-arn-output-{identifier}",
            value=cluster.cluster_arn,
        )

        core.CfnOutput(
            self,
            id=f"prefect-storage-bucket-name-output-{identifier}",
            export_name=f"prefect-storage-bucket-name-output-{identifier}",
            value=bucket.bucket_name,
        )

        core.CfnOutput(
            self,
            id=f"prefect-cache-bucket-name-output-{identifier}",
            export_name=f"prefect-cache-bucket-name-output-{identifier}",
            value=cache_bucket.bucket_name,
        )

        core.CfnOutput(
            self,
            id=f"prefect-task-execution-role-{identifier}",
            export_name=f"prefect-task-execution-role-{identifier}",
            value=ecs_task_execution_role.role_arn,
        )

        core.CfnOutput(
            self,
            id=f"prefect-security-group-output-{identifier}",
            export_name=f"prefect-security-group-output-{identifier}",
            value=security_group.security_group_id,
        )

        core.CfnOutput(
            self,
            id=f"prefect-vpc-output-{identifier}",
            export_name=f"prefect-vpc-output-{identifier}",
            value=vpc.vpc_id,
        )
