"""
replik creates an easy-to-reuse environment based on docker
"""
import json
import os
import sys
from os import makedirs, remove
from os.path import basename, isdir, isfile, join
from shutil import copyfile
from subprocess import call
from typing import Dict

import click

import replik.console as console


@click.command()
@click.argument("directory")
@click.argument("tool")
@click.option("--script", default="demo_script.py")
def replik(directory, tool, script):
    """
    """
    print("\n")
    if tool == "init":
        init(directory)
    elif tool == "run":
        run(directory, script)
    elif tool == "help":
        help(directory)
    elif tool == "enter":
        enter(directory, script)
    elif tool == "check":
        check(directory)
    print("\n")


def check(directory):
    """check if the directories still fit"""
    console.write(f"'{directory}' is valid replik project:")
    settings = get_replik_settings(directory)
    project_name = settings["name"]
    console.write(f"project name: {project_name}")
    console.write("project paths:")
    for path in get_data_paths(directory):
        if isdir(path):
            console.success(f"\t{path}")
        else:
            console.fail(f"\t{path}")


def enter(directory, script):
    build(directory, script, final_docker_exec_command="/bin/bash")


def run(directory, script):
    build(directory, script, final_docker_exec_command="/bin/bash /home/user/run.sh")


def get_data_paths(directory):
    info = get_replik_settings(directory)
    alternative_data_file = join(directory, ".data.txt")
    data = info["data"]
    if info["use_alternative_data_paths"]:
        if isfile(alternative_data_file):
            with open(alternative_data_file, "r") as f:
                data_cur = [l for l in f.readlines() if len(l) > 0]
            if len(data_cur) != len(data):
                console.fail(
                    "The number of files noted in .data.txt do not match! Fix manually!"
                )
                exit(0)
            else:
                data = data_cur
        else:
            console.write("Cannot find alterative data paths: set them up now:")
            data_cur = []
            with open(alternative_data_file, "w") as f:
                for path in data:
                    if isdir(path):
                        console.success(f"keep {path}? [Y/n]")
                        add_data = input()
                        if add_data.lower() == "n":
                            console.write("add new path:")
                            add_data = input()
                            assert isdir(add_data)
                            data_cur.append(add_data)
                            f.write(add_data + "\n")
                    else:
                        console.write(f"Add new path for {path}")
                        add_data = input()
                        assert isdir(add_data)
                        data_cur.append(add_data)
                        f.write(add_data + "\n")
            data = data_cur

    return data


def build(directory, script, final_docker_exec_command):
    """
    """
    if not is_replik_project(directory):
        console.fail(f"{directory} is not a valid replik project")
        exit(0)

    # backup the "base" Dockerfile
    dockerdir = join(directory, "docker")
    dockerfile = join(dockerdir, "Dockerfile")
    dockerfile_bkp = join(dockerdir, "Dockerfile.bkp")
    hook_pre_useradd = join(dockerdir, "hook_pre_useradd")
    hook_post_useradd = join(dockerdir, "hook_post_useradd")
    if isfile(dockerfile_bkp):
        remove(dockerfile_bkp)
    copyfile(dockerfile, dockerfile_bkp)
    remove(dockerfile)

    info = get_replik_settings(directory)
    tag = info["tag"]
    name = info["name"]

    # build the proper Dockerfile
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
        D.write(
            'RUN echo "source ~/.bashrc\\n'
            + f'cd /home/user/{name}/scripts && python {script}"'
            + " >> /home/user/run.sh"
        )

        # add startup bash hook
        D.write("\n")
        D.write(
            'RUN echo "/bin/bash /home/user/docker/bashhook.sh" >> /home/user/.bashrc'
        )

    r = call(f"cd {dockerdir} && docker build --tag='replik/{tag}' .", shell=True)
    remove(dockerfile)
    copyfile(dockerfile_bkp, dockerfile)
    remove(dockerfile_bkp)
    if r != 0:
        console.fail("building failed\n")
        exit(0)

    # execute the docker image
    src_dir = join(directory, name)
    docker_dir = join(directory, "docker")
    docker_exec_command = 'docker run --privileged --shm-size="8g" '
    if sys.platform != "darwin":
        # add gpu
        docker_exec_command += "--gpus all "
    docker_exec_command += f"-v {src_dir}:/home/user/{name} "
    docker_exec_command += f"-v {docker_dir}:/home/user/docker "
    settings_dir = join(directory, "settings")
    if isdir(settings_dir):
        # if a settings dir exists add it as volume
        docker_exec_command += f"-v {settings_dir}:/home/user/settings "
    for path in get_data_paths(directory):
        if isdir(path):
            console.success(f"map {path}")
            bn = basename(path)
            docker_exec_command += f"-v {path}:/home/user/{bn} "
        else:
            console.warning(f"could not map {path}")
    docker_exec_command += f"--rm -it replik/{tag} "
    docker_exec_command += final_docker_exec_command
    call(docker_exec_command, shell=True)


