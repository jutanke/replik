import pwd
import os
from os.path import join, isfile


def replik_root_file(directory: str) -> str:
    """
    {root}/.replik
    """
    return join(directory, ".replik")


def is_replik_project(directory: str) -> bool:
    """"""
    return isfile(replik_root_file(directory))


def get_username():
    """"""
    return pwd.getpwuid(os.getuid()).pw_gecos


def is_broken_project(directory: str) -> bool:
    """"""
    return isfile(join(directory, "docker/Dockerfile.bkp"))