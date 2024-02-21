
import ast
import os
import re
import plumbum
from voyager.env.buffer import CombinedStack, PulumiStack
from voyager.env.buffer import AnsibleStack
from voyager.env.buffer import execute_command

def extract_functions(code):
    # Pattern to find functions
    pattern = r"(def .*?\(.*?\):(?:\n|\r\n)(?:[^\S\n]*.*(?:\n|\r\n))*)"
    # Find all functions
    functions = re.findall(pattern, code, re.DOTALL)

    function_dict = {}
    for func in functions:
        # Extract function name
        func_name = re.search(r"def (.*?\(.*?\)):", func).group(1)
        function_dict[func_name] = func

    return function_dict


# # Extract pulumi function and ansible function
# pulumi_func = [func for name, func in functions.items() if 'pulumi' in func]
# ansible_func = [func for name, func in functions.items() if 'ansible' in func]

# print("Pulumi Function Name:", [name for name in functions if 'pulumi' in functions[name]])
# print("Ansible Function Name:", [name for name in functions if 'ansible' in functions[name]])


def extract_functions(input_string):
    # Test the code with the given string
# input_string = """
# Explain: There are no steps missing in your plan. The code is not completing the task because there is no code provided yet.

# Plan:
# 1) Write a pulumi function that creates an EC2 instance with the necessary security group and ingress rules to allow HTTP traffic.
# 2) Export the necessary variables from the pulumi function.
# 3) Write an ansible function that takes the exported variables from the pulumi function and uses the Ansible API to install Apache on the EC2 instance.

# Code:
# ```python
# import pulumi
# import pulumi_aws as aws
# from ansible_builder import AnsibleInventoryBuilder, AnsibleTaskBuilder

# # Pulumi function to create EC2 instance
# def create_ec2_instance():
#     # Create a new Key for EC2 instance
#     with open("testkey.pub", "r") as file:
#         key_data = file.read()

#     # Create a Key Pair
#     key_pair = aws.ec2.KeyPair('keyPair',
#         key_name='my-KeyPair',
#         public_key=key_data)

#     # Get the latest Ubuntu AMI
#     ami = pulumi.Output.all(
#         aws.ec2.get_ami(most_recent="true", owners=["099720109477"], filters=[{"name": "name", "values": ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"],}]),
#     )

#     # Create a new Security Group that allows SSH and HTTP access
#     group = aws.ec2.SecurityGroup("web-secgrp", egress=[
#         {"protocol": "-1", "from_port": 0, "_port": 0, "cidr_blocks": ["0.0.0.0/0"],}],
#         ingress=[
#             {"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"],},
#             {"protocol": "tcp", "from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"],}],
#     )

#     # Create a new EC2 instance
#     server = aws.ec2.Instance("web-server-www",
#         instance_type="t2.micro",
#         vpc_security_group_ids=[group.id],
#         ami=ami,
#         key_name=key_pair.key_name,
#         tags={
#             "Name": "web-server",
#         },
#     )

#     pulumi.export("publicIp", server.public_ip)

# # Ansible function to install Apache
# def install_apache(output):
#     inventory = AnsibleInventoryBuilder()
#     inventory.add_host("my_host", output["publicIp"], "testkey", group="my_group")
#     inventory.add_group("my_group")
#     tasks = AnsibleTaskBuilder()
#     tasks.add_task("install apache", "apt", args={"name": "apache2", "state": "present"})
#     tasks.add_task("start apache", "service", args={"name": "apache2", "state": "started"})
#     tasks.add_task("enable apache", "service", args={"name": "apache2", "enabled": True})
#     tasks.add_task("restart apache", "service", args={"name": "apache2", "state": "restarted"})
#     return {
#         "inventory": inventory,
#         "tasks": tasks
#     }
# ```

