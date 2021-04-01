import json
import os

import prefect
from prefect import Flow, storage, task
from prefect.run_configs import ECSRun
import yaml
from flow_test.utils import retrieve_stack_outputs, generate_tags

project = os.environ["PREFECT_PROJECT"]
outputs = retrieve_stack_outputs()
flow_name = "hello-flow"

definition = yaml.safe_load(
    """
    networkMode: awsvpc
    cpu: 1024
    memory: 2048
    containerDefinitions:
        - name: flow
    """
)

tags = generate_tags(flow_name)
definition["executionRoleArn"] = outputs["task_execution_role"]


@task
def say_hello():
    logger = prefect.context.get("logger")
    logger.info("Hello, Cloud")
    return "hello result"


with Flow(
    flow_name,
    storage=storage.S3(
        bucket=outputs["storage_bucket_name_output"]
    ),

    run_config=ECSRun(
        image=os.environ["PREFECT_DASK_WORKER_IMAGE"],
        labels=json.loads(os.environ["PREFECT_AGENT_LABELS"]),
        task_definition=definition,
        run_task_kwargs={"tags": tags["tag_list"]},
    )
) as flow:
    hello_result = say_hello()

flow.register(project_name=project)
