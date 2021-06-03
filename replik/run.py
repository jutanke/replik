from os.path import join
import replik.constants as const
import replik.build as build


def execute(directory: str, script: str, is_scheduled):
    """"""
    info = const.get_replik_settings(directory)
    tag = info["tag"]
    name = info["name"]
    docker_shm = info["docker_shm"]
    memory = info["memory"]
    cpus = info["cpus"]
    gpus = int(info["gpus"])
    dockerdir = const.get_dockerdir(directory)

    build.execute(directory, script, info)

    # execute the docker image
    src_dir = join(directory, name)

    docker_exec_command = f'docker run --privileged --shm-size="{docker_shm}" '
    docker_exec_command += f'--memory="{memory}" '
    docker_exec_command += f'--cpus="{cpus}" '
    if gpus > 0:
        if is_scheduled:
            raise NotImplementedError("EEE")
        else:
            docker_exec_command += "--gpus all "

    # docker_exec_command += docker_mem + '" '

    print(docker_exec_command)
