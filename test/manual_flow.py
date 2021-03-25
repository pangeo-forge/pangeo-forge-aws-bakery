import json
import os
from datetime import datetime

import prefect
from prefect import task, Flow, storage
from prefect.engine.results import S3Result
from prefect.run_configs import UniversalRun


@task(
    result=S3Result(
        bucket=os.environ["PREFECT_FLOW_STORAGE_BUCKET"],
        location=f"{datetime.now().strftime('%Y/%m/%d/%H-%M-%S-')}result.txt"
    )
)
def say_hello():
    logger = prefect.context.get("logger")
    logger.info("Hello, Cloud")
    return "hello result"


with Flow(
    "hello-flow",
    storage=storage.S3(
        bucket=os.environ["PREFECT_FLOW_STORAGE_BUCKET"],
    ),
    run_config=UniversalRun(labels=json.loads(os.environ["PREFECT_FLOW_LABELS"]))
) as flow:
    hello_result = say_hello()
