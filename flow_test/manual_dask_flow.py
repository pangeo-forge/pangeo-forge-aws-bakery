import json
import os

import prefect
import yaml
from prefect import Flow, storage, task
from prefect.engine.executors import DaskExecutor
from prefect.run_configs import ECSRun

from flow_test.utils import generate_tags, retrieve_stack_outputs

project = os.environ["PREFECT_PROJECT"]
worker_image = os.environ["PREFECT_DASK_WORKER_IMAGE"]
flow_name = "dask-test-flow"

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
tags = generate_tags(flow_name)


definition["executionRoleArn"] = outputs["task_execution_role"]

executor = DaskExecutor(
    cluster_class="dask_cloudprovider.aws.FargateCluster",
    cluster_kwargs={
        "image": worker_image,
        "vpc": outputs["vpc_output"],
        "cluster_arn": outputs["cluster_arn_output"],
        "task_role_arn": outputs["task_role_arn_output"],
        "execution_role_arn": outputs["task_execution_role"],
        "security_groups": [outputs["security_group_output"]],
        "n_workers": 1,
        "scheduler_cpu": 256,
        "scheduler_mem": 512,
        "worker_cpu": 1024,
        "worker_mem": 2048,
        "scheduler_timeout": "15 minutes",
        "tags": tags["tag_dict"],
    },
)


@task
def say_hello():
    logger = prefect.context.get("logger")
    logger.info("Hello, Cloud")
    return "hello result"


with Flow(
    flow_name,
    storage=storage.S3(bucket=outputs["storage_bucket_name_output"]),
    run_config=ECSRun(
        image=worker_image,
        labels=json.loads(os.environ["PREFECT_AGENT_LABELS"]),
        task_definition=definition,
        run_task_kwargs={"tags": tags["tag_list"]},
    ),
    executor=executor,
) as flow:
    hello_result = say_hello()

flow.register(project_name=project)
