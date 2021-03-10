#!/usr/bin/env python3
import os

from aws_cdk import core
from bakery_stack import BakeryStack

app = core.App()

identifier = os.environ["IDENTIFIER"]

BakeryStack(
    scope=app,
    construct_id=f"pangeo-forge-aws-bakery-{identifier}",
    identifier=identifier,
)

for k, v in {
    "Project": "pangeo-forge-aws-bakery",
    "Stack": identifier,
    "Client": "pangeo-forge",
    "Owner": os.environ["OWNER"],
}.items():
    core.Tags.of(app).add(k, v, apply_to_launched_instances=True)

app.synth()
