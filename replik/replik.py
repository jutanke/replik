"""
replik creates an easy-to-reuse environment based on docker
"""
import json
import os
from os import makedirs
from os.path import isdir, isfile, join
from shutil import copyfile

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

    print("\n")


def run(directory, script):
    """
    """
    pass


def init(directory):
    """ initialize a repository
    """
    replik_dir = os.getcwd()
    templates_dir = join(replik_dir, "templates")

    replik_fname = join(directory, ".replik")
    console.write(f"initialize at {directory}")
    if isfile(replik_fname):
        console.fail(f"Directory already contains a 'replik'")
        return

    # create folder structure
    console.info("project name:")
    project_name = input()
    if len(project_name) == 0:
        console.fail("Name must be at least one character long!")
        return
    print("\n")

    info = {"name": project_name, "data": []}

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
    copyfile(join(templates_dir, "Dockerfile"), join(docker_dir, "Dockerfile"))
    dockerignore_tar = join(docker_dir, ".dockerignore")
    copyfile(join(templates_dir, "dockerignore"), dockerignore_tar)
    demoscript_tar = join(script_dir, "demo_script.py")
    copyfile(join(templates_dir, "demo_script.py"), demoscript_tar)

    with open(replik_fname, "w") as f:
        json.dump(info, f, indent=4, sort_keys=True)


if __name__ == "__main__":
    replik()
