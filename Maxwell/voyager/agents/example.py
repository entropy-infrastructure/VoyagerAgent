import pulumi
from pulumi_aws import ec2

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