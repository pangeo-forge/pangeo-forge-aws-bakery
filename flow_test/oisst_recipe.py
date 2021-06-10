import json
import logging
import os
from functools import wraps

import pandas as pd
import yaml
from pangeo_forge_recipes.patterns import pattern_from_file_sequence
from pangeo_forge_recipes.recipes import XarrayZarrRecipe
from pangeo_forge_recipes.recipes.base import BaseRecipe
from pangeo_forge_recipes.storage import CacheFSSpecTarget, FSSpecTarget
from prefect import storage
from prefect.executors.dask import DaskExecutor
from prefect.run_configs.ecs import ECSRun
from rechunker.executors import PrefectPipelineExecutor
from s3fs import S3FileSystem

from flow_test.utils import generate_tags, retrieve_stack_outputs


def set_log_level(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.basicConfig()
        logging.getLogger("pangeo_forge.recipes.xarray_zarr").setLevel(level=logging.DEBUG)
        result = func(*args, **kwargs)
        return result

    return wrapper


def register_recipe(recipe: BaseRecipe):
    flow_name = "test-noaa-flow"
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

    fs_remote = S3FileSystem()
    target = FSSpecTarget(
        fs_remote,
        root_path=f"s3://{outputs['cache_bucket_name_output']}/target/oisst/",
    )
    recipe.target = target
    recipe.input_cache = CacheFSSpecTarget(
        fs_remote,
        root_path=(f"s3://{outputs['cache_bucket_name_output']}/cache/oisst/"),
    )
    recipe.metadata_cache = target

    executor = PrefectPipelineExecutor()
    pipeline = recipe.to_pipelines()
    flow = executor.pipelines_to_plan(pipeline)

    flow.storage = storage.S3(bucket=outputs["storage_bucket_name_output"])
    flow.run_config = ECSRun(
        image=os.environ["BAKERY_IMAGE"],
        labels=json.loads(os.environ["PREFECT_AGENT_LABELS"]),
        task_definition=definition,
        run_task_kwargs={"tags": tags["tag_list"]},
    )
    flow.executor = DaskExecutor(
        cluster_class="dask_cloudprovider.aws.FargateCluster",
        cluster_kwargs={
            "image": os.environ["BAKERY_IMAGE"],
            "vpc": outputs["vpc_output"],
            "cluster_arn": outputs["cluster_arn_output"],
            "task_role_arn": outputs["task_role_arn_output"],
            "execution_role_arn": outputs["task_execution_role_arn_output"],
            "security_groups": [outputs["security_group_output"]],
            "scheduler_cpu": 256,
            "scheduler_mem": 512,
            "worker_cpu": 1024,
            "worker_mem": 2048,
            "scheduler_timeout": "15 minutes",
            "tags": tags["tag_dict"],
        },
        adapt_kwargs={"maximum": 10},
    )

    for flow_task in flow.tasks:
        flow_task.run = set_log_level(flow_task.run)

    flow.name = flow_name
    project_name = os.environ["PREFECT_PROJECT"]
    flow.register(project_name=project_name)


if __name__ == "__main__":
    input_url_pattern = (
        "https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation"
        "/v2.1/access/avhrr/{yyyymm}/oisst-avhrr-v02r01.{yyyymmdd}.nc"
    )
    dates = pd.date_range("2019-09-01", "2021-01-05", freq="D")
    input_urls = [
        input_url_pattern.format(yyyymm=day.strftime("%Y%m"), yyyymmdd=day.strftime("%Y%m%d"))
        for day in dates
    ]
    pattern = pattern_from_file_sequence(input_urls, "time", nitems_per_file=1)

    recipe = XarrayZarrRecipe(pattern, inputs_per_chunk=20)
    register_recipe(recipe)
