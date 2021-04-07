import os

import fsspec
from prefect import task


@task
def download(source_url, cache_location):
    target_url = os.path.join(cache_location, str(hash(source_url)))

    try:
        fsspec.open(target_url).open()
        return target_url
    except FileNotFoundError:
        pass

    with fsspec.open(source_url, mode="rb") as source:
        with fsspec.open(target_url, mode="wb") as target:
            target.write(source.read())
    return target_url
