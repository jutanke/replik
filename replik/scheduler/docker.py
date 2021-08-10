from subprocess import call
import subprocess
import time


def kill(container_name: str):
    call(
        f"docker exec -d {container_name} bash /home/user/docker/killhook.sh",
        shell=True,
    )
    time.sleep(10)
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
