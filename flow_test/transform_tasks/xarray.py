from typing import Any, List, Tuple

import fsspec
import xarray as xr
from pangeo_forge import utils
from prefect import task


@task
def chunk(sources: List[Any], size: int) -> List[Tuple[Any, ...]]:
    return list(utils.chunked_iterable(sources, size))


@task
def combine_and_write(
    sources: List[str], target: str, append_dim: str, concat_dim: str
) -> List[str]:
    double_open_files = [fsspec.open(url).open() for url in sources]
    ds = xr.open_mfdataset(double_open_files, combine="nested", concat_dim=concat_dim)
    ds = ds.chunk({append_dim: len(sources)})
    mapper = fsspec.get_mapper(target)

    if not len(mapper):
        kwargs = dict(mode="w")
    else:
        kwargs = dict(mode="a", append_dim=append_dim)
    ds.to_zarr(mapper, **kwargs)
    return target
