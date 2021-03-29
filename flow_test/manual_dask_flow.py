import json
import os

import prefect
from prefect import Flow, storage, task
from prefect.run_configs import ECSRun
import yaml
import boto3
from prefect.engine.executors import DaskExecutor
import pandas as pd

identifier = os.environ["IDENTIFIER"]
project = os.environ["PREFECT_PROJECT"]
worker_image = os.environ["PREFECT_DASK_WORKER_IMAGE"]
storage_bucket = os.environ["PREFECT_FLOW_STORAGE_BUCKET"]

cloudformation = boto3.resource('cloudformation')
stack = cloudformation.Stack(f"pangeo-forge-aws-bakery-{identifier}")

execution_role_output = next((output for output in stack.outputs 
    if output["ExportName"] == f"prefect-task-execution-role-{identifier}"),
        None)["OutputValue"]

task_role_output = next((output for output in stack.outputs 
    if output["ExportName"] == f"prefect-task-role-arn-output-{identifier}"),
        None)["OutputValue"]

cluster_output = next((output for output in stack.outputs 
    if output["ExportName"] == f"prefect-cluster-arn-output-{identifier}"),
        None)["OutputValue"]

security_group_output = next((output for output in stack.outputs 
    if output["ExportName"] == f"prefect-security-group-output-{identifier}"),
        None)["OutputValue"]

vpc_output = next((output for output in stack.outputs 
    if output["ExportName"] == f"prefect-vpc-output-{identifier}"),
        None)["OutputValue"]


definition = yaml.safe_load(
    """
    networkMode: awsvpc
    cpu: 1024
    memory: 2048
    containerDefinitions:
        - name: flow
    """
)
definition["executionRoleArn"] = execution_role_output

executor = DaskExecutor(
    cluster_class="dask_cloudprovider.aws.FargateCluster",
    cluster_kwargs={
        "image": "552819999234.dkr.ecr.us-west-2.amazonaws.com/pangeo-forge-aws-bakery-worker",
        "vpc": vpc_output,
        "cluster_arn": cluster_output,
        "task_role_arn": task_role_output,
        "execution_role_arn": execution_role_output,
        "security_groups": [
            security_group_output
        ],
        "n_workers": 1,
        "scheduler_cpu": 256,
        "scheduler_mem": 512,
        "worker_cpu": 1024,
        "worker_mem": 2048,
        "scheduler_timeout": "15 minutes",
    },
)
@task
def say_hello():
    logger = prefect.context.get("logger")
    logger.info("Hello, Cloud")
    return "hello result"


with Flow(
    "dask-test-flow",
    storage=storage.S3(
        bucket=storage_bucket
    ),
    run_config=ECSRun(
        image=worker_image,
        labels=json.loads(os.environ["PREFECT_AGENT_LABELS"]),
        task_definition=definition,
    ),
    executor=executor,
) as flow:
    hello_result = say_hello()

flow.register(project_name=project)
