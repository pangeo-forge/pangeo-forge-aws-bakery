.PHONY: install
install:
	npm install
	poetry install
	poetry run pre-commit install

.PHONY: lint
lint:
	poetry run pre-commit run --all-files

.PHONY: format
format:
	poetry run isort --profile black cdk/ flow_test/
	poetry run black cdk/ flow_test/ --line-length 100

.PHONY: diff
diff:
	poetry run dotenv run npx cdk diff --app cdk/app.py || true

.PHONY: deploy
deploy:
	poetry run dotenv run npx cdk deploy --app cdk/app.py --require-approval never

.PHONY: destroy
destroy:
	poetry run dotenv run npx cdk destroy --app cdk/app.py --force

.PHONY: register-flow
register-flow:
	poetry run dotenv run sh -c 'docker run -it --rm \
	-v $$(pwd)/flow_test:/flow_test \
	-v ~/.aws/:/home/jovyan/.aws:ro \
	-e IDENTIFIER -e BAKERY_IMAGE -e PREFECT__CLOUD__AGENT__LABELS -e PREFECT_PROJECT -e PREFECT__CLOUD__AUTH_TOKEN \
	-e AWS_DEFAULT_PROFILE -e AWS_DEFAULT_REGION \
    $$BAKERY_IMAGE python3 /flow_test/$(flow)'
