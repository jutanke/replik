"""
replik creates an easy-to-reuse environment based on docker
"""
import json
import os
import sys
from os import makedirs, remove
from os.path import basename, isdir, isfile, join
from shutil import copyfile, move
from subprocess import call
from typing import Dict

import click

import replik.console as console
import replik.replik_scheduler as sched


@click.command()
@click.argument("directory")
@click.argument("tool")
@click.option("--script", default="demo_script.py")
@click.option("--extra_paths", default="")
@click.option("--sid", default="")
def replik(directory, tool, script, extra_paths, sid):
    """
    :param extra_paths: path to file that contains extra paths
        [
            {
                "dir": "/path/to/folder",
                "alias": "alias_inside_container"
            }
        ]
    """
    print("\n")
    if tool == "init":
        init(directory)
    elif tool == "init-simple":
        init(directory, simple=True)
    elif tool == "run":
        run(directory, script, extra_paths)
    elif tool == "schedule":
        schedule(directory, script, extra_paths)
    elif tool == "unschedule":
        sched.unschedule(sid)
    elif tool == "schedule-info":
        sched.info()
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

    handle_broken_project(directory)


def handle_broken_project(directory):
    if is_broken_project(directory):
        console.warning(
            "\nThis repo seems to be broken (interrupt during Docker build)"
        )
        fname_bkp = join(directory, "docker/Dockerfile.bkp")
        fname_broken = join(directory, "docker/Dockerfile")
        move(fname_bkp, fname_broken)
        console.success("\tfixed!\n")


def run(directory, script, extra_paths):
    build(
        directory,
        script,
        final_docker_exec_command="/bin/bash /home/user/run.sh",
        extra_paths=extra_paths,
    )


def enter(directory, script):
    build(directory, script, final_docker_exec_command="/bin/bash")


def schedule(directory, script, extra_paths):
    build(
        directory,
        script,
        final_docker_exec_command="/bin/bash /home/user/run.sh",
        extra_paths=extra_paths,
        scheduler_id=sched.generate_id(directory, script),
    )


def get_data_paths(directory):
    info = get_replik_settings(directory)
    alternative_data_file = join(directory, "paths.json")
    data = info["data"]
    if info["use_alternative_data_paths"]:
        assert isfile(alternative_data_file), alternative_data_file
        with open(alternative_data_file, "r") as f:
            data_from_file = json.load(f)
            data = []
            for d in data_from_file:
                if "/" in d:
                    data.append(d)
                else:
                    # make any "lonely" folder relative to the project dir
                    d = join(directory, d)
                    if not isdir(d):
                        makedirs(d)
                    data.append(d)

    return data


def build(
    directory, script, final_docker_exec_command, extra_paths="", scheduler_id=""
):
    """
    :param extra_paths: path to file that contains extra paths
        [
            {
                "dir": "/path/to/folder",
                "alias": "alias_inside_container"
            }
        ]
    :param scheduler_id: if not empty this id uniquely identifies this process
    """
    if not is_replik_project(directory):
        console.fail(f"{directory} is not a valid replik project")
        exit(0)

    handle_broken_project(directory)

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
    docker_mem = info["docker_shm"]

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
    docker_exec_command = 'docker run --privileged --shm-size="'
    docker_exec_command += docker_mem + '" '

    if sys.platform != "darwin" and len(scheduler_id) == 0:
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

    if len(extra_paths) > 0:
        if not isfile(extra_paths):
            extra_paths = join(directory, extra_paths)
        # extra paths are provided as .json
        with open(extra_paths) as f:
            extra_paths = json.load(f)
            # [
            #    {
            #        "dir": "/path/to/folder",
            #        "alias": "alias_inside_container"
            #    }
            # ]
            for path_entry in extra_paths:
                path = path_entry["dir"]
                alias = path_entry["alias"]
                if isdir(path):
                    console.success(f"map {path}")
                    docker_exec_command += f"-v {path}:/home/user/{alias} "
                else:
                    console.warning(f"could not map {path}")

    final_docker_exec_command = f"--rm -it replik/{tag} " + final_docker_exec_command
    if len(scheduler_id) > 0:
        # IF scheduled we need to potentially delay here!
        sched.schedule(
            directory,
            script,
            scheduler_id,
            docker_exec_command,
            final_docker_exec_command,
        )
    else:
        # docker_exec_command += f"--rm -it replik/{tag} "
        docker_exec_command += final_docker_exec_command
        call(docker_exec_command, shell=True)


