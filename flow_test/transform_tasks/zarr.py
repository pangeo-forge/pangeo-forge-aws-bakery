from typing import List, Optional

import fsspec
import zarr
from prefect import task


@task
def consolidate_metadata(target, writes: Optional[List[str]] = None) -> None:
    mapper = fsspec.get_mapper(target)
    zarr.consolidate_metadata(mapper)
