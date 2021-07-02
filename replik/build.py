import os
from os.path import join
from typing import Dict
from shutil import copyfile, move
from subprocess import call

import replik.console as console
import replik.utils as utils
import replik.constants as const


def execute(directory: str, script: str, info: Dict, outfile_name: str = ""):
    """"""
    utils.handle_broken_project(directory)
    dockerdir = const.get_dockerdir(directory)
    dockerfile = join(dockerdir, "Dockerfile")
    dockerfile_bkp = join(dockerdir, "Dockerfile.bkp")
    hook_pre_useradd = join(dockerdir, "hook_pre_useradd")
    hook_post_useradd = join(dockerdir, "hook_post_useradd")

    tag = info["tag"]
    name = info["name"]
    docker_mem = info["docker_shm"]
    is_simple = info["is_simple"]
    stdout_to_file = info["stdout_to_file"]

    if len(outfile_name) > 0:
        if not info["stdout_to_file"]:
            console.fail(
                f"Output file name is set to '{outfile_name}' but is currently set to output to terminal rather than file!"
            )
            exit()
        # check for forbidden chars
        if const.check_if_string_contains_forbidden_symbols(outfile_name):
            console.fail(
                f"Output file name is set to '{outfile_name}' which contains invalid characters for a file name!"
            )
            exit()

    # -- (1) construct Dockerfile
    move(dockerfile, dockerfile_bkp)

    with open(dockerfile, "w") as D:
        with open(dockerfile_bkp) as D_base:
            for line in D_base:
                D.write(line)
        D.write("\n")
        with open(hook_pre_useradd) as hook:
            for line in hook:
                D.write(line)
        D.write("\n")

        # add user
        uid = os.getuid()
        D.write(f'RUN adduser --disabled-password --gecos "" -u {uid} user')
        D.write("\nUSER user\n")

        with open(hook_post_useradd) as hook:
            for line in hook:
                D.write(line)

        # add the script call
        D.write("\n")

        pipe = ""
        if stdout_to_file:
            outfile = const.get_stdout_file_in_container(directory, outfile_name)
            pipe = f" &>{outfile}"

        if is_simple:
            D.write(
                'RUN echo "source ~/.bashrc\\n'
                + f'cd /home/user/{name} && bash {script}{pipe}"'
                + " >> /home/user/run.sh"
            )
        else:
            D.write(
                'RUN echo "source ~/.bashrc\\n'
                + f'cd /home/user/{name}/scripts && python {script}{pipe}"'
                + f" >> /home/user/run.sh"
            )

        # add startup bash hook
        D.write("\n")
        D.write(
            'RUN echo "/bin/bash /home/user/docker/bashhook.sh" >> /home/user/.bashrc'
        )

    r = call(f"cd {dockerdir} && docker build --tag='{tag}' .", shell=True)

    move(dockerfile_bkp, dockerfile)
    if r != 0:
        console.fail("building failed\n")
        exit(0)

    # --
