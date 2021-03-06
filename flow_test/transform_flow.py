import json
import os

import pandas as pd
import yaml
from prefect import Flow, Parameter, storage, task, unmapped
from prefect.executors import DaskExecutor
from prefect.run_configs import ECSRun

from flow_test.transform_tasks.http import download
from flow_test.transform_tasks.xarray import chunk, combine_and_write
from flow_test.transform_tasks.zarr import consolidate_metadata
from flow_test.utils import generate_tags, retrieve_stack_outputs

project = os.environ["PREFECT_PROJECT"]
worker_image = os.environ["PREFECT_DASK_WORKER_IMAGE"]
flow_name = "dask-transform-flow"

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

definition["executionRoleArn"] = outputs["task_execution_role_arn_output"]

executor = DaskExecutor(
    cluster_class="dask_cloudprovider.aws.FargateCluster",
    cluster_kwargs={
        "image": worker_image,
        "vpc": outputs["vpc_output"],
        "cluster_arn": outputs["cluster_arn_output"],
        "task_role_arn": outputs["task_role_arn_output"],
        "execution_role_arn": outputs["task_execution_role_arn_output"],
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
def source_url(day: str) -> str:
    day = pd.Timestamp(day)
    source_url_pattern = (
        "https://www.ncei.noaa.gov/data/"
        "sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/"
        "{day:%Y%m}/oisst-avhrr-v02r01.{day:%Y%m%d}.nc"
    )
    return source_url_pattern.format(day=day)


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
    days = Parameter(
        "days",
        default=pd.date_range("1981-09-01", "1981-09-10", freq="D").strftime("%Y-%m-%d").tolist(),
    )
    sources = source_url.map(days)
    zarr_output = "dask_transform_flow.zarr"
    nc_sources = download.map(
        sources,
        cache_location=unmapped(f"s3://{outputs['cache_bucket_name_output']}/cache/{zarr_output}"),
    )
    chunked = chunk(nc_sources, size=5)
    target = f"s3://{outputs['cache_bucket_name_output']}/target/{zarr_output}"
    writes = combine_and_write.map(
        chunked,
        unmapped(target),
        append_dim=unmapped("time"),
        concat_dim=unmapped("time"),
    )

    consolidate_metadata(target, writes=writes)

flow.register(project_name=project)
