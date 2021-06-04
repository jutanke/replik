import replik.constants as const
import replik.build as build
from subprocess import call
from typing import Dict
from os.path import join


def set_shm_cpu_memory(info: Dict):
    docker_shm = info["docker_shm"]
    memory = info["memory"]
    cpus = info["cpus"]
    docker_exec_command = f' --privileged --shm-size="{docker_shm}" '
    docker_exec_command += f'--memory="{memory}" '
    docker_exec_command += f'--cpus="{cpus}" '
    return docker_exec_command


def set_all_paths(directory: str, info: Dict):
    name = info["name"]
    if info["is_simple"]:
        docker_exec_command = f"-v {directory}:/home/user/{name} "
    else:
        src_dir = join(directory, name)
        docker_exec_command = f"-v {src_dir}:/home/user/{name} "

    dockerdir = const.get_dockerdir(directory)
    docker_exec_command += f"-v {dockerdir}:/home/user/docker "

    return docker_exec_command


def execute(directory: str, script: str, final_docker_exec_command: str):
    """"""
    info = const.get_replik_settings(directory)
    tag = info["tag"]
    name = info["name"]

    gpus = int(info["gpus"])
    dockerdir = const.get_dockerdir(directory)

    build.execute(directory, script, info)

    # execute the docker image

    docker_exec_command = "docker run" + set_shm_cpu_memory(info)

    if gpus > 0:
        docker_exec_command += "--gpus all "

    docker_exec_command += set_all_paths(directory, info)

    docker_exec_command += f"--rm -it {tag} " + final_docker_exec_command

    call(docker_exec_command, shell=True)
