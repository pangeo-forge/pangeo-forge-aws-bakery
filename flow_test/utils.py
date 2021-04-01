import os
import boto3

identifier = os.environ["IDENTIFIER"]
cloudformation = boto3.resource('cloudformation')
stack = cloudformation.Stack(f"pangeo-forge-aws-bakery-{identifier}")


def retrieve_stack_outputs():
    outputs = {
        "_".join(output.get("ExportName").replace(identifier, "").split("-")[1:-1])
        if output.get("ExportName") else None: output.get("OutputValue")
        for output in stack.outputs
    }
    return outputs
