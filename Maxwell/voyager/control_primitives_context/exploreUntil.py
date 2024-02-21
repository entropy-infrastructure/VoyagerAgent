"""
Add nginx to an EC2 instance
def my_ansible_example(ip_address,key_file):

    inventory = AnsibleInventoryBuilder()
    inventory.add_host("my_host",ip_address,key_file,group="my_group")
    inventory.add_group("my_group")
    tasks = AnsibleTaskBuilder()
    tasks.add_task("install nginx","apt",args={"name": "nginx","state": "present"})
    tasks.add_task("start nginx","service",args={"name": "nginx","state": "started"})
    tasks.add_task("enable nginx","service",args={"name": "nginx","enabled": True})
    return {
        "inventory": inventory,
        "tasks": tasks
    }
"""
def ansible_InstallDocker(output):
    """
    Implementation of this function is omitted.
    In this case the output would contain the target host, ip, and private key location.

    return {
        inventory:
        tasks
    }
    """
