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


def generate_tags(flow_name):
    tags = stack.tags
    tags.append({
        "Key": "Flow",
        "Value": flow_name
    })
    lowercase_tags = [
        {k.lower(): v for k, v in tag.items()}
        for tag in tags
    ]
    tag_dict = {
        tag.get("Key"): tag.get("Value")
        for tag in tags
    }
    return {
        "tag_list": lowercase_tags,
        "tag_dict": tag_dict
    }
