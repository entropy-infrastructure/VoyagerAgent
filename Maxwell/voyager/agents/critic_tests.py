from critic import CriticAgent
import os

openai_api_key=os.getenv("OPENAI_API_KEY")

apache_code = """
import pulumi
from pulumi_aws import ec2

def apache_pulumi():
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

    critic_agent = CriticAgent(mode="auto")

    task = "Create an apache server"

    print(critic_agent.check_task_success("", "Create an apache server", "", apache_code))


if __name__ == "__main__":
    main()
