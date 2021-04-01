import json
import os

import prefect
from prefect import Flow, storage, task
from prefect.run_configs import ECSRun
import yaml
from prefect.engine.executors import DaskExecutor
from flow_test.utils import retrieve_stack_outputs

project = os.environ["PREFECT_PROJECT"]
worker_image = os.environ["PREFECT_DASK_WORKER_IMAGE"]

definition = yaml.safe_load(
    """
    networkMode: awsvpc
    cpu: 1024
    memory: 2048
    containerDefinitions:
        - name: flow
    """
)

outputs = retrieve_stack_outputs()

definition["executionRoleArn"] = outputs["task_execution_role"]

executor = DaskExecutor(
    cluster_class="dask_cloudprovider.aws.FargateCluster",
    cluster_kwargs={
        "image": worker_image,
        "vpc": outputs["vpc_output"],
        "cluster_arn": outputs["cluster_arn_output"],
        "task_role_arn": outputs["task_role_arn_output"],
        "execution_role_arn": outputs["task_execution_role"],
        "security_groups": [
            outputs["security_group_output"]
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
        bucket=outputs["storage_bucket_name_output"]
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
