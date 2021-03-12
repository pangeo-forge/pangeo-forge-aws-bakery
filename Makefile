.PHONEY: install install-dev lint format diff deploy destroy

install:
	npm install
	pipenv install

install-dev:
	npm install
	pipenv install --dev

lint:
	pipenv run flake8 cdk/
	pipenv run isort --check-only --profile black cdk/
	pipenv run black --check --diff cdk/

format:
	pipenv run isort --profile black cdk/
	pipenv run black cdk/

diff:
	pipenv run npx cdk diff --app cdk/app.py || true

deploy:
	pipenv run npx cdk deploy --app cdk/app.py --require-approval never

destroy:
	pipenv run npx cdk destroy --app cdk/app.py --force
