FROM pangeo/pangeo-notebook:latest
RUN conda run -n notebook pip install -I git+https://github.com/pangeo-forge/pangeo-forge@master
RUN conda run -n notebook pip uninstall -y xarray
RUN conda run -n notebook pip install -I git+https://github.com/pydata/xarray@master
RUN conda run -n notebook pip install -I dask-cloudprovider==2021.3.1
RUN conda run -n notebook pip uninstall -y prefect
RUN conda run -n notebook pip install -I prefect[aws]==0.14.13
