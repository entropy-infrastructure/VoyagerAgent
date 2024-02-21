from skill import SkillManager
import os

openai_api_key=os.getenv("OPENAI_API_KEY")

skillcode = """
def apache_pulumi():
    # Create a security group
    security_group = ec2.SecurityGroup("apache-sg",
        ingress=[
            ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=22,
                to_port=22,
                cidr_blocks=["0.0.0.0/0"],
            ),
            ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=80,
                to_port=80,
                cidr_blocks=["0.0.0.0/0"],
            ),
            ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=443,
                to_port=443,
                cidr_blocks=["0.0.0.0/0"],
            ),
        ],
    )

    # Create an EC2 instance
    instance = ec2.Instance("apache-instance",
        instance_type="t2.micro",
        ami="ami-0c94855ba95c71c99",
        key_name=pulumi_config.require("keypair_path"),
        security_groups=[security_group.name],
    )

    pulumi.export("instance_id", instance.id)
    pulumi.export("public_ip", instance.public_ip)
    pulumi.export("private_key", instance.key_name)
"""
ansiblecode = """
def apache_ansible(output):
    inventory = AnsibleInventoryBuilder()
    inventory.add_host("apache_host", output["public_ip"], output["private_key"], group="apache_group")
    inventory.add_group("apache_group")
    tasks = AnsibleTaskBuilder()
    tasks.add_task("install apache", "apt", args={"name": "apache2", "state": "present"})
    tasks.add_task("start apache", "service", args={"name": "apache2", "state": "started"})
    tasks.add_task("enable apache", "service", args={"name": "apache2", "enabled": True})
    return {
        "inventory": inventory,
        "tasks": tasks
    }
"""

def main():
    # set openai api key
    os.environ["OPENAI_API_KEY"] = openai_api_key

    skill_manager = SkillManager(retrieval_top_k=1)

    task = "Create an apache server"

    # print(cirriculum_agent.render_human_message())

    print(skill_manager.generate_pulumi_skill_description(program_name="apache_pulumi", program_code=skillcode))
    print(skill_manager.generate_ansible_skill_description(program_name="apache_ansible", program_code=ansiblecode))

    info = {
        "pulumi_program_name": "apache_pulumi",
        "pulumi_program_code": skillcode,
        "ansible_program_name": "apache_ansible",
        "ansible_program_code": ansiblecode,
        "task":"Deploy an apache server",
        "context":""
    }

    skill_manager.add_new_pulumi_skill(info)
    skill_manager.add_new_ansible_skill(info)
    print(skill_manager.retrieve_skills("apache"))


if __name__ == "__main__":
    main()
