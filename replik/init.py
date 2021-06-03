import os
import json
from os.path import join
from shutil import copyfile

import replik.console as console
import replik.constants as const
import replik.utils as utils


def execute(directory: str, simple=False):
    """pass"""
    replik_dir = os.getcwd()
    templates_dir = join(replik_dir, "templates")
    replik_fname = const.replik_root_file(directory)

    console.write(f"initialize at {directory}")

    if const.is_replik_project(directory):
        console.fail(f"Directory {directory} already contains a 'replik' project")
        exit(0)  # exit program

    # create folder structure
    console.info("project name:")
    project_name = input()
    if len(project_name) == 0:
        console.fail("Name must be at least one character long!")
        exit(0)
    for forbidden_string in const.FORBIDDEN_CHARACTERS:
        if forbidden_string in project_name:
            console.fail(f"Name must not contain '{forbidden_string}'!")
            exit(0)
    print("\n")

    username = const.get_username().lower().replace(" ", "_")

    info = {
        "name": project_name,
        "tag": f"{username}/replik_{project_name}",
        "docker_shm": "32g",
        "memory": "12g",
        "cpus": "8",
        "gpus": "0",
        "is_simple": simple,
    }

    docker_dir = join(directory, "docker")
    os.makedirs(docker_dir)

    # handle .gitignore
    gitignore_file = join(directory, ".gitignore")
    with open(gitignore_file, "a+") as f:
        f.write("output/\n")
        f.write("paths.json\n")

    if not simple:
        # if not "simple": create additional boilerplate
        project_dir = join(directory, project_name)
        os.makedirs(project_dir)
        script_dir = join(project_dir, "scripts")
        os.makedirs(script_dir)
        utils.copy2target("demo_script.py", templates_dir, script_dir)

        output_dir = join(directory, "output")
        makedirs(output_dir)

    # copy docker files
    utils.copy2target("hook_post_useradd", templates_dir, docker_dir)
    utils.copy2target("hook_pre_useradd", templates_dir, docker_dir)
    utils.copy2target("bashhook.sh", templates_dir, docker_dir)
    utils.copy2target("Dockerfile", templates_dir, docker_dir)
    dockerignore_tar = join(docker_dir, ".dockerignore")
    copyfile(join(templates_dir, "dockerignore"), dockerignore_tar)

    with open(replik_fname, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)