def help(directory):
    """help info"""
    replik_dir = os.getcwd()
    console.info("*** replik ***")
    console.write(f"replik path: {replik_dir}\n")

    if is_replik_project(directory):
        check(directory)


def is_broken_project(directory: str) -> bool:
    """"""
    return isfile(join(directory, "docker/Dockerfile.bkp"))


def is_replik_project(directory: str) -> bool:
    """True if the directory is a valid replik repo"""
    replik_fname = join(directory, ".replik")
    return isfile(replik_fname)


def get_replik_settings(directory: str) -> Dict:
    """"""
    if not is_replik_project(directory):
        console.fail(f"Directory {directory} is no replik project")
        exit(0)  # exit program
    replik_fname = join(directory, ".replik")
    with open(replik_fname, "r") as f:
        return json.load(f)


def init(directory, simple=False):
    """initialize a repository"""
    replik_dir = os.getcwd()
    templates_dir = join(replik_dir, "templates")

    replik_fname = join(directory, ".replik")
    console.write(f"initialize at {directory}")
    if is_replik_project(directory):
        console.fail(f"Directory already contains a 'replik' project")
        return

    # create folder structure
    console.info("project name:")
    project_name = input()
    if len(project_name) == 0:
        console.fail("Name must be at least one character long!")
        return
    print("\n")

    use_alternative_data_paths = True  # this is only for backward-compatibilty
    info = {
        "name": project_name,
        "tag": f"replik_{project_name}",
        "data": [],
        "use_alternative_data_paths": use_alternative_data_paths,
        "docker_shm": "32g",
    }

    if use_alternative_data_paths:
        output_dir = join(directory, "output")
        makedirs(output_dir)

        data_fname = join(directory, "paths.json")
        data_locations = [output_dir]
        with open(data_fname, "w") as f:
            json.dump(data_locations, f, indent=4, sort_keys=True)

    else:
        console.write("Do you want to add data directories? [y/N]")
        add_data = input()
        while add_data == "y":
            console.write("data path:")
            data_path = input()
            assert isdir(data_path), data_path
            info["data"].append(data_path)
            console.write("Do you want to add additional data directories? [y/N]")
            add_data = input()

    if not simple:
        project_dir = join(directory, project_name)
        makedirs(project_dir)
        script_dir = join(project_dir, "scripts")
        makedirs(script_dir)
    docker_dir = join(directory, "docker")
    makedirs(docker_dir)

    # handle .gitignore
    gitignore_file = join(directory, ".gitignore")

    with open(gitignore_file, "a+") as f:
        f.write("output/\n")
        f.write("paths.json\n")

    # copy templates to appropriate folders
    def copy2tar(fname: str, templates_dir: str, directory: str):
        src_file = join(templates_dir, fname)
        tar_file = join(directory, fname)
        copyfile(src_file, tar_file)

    copyfile(join(templates_dir, "Dockerfile"), join(docker_dir, "Dockerfile"))
    dockerignore_tar = join(docker_dir, ".dockerignore")
    copyfile(join(templates_dir, "dockerignore"), dockerignore_tar)
    if not simple:
        demoscript_tar = join(script_dir, "demo_script.py")
        copyfile(join(templates_dir, "demo_script.py"), demoscript_tar)
    copy2tar("hook_post_useradd", templates_dir, join(directory, "docker"))
    copy2tar("hook_pre_useradd", templates_dir, join(directory, "docker"))
    copy2tar("bashhook.sh", templates_dir, join(directory, "docker"))

    with open(replik_fname, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)

    if not use_alternative_data_paths:
        gitignore = join(directory, ".gitignore")
        mode = "a" if isfile(gitignore) else "w"
        with open(gitignore, mode) as f:
            f.write("\n")
            f.write(".data.txt")


if __name__ == "__main__":
    replik()
