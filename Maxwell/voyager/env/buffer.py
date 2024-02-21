import importlib.util
import os
import time
import plumbum
import yaml
import random
import subprocess
from plumbum import local
def execute_command(command):
    # process = subprocess.Popen(
    #     command,
    #     shell=True,
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.STDOUT,
    #     universal_newlines=True)
    return local[command]()


    # Read and print the output line by line
    # for line in process.stdout:
    #     print(line, end='')  # Print without adding an extra newline
    #     pass
    # Wait for the command to complete
    

    # Return the exit code and the output
    return process.communicate()


class StackStore():

    def __init__(self):
        self.stacks = []

    def add_stack(self,stack):
        self.stacks.append(stack)
    
    def get_stack(self,stack_name):
        for stack in self.stacks:
            if stack.stack_name == stack_name:
                return stack


class PulumiStack():

    def __init__(self,stack_name,func_name,code,path="./voyager/env/pulumi"):
        self.stack_name = stack_name
        self.code = code
        self.func_name = func_name
        self.path = path

    def write_file(self):
        full_code = f"""import pulumi
from pulumi_aws import *
from pulumi import automation as auto

{self.code}

stack = auto.create_or_select_stack(
        {self.stack_name}=\"{self.stack_name}\",
        project_name="project")

    # Set the AWS region.
stack.set_config("aws:region", auto.ConfigValue(value="us-west-2"))
stack.set_program({self.func_name})

up_res = stack.up(on_output=print)
"""



        with open(self.path+f"/{self.stack_name}.py","w") as f:
            f.write(full_code)

        return full_code
    
    def full_code(self):
        return f"""import pulumi
from pulumi_aws import *
from pulumi import automation as auto

{self.code}

{self.stack_name} = auto.create_or_select_stack(
        stack_name=\"{self.stack_name + str(random.randint(0,1000))}\",
        project_name="project",
        program={self.func_name})

    # Set the AWS region.
{self.stack_name}.set_config("aws:region", auto.ConfigValue(value="us-west-2"))

up_res = {self.stack_name}.up(on_output=print)
state_dict["{self.stack_name}"] = {self.stack_name}.outputs()
"""
    
    def deploy(self):
        with open(self.path+f"/{self.stack_name}.py","r") as f:
            code = f.read()
        exec(code)

    def destroy(self):
        module = importlib.import_module(self.path+f"/{self.stack_name}.py") 
        stack = getattr(module, self.stack_name)
        stack.destroy(on_output=print)


class AnsibleInventoryBuilder:
    def __init__(self):
        self.inventory = {}

    def add_host(self, host_name, ip_address,key_file, host_vars=None, group=None):
        if group not in self.inventory:
            self.inventory[group] = {'hosts': {}}
        self.inventory[group]['hosts'][host_name] = {
            "ansible_host": f"ubuntu@{ip_address.__str__()[1:-1]}",
            "ansible_ssh_private_key_file": key_file.__str__(),
            **(host_vars or {})
        }
    
    def write_file(self):
        if os.getcwd().endswith("voyager/env"):
            os.chdir("../..")

        if not os.path.exists("./voyager/env/ansible"):
            print(os.path.abspath("./voyager/env/ansible"))
            os.mkdir("./voyager/env/ansible")
        with open("./voyager/env/ansible/inventory.yml","w") as f:
            f.write(yaml.dump(self.inventory))

    def add_group(self, group_name, group_vars=None):
        if group_name not in self.inventory:
            self.inventory[group_name] = {'hosts': {}, 'vars': group_vars}

    def to_dict(self):
        return self.inventory
    
    def to_yaml(self):
        return yaml.dump(self.inventory)
    
class AnsibleTaskBuilder:
    def __init__(self):
        self.tasks = []

    def add_task(self, name, module, args=None, delegate_to=None, when=None):
        task = {'name': name}
        if args:
            task[module] = args
        if delegate_to:
            task['delegate_to'] = delegate_to
        if when:
            task['when'] = when
        self.tasks.append(task)

    def write_file(self):
        if not os.path.exists("./voyager/env/ansible"):
            os.mkdir("./voyager/env/ansible")
        with open("./voyager/env/ansible/playbook.yml","w") as f:
            # f.write(yaml.dump(self.tasks))
            playbook = [{"hosts": "all", "tasks": self.tasks,"become": True}]
            f.write(yaml.dump(playbook))

    def to_list(self):
        return self.tasks
    
    def to_yaml(self):
        return yaml.dump(self.tasks)
    

class AnsibleStack:
    
    def __init__(self,stack_name,func_name,code):
        self.code = code
        self.stack_name = stack_name
        self.func_name = func_name

    def write_files(self):
        full_code = f"""
{self.code}

{self.func_name}()"""

        with open(f"./voyager/env/ansible/{self.stack_name}.py") as f:
            f.write(yaml.dump(self.code))

        return self.code

    def deploy(self):
        self.write_files()
        with plumbum.local.cwd("./voyager/env/ansible"):
            execute_command("ansible-playbook -i ./inventory.yml ./playbook.yml")

    def full_code(self):
        return f"""
from voyager.env.buffer import AnsibleInventoryBuilder, AnsibleTaskBuilder, AnsibleDeployer
import os

{self.code}


        """
    

class CombinedStack:

    def __init__(self,pulumi_stacks,ansible_stacks, dependencieMap,path="./voyager/env/pulumi"):
        self.pulumi_stack = pulumi_stacks
        self.ansible_stack = ansible_stacks
        self.dependencieMap = dependencieMap
        self.path = path

    def write_files(self):
        pulumi_code = "state_dict = {}\n"
        ansible_code = ""
        for stack in self.pulumi_stack:
            pulumi_code += stack.full_code()
        for stack in self.ansible_stack:
            ansible_code += stack.full_code()
        full_code = f"""{pulumi_code}

{ansible_code}"""
        
        for key in self.dependencieMap:
            for dependencie in self.dependencieMap[key]:
                full_code += f"""
AnsibleDeployer(**{key}(state_dict["{dependencie}"])).deploy()
"""
        print(self.path)
        with open(f"{self.path}/combined.py","w") as f:
            f.write(full_code)
        return full_code

    


# CombinedStack(
#     [PulumiStack("my_stack","my_stack","""def my_stack():
#         s3.Bucket("my-bucket-dshbfkjawhbdhks")""")],
#     [AnsibleStack("my_a_stack","my_ansible_example",
# """def my_a_stack(ip_address,key_file):
    
#     inventory = AnsibleInventoryBuilder()
#     inventory.add_host("my_host",ip_address,key_file,group="my_group")
#     inventory.add_group("my_group")
#     tasks = AnsibleTaskBuilder()
#     tasks.add_task("install nginx","apt",args={"name": "nginx","state": "present"})
#     tasks.add_task("start nginx","service",args={"name": "nginx","state": "started"})
#     tasks.add_task("enable nginx","service",args={"name": "nginx","enabled": True})
#     """)],{"my_a_stack":["my_stack"]}).write_files()

    

class AnsibleDeployer:

    def __init__(self,inventory,tasks) -> None:
        self.inventoryBuilder = inventory
        self.taskBuilder = tasks

    def write_files(self):
        self.inventoryBuilder.write_file()
        self.taskBuilder.write_file()

    def deploy(self):
        self.write_files()
        print("Waiting for instance to be ready...")
        time.sleep(60)


        with plumbum.local.cwd("./voyager/env/ansible"):
            plumbum.local["ansible-playbook"](["-i", "./inventory.yml", "./playbook.yml"])
        