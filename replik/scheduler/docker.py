from subprocess import call
import subprocess


def kill(container_name: str):
    call(f"docker kill {container_name}", shell=True)


def get_running_container_names():
    """
    get the names of all currently running containers
    """
    return [
        f.replace('"', "")
        for f in (
            subprocess.run(
                ["docker", "ps", "--format", '"{{.Names}}"'], stdout=subprocess.PIPE
            )
            .stdout.decode("utf-8")
            .lower()
            .split("\n")
        )
        if len(f) > 0
    ]
