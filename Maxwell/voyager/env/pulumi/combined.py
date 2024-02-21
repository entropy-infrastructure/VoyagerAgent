state_dict = {}
import pulumi
from pulumi_aws import *
from pulumi import automation as auto

def deploy_ec2_instance():
    # Create a new Security Group that allows SSH, HTTP, and HTTPS access
    group = ec2.SecurityGroup("web-secgrp", egress=[
        {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"],}],
        ingress=[
            {"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"],},
            {"protocol": "tcp", "from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"],},
            {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"],},])

    # Create a new EC2 instance
    server = ec2.Instance("web-server-www",
        instance_type="a1.medium",
        vpc_security_group_ids=[group.id],
        ami="ami-08305dd8ab642ad8c",
        key_name="my-KeyPair",
        tags={
            "Name": "web-server",
        },
    )

    pulumi.export("publicIp", server.public_ip)



deploy_ec2_instance_stack = auto.create_or_select_stack(
        stack_name="deploy_ec2_instance_stack68",
        project_name="project",
        program=deploy_ec2_instance)

    # Set the AWS region.
deploy_ec2_instance_stack.set_config("aws:region", auto.ConfigValue(value="us-west-2"))

up_res = deploy_ec2_instance_stack.up(on_output=print)
state_dict["deploy_ec2_instance_stack"] = deploy_ec2_instance_stack.outputs()



from voyager.env.buffer import AnsibleInventoryBuilder, AnsibleTaskBuilder, AnsibleDeployer
import os

def ansible(state):
    inventory = AnsibleInventoryBuilder()
    inventory.add_host("my_host", state['publicIp'], "./testkey", group="my_group")
    inventory.add_group("my_group")
    tasks = AnsibleTaskBuilder()
    tasks.add_task("install docker","apt",args={"name": ["docker.io"],"state": "present","update_cache": True})
    tasks.add_task("copy directory","ansible.posix.synchronize",args={'src': os.path.abspath("."),'dest': '/home/ubuntu/','mode': 'push','delete': True,'recursive': True,'times': True,'compress': True,'links': True,'checksum': True})
    tasks.add_task("build image","community.docker.docker_image",args={"source": "build","state": "present","build": {"path":"/home/ubuntu/Maxwell","pull":True},"name":"my_docker_image","force_source":True})
    tasks.add_task("start container","community.docker.docker_container",args={"name": "my_docker_container","image": "my_docker_image","state":"started","detach":True})
    return {
        "inventory": inventory,
        "tasks": tasks
    }


        
AnsibleDeployer(**ansible(state_dict["deploy_ec2_instance_stack"])).deploy()
