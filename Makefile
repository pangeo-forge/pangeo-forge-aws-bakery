.PHONEY: install lint format diff deploy destroy

install:
	npm install
	poetry install
	poetry run pre-commit install

lint:
	poetry run pre-commit run --all-files

format:
	poetry run isort --profile black cdk/ flow_test/
	poetry run black cdk/ flow_test/ --line-length 100

diff:
	poetry run dotenv run npx cdk diff --app cdk/app.py || true

deploy:
	poetry run dotenv run npx cdk deploy --app cdk/app.py --require-approval never

destroy:
	poetry run dotenv run npx cdk destroy --app cdk/app.py --force
