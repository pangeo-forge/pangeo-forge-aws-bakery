import json
import os

import prefect
from prefect import Flow, storage, task
from prefect.run_configs import ECSRun
import yaml
import boto3

identifier = os.environ["IDENTIFIER"]
project = os.environ["PREFECT_PROJECT"]
cloudformation = boto3.resource('cloudformation')
stack = cloudformation.Stack(f"pangeo-forge-aws-bakery-{identifier}")
execution_role_output = next((output for output in stack.outputs 
    if output["ExportName"] == f"prefect-task-execution-role-{identifier}"), None)
print(execution_role_output)

definition = yaml.safe_load(
    """
    networkMode: awsvpc
    cpu: 1024
    memory: 2048
    containerDefinitions:
        - name: flow
    """
)
definition["executionRoleArn"] = execution_role_output["OutputValue"]


@task
def say_hello():
    logger = prefect.context.get("logger")
    logger.info("Hello, Cloud")
    return "hello result"


with Flow(
    "hello-flow",
    storage=storage.S3(
        bucket=os.environ["PREFECT_FLOW_STORAGE_BUCKET"],
    ),

    run_config=ECSRun(
        image=os.environ["PREFECT_DASK_WORKER_IMAGE"],
        labels=json.loads(os.environ["PREFECT_FLOW_LABELS"]),
        task_definition=definition,
    )
) as flow:
    hello_result = say_hello()

flow.register(project_name=project)