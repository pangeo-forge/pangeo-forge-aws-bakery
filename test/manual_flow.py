import json
import os

import prefect
from prefect import Flow, storage, task
from prefect.run_configs import ECSRun


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
    )
) as flow:
    hello_result = say_hello()