# Ansible Function Name: install_apache
# Pulumi Function Name: create_ec2_instanc
# """

    code_match = re.search(r'```python\n(.*?)\n```', input_string, re.DOTALL)

    if code_match:
        code = code_match.group(1)
    else:
        code = "No match found"

    # tree = ast.parse(code)
    # functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]

    # functions_info = [] 
    # for function in functions: 
    #     function_info = { 'name': function.name, 'body': [ast.unparse(node) for node in function.body] } 
    #     functions_info.append(function_info)
    # # print(f"def  {functions_info[0]['name']}:")
    # # print("\n".join(functions_info[0]["body"]))

    # # Match all function definitions in the code using regular expressions
    function_matches = re.findall(r'(def .*?:.*?)(?=def |\Z)', code, re.DOTALL)
    # print(function_matches)
    # # If we found function matches, we extract them, otherwise return an empty list
    functions = function_matches if function_matches else []

    # print(functions[1])

    ansible_function_match = re.search(r'Ansible Function Name: (\w+)', input_string)
    pulumi_function_match = re.search(r'Pulumi Function Name: (\w+)', input_string)
    # print(ansible_function_match, pulumi_function_match)
    # If matches are found, extract them, otherwise assign None
    ansible_function_name = ansible_function_match.group(1) if ansible_function_match else None
    pulumi_function_name = pulumi_function_match.group(1) if pulumi_function_match else None
    # print(ansible_function_name, pulumi_function_name)

    return {
        "ansible_function_name": ansible_function_name,
        "pulumi_function_name": pulumi_function_name,
        "ansible_function_code": functions[1],
        "pulumi_function_code": functions[0]
    }

input_string =  """
Explain: In order to create an Ansible inventory builder for installing Apache, we need to define the necessary resources in Pulumi and then write an Ansible function that uses those resources to configure the Apache installation.

Plan:
1) Write a Pulumi function that creates an EC2 instance and a security group.
2) Export the necessary variables from the Pulumi function to be used in the Ansible function.
3) Write an Ansible function that uses the exported variables to configure the Apache installation.

Code:
```python
import pulumi
import pulumi_aws as aws
from ansible_builder import AnsibleInventoryBuilder, AnsibleTaskBuilder

# Pulumi function to create EC2 instance and security group
def create_ec2_instance():
    # Create a new Security Group that allows SSH, HTTP, and HTTPS access
    group = aws.ec2.SecurityGroup("web-secgrp",
        egress=[
            {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]},
        ],
        ingress=[
            {"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]},
            {"protocol": "tcp", "from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"]},
            {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]},
        ],
    )

    # Create a new EC2 instance
    server = aws.ec2.Instance("web-server-www",
        instance_type="t2.micro",
        vpc_security_group_ids=[group.id],
        ami="ami-00fdb2c249fd46083",
        key_name="my-KeyPair",
        tags={
            "Name": "web-server",
        },
    )

    # Export the necessary variables for the Ansible function
    pulumi.export("publicIp", server.public_ip)
    pulumi.export("keyFile", "./testkey")

# Ansible function to configure Apache installation
def configure_apache(state):
    inventory = AnsibleInventoryBuilder()
    inventory.add_host("my_host", state["publicIp"], state["keyFile"], group="my_group")
    inventory.add_group("my_group")
    tasks = AnsibleTaskBuilder()
    tasks.add_task("install apache", "apt", args={"name": "apache2", "state": "present"})
    tasks.add_task("start apache", "service", args={"name": "apache2", "state": "started"})
    tasks.add_task("enable apache", "service", args={"name": "apache2", "enabled": True})
    return {
        "inventory": inventory,
        "tasks": tasks
    }
```

Ansible Function Name: configure_apache
Pulumi Function Name: create_ec2_instance
"""


def write_files(input_string):
    funcs = extract_functions(input_string)

    stack = CombinedStack([PulumiStack(funcs["pulumi_function_name"]+"_stack",funcs["pulumi_function_name"],funcs["pulumi_function_code"])],
                [AnsibleStack(funcs["ansible_function_name"]+"_stack",funcs["ansible_function_name"],funcs["ansible_function_code"])],
                {funcs["ansible_function_name"]:[funcs["pulumi_function_name"]+"_stack"]})
    stack.write_files()
    return funcs
    
def execute():
    
    out = plumbum.local["python3"]("voyager/env/pulumi/combined.py")
    # print(out)
    os.chdir("../..")
    return str(out)


# write_files(input_string)
# execute()