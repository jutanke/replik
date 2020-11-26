"""
replik creates an easy-to-reuse environment based on docker
"""
import os
from os import makedirs
from os.path import isfile, join
from shutil import copyfile

import click

import replik.console as console


@click.command()
@click.argument("directory")
@click.argument("tool")
def replik(directory, tool):
    """
    """
    print("\n")
    if tool == "init":
        init(directory)

    print("\n")


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


if __name__ == "__main__":
    replik()