def help(directory):
    """ help info
    """
    replik_dir = os.getcwd()
    console.info("*** replik ***")
    console.write(f"replik path: {replik_dir}\n")

    if is_replik_project(directory):
        check(directory)


def is_replik_project(directory: str) -> bool:
    """True if the directory is a valid replik repo"""
    replik_fname = join(directory, ".replik")
    return isfile(replik_fname)


def get_replik_settings(directory: str) -> Dict:
    """
    """
    if not is_replik_project(directory):
        console.fail(f"Directory {directory} is no replik project")
        exit(0)  # exit program
    replik_fname = join(directory, ".replik")
    with open(replik_fname, "r") as f:
        return json.load(f)


def init(directory):
    """ initialize a repository
    """
    replik_dir = os.getcwd()
    templates_dir = join(replik_dir, "templates")

    replik_fname = join(directory, ".replik")
    console.write(f"initialize at {directory}")
    if is_replik_project(directory):
        console.fail(f"Directory already contains a 'replik'")
        return

    # create folder structure
    console.info("project name:")
    project_name = input()
    if len(project_name) == 0:
        console.fail("Name must be at least one character long!")
        return
    print("\n")

    info = {
        "name": project_name,
        "tag": f"replik_{project_name}",
        "data": [],
        "use_alternative_data_paths": False,
    }

    console.write("Do you want to add data directories? [y/N]")
    add_data = input()
    while add_data == "y":
        console.write("data path:")
        data_path = input()
        assert isdir(data_path), data_path
        info["data"].append(data_path)
        console.write("Do you want to add additional data directories? [y/N]")
        add_data = input()

    project_dir = join(directory, project_name)
    makedirs(project_dir)
    script_dir = join(project_dir, "scripts")
    makedirs(script_dir)
    docker_dir = join(directory, "docker")
    makedirs(docker_dir)

    # copy templates to appropriate folders
    def copy2tar(fname: str, templates_dir: str, directory: str):
        src_file = join(templates_dir, fname)
        tar_file = join(directory, fname)
        copyfile(src_file, tar_file)

    copyfile(join(templates_dir, "Dockerfile"), join(docker_dir, "Dockerfile"))
    dockerignore_tar = join(docker_dir, ".dockerignore")
    copyfile(join(templates_dir, "dockerignore"), dockerignore_tar)
    demoscript_tar = join(script_dir, "demo_script.py")
    copyfile(join(templates_dir, "demo_script.py"), demoscript_tar)
    copy2tar("hook_post_useradd", templates_dir, join(directory, "docker"))
    copy2tar("hook_pre_useradd", templates_dir, join(directory, "docker"))
    copy2tar("bashhook.sh", templates_dir, join(directory, "docker"))

    with open(replik_fname, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)

    gitignore = join(directory, ".gitignore")
    mode = "a" if isfile(gitignore) else "w"
    with open(gitignore, mode) as f:
        f.write("\n")
        f.write(".data.txt")


if __name__ == "__main__":
    replik()
