# pangeo-forge AWS Bakery ☁️🍞

This repository serves as the provider of an AWS CDK Application which deploys the necessary infrastructure to provide a `pangeo-forge` Bakery on AWS

# Contents

* [🧑‍💻 Development - Requirements](#requirements)
* [🧑‍💻 Development - Getting Started](#getting-started-🏃‍♀️)
* [🧑‍💻 Development - Makefile goodness](#makefile-goodness)
* [🚀 Deployment - Prerequisites](#prerequisites)
* [🚀 Deployment - Deploying](#deploying)
* [🚀 Deployment - Destroying](#destroying)
* [📊 Flows - Registering the test Recipe](#registering-the-test-recipe)

# Development

## Requirements

To develop on this project, you should have the following installed:

* [Node 14](https://nodejs.org/en/) (We recommend using NVM [Node Version Manager](https://github.com/nvm-sh/nvm))
* [AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html) - There is a `package.json` in the repository, it's recommended to run `npm install` in the repository root and make use of `npx <command>` rather than globally installing AWS CDK
* [Python 3.8.10](https://www.python.org/downloads/) (We recommend using [Pyenv](https://github.com/pyenv/pyenv) to handle Python versions)
* [Poetry](https://github.com/python-poetry/poetry)
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html)
* [Docker](https://docs.docker.com/get-docker/)

If you're developing on MacOS, all of the above (apart from AWS CDK) can be installed using [homebrew](https://brew.sh/)

If you're developing on Windows, we'd recommend using either [Git BASH](https://gitforwindows.org/) or [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10)

## Getting started 🏃‍♀️

_**NOTE:** All `make` commands should be run from the **root** of the repository_

### Installing dependencies

This project requires some Python and Node dependencies (Including `cdk`, `prefect`, and `python-dotenv`), these are so that:

* We can deploy the Bakery AWS infrastructure
* We can register flows for testing
* We can use `.env` files to provide both Prefect Flows and CDK with environment variables

To install the dependencies, run:

```bash
$ make install # Runs `npm install` to install CDK and `poetry install` to install all the Python dependencies required
```

### `.env` file

A file named `.env` is expected in the root of the repository to store variables used within deployment, the expected values are:

```bash
# SET BY YOU MANUALLY:

OWNER="<your-name>"
IDENTIFIER="<a-unique-value-to-tie-to-your-deployment>"
AWS_DEFAULT_REGION="<your-preferred-aws-region>"
AWS_DEFAULT_PROFILE="<your-preferred-named-aws-cli-profile>"
RUNNER_TOKEN_SECRET_ARN="<arn-of-your-runner-token-secret>" # See [Deployment - Prerequisites > Prerequisites > cloud.prefect.io Runner Token]
PREFECT__CLOUD__AUTH_TOKEN="<value-of-tenant-token>" # See https://docs.prefect.io/orchestration/concepts/tokens.html#tenant - This is used to support flow registration
PREFECT_PROJECT="<name-of-a-prefect-project>" # See https://docs.prefect.io/orchestration/concepts/projects.html#creating-a-project - This is where the bakery's test flows will be registered
PREFECT__CLOUD__AGENT__LABELS="<a-set-of-prefect-agent-labels>" # See https://docs.prefect.io/orchestration/agents/overview.html#labels - These will be registered with the deployed agent to limit which flows should be executed by the agent
BUCKET_USER_ARN="<arn-of-your-bucket-iam-user>" # See [Deployment > Prerequisites > Bucket IAM User]
BAKERY_IMAGE="<pangeo-forge-bakery-images-image-you-wish-to-use>" # See [Deployment > Prerequisites > Bakery Image]
```

An example called `example.env` is available for you to copy, rename, and fill out accordingly.

## Makefile goodness

A `Makefile` is available in the root of the repository to abstract away commonly used commands for development:

**`make install`**

> This will run `npm install` and `pipenv install` on the repo root, installing the dependencies needed for development of this project

**`make lint`**

> This will perform a dry run of `flake8`, `isort`, and `black` and let you know what issues were found

**`make format`**

> This will peform a run of `isort` and `black`, this **will** modify files if issues were found

**`make diff`**

> This will run a `cdk diff` using the contents of your `.env` file

**`make deploy`**

> This will run a `cdk deploy` using the contents of your `.env` file. The deployment is auto-approved, so **make sure** you know what you're changing with your deployment first! (Best to run `make diff` to check!)

**`make destroy`**

> This will run a `cdk destroy` using the contents of your `.env` file. The destroy is auto-approved, so **make sure** you know what you're destroying first!

**`make register-flow`**

> This uses the bakery image defined in `BAKERY_IMAGE` to register your Flow with Prefect. It takes a parameter `flow` which is the Python file within `flow_test/` you'd like to use. You would use it like: `$ make register-flow flow=oisst_recipe.py`

# Deployment

## Prerequisites

Firstly, ensure you've installed all the project requirements as described [here](#requirements) and [here](#getting-started-🏃‍♀️).

### cloud.prefect.io Runner Token

To successfully communicate with Prefect Cloud, the ECS Agent we deploy needs access to a `RUNNER` token [outlined here](https://docs.prefect.io/orchestration/agents/overview.html#tokens).

You should create a Secret in AWS Secrets Manager (in your deployment region) in the form:

```
{
    "RUNNER_TOKEN": "<The value of the token>"
}
```

Take a note of the ARN for the token and put it in your `.env` file under the key of `RUNNER_TOKEN_SECRET_ARN`.

### Bucket IAM User

To be able to utilise S3 Flow Storage, a IAM User must be created in the AWS Account the Bakery is being deployed into.

This user needs no permissions applied to them, these are applied on Bakery deployment.

You can follow the instructions [here](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html) to create the IAM User, once this is done, place the value of the IAM Users ARN into `.env` under `BUCKET_USER_ARN`.

This value is provided to `bakeries.yaml` so that Flows may be registered to your Bakery.

### Bakery Image

To be able to register and run Recipes as Prefect Flows, your Bakery must be running one of the `pangeo-forge-bakery-images` images in both your Prefect Agent **and** your Flow & Dask tasks.

You can find more information on the `pangeo-forge-bakery-images` [here](https://github.com/pangeo-forge/pangeo-forge-bakery-images). Once you've selected which tag you wish to support, you need to add an entry into `.env` under the name `BAKERY_IMAGE`. See below for an example:

```bash
BAKERY_IMAGE="pangeo/pangeo-forge-bakery-images:pangeonotebook-2021.05.15_prefect-0.14.19_pangeoforgerecipes-0.3.4"
```

## Deploying

You can check _what_ you'll be deploying by running:

```bash
$ make diff # Outputs the result of `cdk diff`
```

To deploy the AWS infrastructure required to host your Bakery, you can run:

```bash
$ make deploy # Deploys Bakery AWS infrastructure
```

## Destroying

To destroy the Bakery infrastructure within AWS, you can run:

```bash
$ make destroy # Destroys the Bakery infrastructure
```

# Flows

## Registering the test Recipe

For quick testing of your Bakery deployment, there is a Recipe setup as a Flow within `flow_test/` that you can register and run. Before you register the example Flow, you must have the values of `PREFECT__CLOUD__AUTH_TOKEN`, `PREFECT_PROJECT`, `PREFECT__CLOUD__AGENT__LABELS`, `BAKERY_IMAGE`, `IDENTIFIER`, `AWS_DEFAULT_PROFILE`, and `AWS_DEFAULT_REGION` present and populated in `.env`. You must also have run [`make install`](#makefile-goodness).

When your `.env` is populated and you've installed the project dependencies, you can register the Flow by running:

```bash
$ make register-flow flow=<name-of-flow-file-in-flow_test/>.py

[2021-06-11 12:30:03+0100] INFO - prefect.S3 | Uploading test-noaa-flow/2021-06-11t11-30-03-443149-00-00 to <storage-bucket>
Flow URL: https://cloud.prefect.io/<your-account>/flow/1429ce74-1be7-412f-bc03-2553d79d7752
 └── ID: c8de9a87-a534-4b86-a5cc-b02dc61e58bc
 └── Project: <PREFECT_PROJECT>
 └── Labels: <PREFECT__CLOUD__AGENT__LABELS>
```

You can then navigate to [cloud.prefect.io](https://cloud.prefect.io/), find your Flow, and run it.
