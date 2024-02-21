import pulumi
from pulumi_aws import *
from pulumi import automation as auto

def pulumi_program():
        s3.Bucket("my-bucket-dshbfkjawhbdhks")

stack = auto.create_or_select_stack(
        stack_name="my_stack",
        project_name="project",
        program=pulumi_program)

    # Set the AWS region.
stack.workspace.install_plugin("aws", "v4.0.0")

stack.set_config("aws:region", auto.ConfigValue(value="us-west-2"))


up_res = stack.up(on_output=print)

stack.destroy(on_output=print)
