import os
import yaml
import json
import boto3
import pandas as pd
from flow_test.transform_tasks.http import download
from flow_test.transform_tasks.xarray import combine_and_write, chunk
from flow_test.transform_tasks.zarr import consolidate_metadata
from prefect import Flow, Parameter, task, unmapped, storage
from prefect.run_configs import ECSRun
from prefect.engine.executors import DaskExecutor

identifier = os.environ["IDENTIFIER"]
project = os.environ["PREFECT_PROJECT"]
worker_image = os.environ["PREFECT_DASK_WORKER_IMAGE"]
cloudformation = boto3.resource('cloudformation')
stack = cloudformation.Stack(f"pangeo-forge-aws-bakery-{identifier}")
execution_role_output = next((
    output for output in stack.outputs
    if output.get("ExportName") == f"prefect-task-execution-role-{identifier}"),
    None)["OutputValue"]

task_role_output = next((
    output for output in stack.outputs
    if output.get("ExportName") == f"prefect-task-role-arn-output-{identifier}"),
    None)["OutputValue"]

cluster_output = next((
    output for output in stack.outputs
    if output.get("ExportName") == f"prefect-cluster-arn-output-{identifier}"),
    None)["OutputValue"]

security_group_output = next((
    output for output in stack.outputs
    if output.get("ExportName") == f"prefect-security-group-output-{identifier}"),
    None)["OutputValue"]

vpc_output = next((
    output for output in stack.outputs
    if output.get("ExportName") == f"prefect-vpc-output-{identifier}"),
    None)["OutputValue"]

cache_bucket_output = next((
    output for output in stack.outputs
    if output.get("ExportName") == f"prefect-cache-bucket-name-output-{identifier}"),
    None)["OutputValue"]

storage_bucket_output = next((
    output for output in stack.outputs
    if output.get("ExportName") == f"prefect-storage-bucket-name-output-{identifier}"),
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
        "n_workers": 2,
        "scheduler_cpu": 256,
        "scheduler_mem": 512,
        "worker_cpu": 1024,
        "worker_mem": 2048,
        "scheduler_timeout": "15 minutes",
    },
)


@task
def source_url(day: str) -> str:
    """
    Format the URL for a specific day.
    """
    day = pd.Timestamp(day)
    source_url_pattern = (
        "https://www.ncei.noaa.gov/data/"
        "sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/"
        "{day:%Y%m}/oisst-avhrr-v02r01.{day:%Y%m%d}.nc"
    )
    return source_url_pattern.format(day=day)


with Flow(
    "dask-transform-flow",
    storage=storage.S3(
        bucket=storage_bucket_output
    ),
    run_config=ECSRun(
        image=worker_image,
        labels=json.loads(os.environ["PREFECT_AGENT_LABELS"]),
        task_definition=definition,
    ),
    executor=executor,
) as flow:
    days = Parameter(
        # All parameters have a "name" and should have a default value.
        "days",
        default=pd.date_range(
            "1981-09-01",
            "1981-09-10",
            freq="D"
        ).strftime("%Y-%m-%d").tolist(),
    )
    # Use map the `source_url` task to each day. This returns a mapped output,
    # a list of string URLS. See
    # https://docs.prefect.io/core/concepts/mapping.html#prefect-approach
    # for more. We'll have one output URL per day.
    sources = source_url.map(days)
    # Map the `download` task (provided by prefect) to download the raw data
    # into a cache.
    # Mapped outputs (sources) can be fed straight into another Task.map call.
    # If an input is just a regular argument that's not a mapping, it must
    # be wrapepd in `prefect.unmapped`.
    # https://docs.prefect.io/core/concepts/mapping.html#unmapped-inputs
    # nc_sources will be a list of cached URLs, one per input day.
    nc_sources = download.map(
        sources,
        cache_location=unmapped(
            f"s3://{cache_bucket_output}/cache/dask_transform_flow.zarr"
        )
    )
    chunked = chunk(nc_sources, size=5)
    target = f"s3://{cache_bucket_output}/target/dask_transform_flow.zarr"
    writes = combine_and_write.map(
        chunked,
        unmapped(target),
        append_dim=unmapped("time"),
        concat_dim=unmapped("time"),
    )

    # Consolidate the metadata for the final dataset.
    consolidate_metadata(target, writes=writes)

flow.register(project_name=project)
