.PHONEY: install install-dev lint format diff deploy destroy

install:
	npm install
	pipenv install

install-dev:
	npm install
	pipenv install --dev

lint:
	pipenv run flake8 cdk/ flow_test/
	pipenv run isort --check-only --profile black cdk/ flow_test/
	pipenv run black --check --diff cdk/ flow_test/

format:
	pipenv run isort --profile black cdk/ flow_test/
	pipenv run black cdk/ flow_test/

diff:
	pipenv run npx cdk diff --app cdk/app.py || true

deploy:
	pipenv run npx cdk deploy --app cdk/app.py --require-approval never

destroy:
	pipenv run npx cdk destroy --app cdk/app.py --force
