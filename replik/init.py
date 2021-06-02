import os
from os.path import join
import replik.console as console
import replik.constants as const
from shutil import copyfile, move


def execute(directory, simple=False):
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
    print("\n")

    username = const.get_username().lower().replace(" ", "_")

    if not simple:
        project_dir = join(directory, project_name)
        os.makedirs(project_dir)
        script_dir = join(project_dir, "scripts")
        os.makedirs(script_dir)

    info = {
        "name": project_name,
        "tag": f"{username}/replik_{project_name}",
        "docker_shm": "32g",
        "memory": "12g",
        "cpus": "8",
    }

    docker_dir = join(directory, "docker")
    os.makedirs(docker_dir)

    # handle .gitignore
    gitignore_file = join(directory, ".gitignore")

    print(info)

    # print("\n\n")
    # # print("init", directory, simple)
    # print(username)
    # print(replik_dir)
