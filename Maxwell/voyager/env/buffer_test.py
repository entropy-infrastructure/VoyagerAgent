


from buffer import Deployer


def test_full_code():
    buf = Deployer("my_stack","pulumi_program","""def pulumi_program():
        s3.Bucket("my-bucket-dshbfkjawhbdhks")""")
    assert buf.write_file() == """import pulumi
from pulumi_aws import *
from pulumi import automation as auto

def pulumi_program():
        s3.Bucket("my-bucket-dshbfkjawhbdhks")

stack = auto.create_or_select_stack(
        stack_name="my_stack",
        project_name="project")

    # Set the AWS region.
stack.set_config("aws:region", auto.ConfigValue(value="us-west-2"))
stack.set_program(pulumi_program)

up_res = stack.up(on_output=print)
"""



