.PHONEY: install install-dev lint format diff deploy destroy

install:
	npm install
	pipenv install

install-dev:
	npm install
	pipenv install --dev
	pipenv run pip install botocore==1.19.52
	pipenv run pip install dask-cloudprovider[aws]==2021.3.1
	pipenv run pip install boto3==1.16.52
	pipenv run pip install xarray
	pipenv run pip install zarr
	pipenv run pip install git+https://github.com/pangeo-forge/pangeo-forge

lint:
	pipenv run flake8 cdk/ test/
	pipenv run isort --check-only --profile black cdk/ test/
	pipenv run black --check --diff cdk/ test/

format:
	pipenv run isort --profile black cdk/ test/
	pipenv run black cdk/ test/

diff:
	pipenv run npx cdk diff --app cdk/app.py || true

deploy:
	pipenv run npx cdk deploy --app cdk/app.py --require-approval never

destroy:
	pipenv run npx cdk destroy --app cdk/app.py --force
