import yaml
from nornir import InitNornir
from nornir.core.task import Task, Result
from nornir_rich.progress_bar import RichProgressBar
from nornir_rich.functions import print_result
from nornir_jinja2.plugins.tasks import template_file
from nornir_netmiko.tasks import netmiko_send_config

def apply_service_declaration(task: Task, services: list) -> Result:
    # TODO: Implement this task to provision the services defined in "services.yaml"
    # and deprovision any unnecessary services currently deployed on the devices.
    # Note: Ensure device management access.
    # Hint: Use subtasks to keep the code organized.
    selected = []

    for service in services:
        for site_name, site_config in service["sites"].items():
            if task.host.has_parent_group(site_name):
                selected.append({
                    **service,
                    "interfaces": site_config["interfaces"],
                })

    rendered = task.run(
        task=template_file,
        template="service.j2",
        path="l3vpn/templates",
        services=selected,
        bgp_as=task.host["bgp_as"],
        router_id=task.host["router_id"],
    )

    config_text = rendered.result

    if task.is_dry_run():
        return Result(host=task.host, result=config_text)

    deployed = task.run(
        task=netmiko_send_config,
        config_commands=config_text.splitlines(),
    )

    return Result(
        host=task.host,
        result=deployed.result,
        changed=deployed.changed,
    )


def main(dry_run: bool = True):
    with open("services.yaml") as file:
        services = yaml.safe_load(file)["services"]

    nr = InitNornir(config_file="config.yaml", dry_run=dry_run)

    eos_hosts = nr.filter(platform="eos")

    results = eos_hosts.run(
        task=apply_service_declaration,
        services=services,
    )
    print_result(results, vars=["result", "failed", "changed"])

