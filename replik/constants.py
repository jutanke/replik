import pwd
import os
import json
from os.path import join, isfile
from typing import Dict


VERSION = "0.5.0"

FORBIDDEN_CHARACTERS = [
    " ",
    "%",
    "^",
    "&",
    "/",
    "\\",
    ".",
    "?",
    "$",
    "#",
    "'",
    '"',
    "!",
    ",",
    ".",
    ":",
    ";",
    "*",
    "(",
    ")",
    "[",
    "]",
    "-",
    "+",
    "=",
    "{",
    "}",
]


def get_dockerdir(directory: str) -> str:
    return join(directory, "docker")


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


def get_replik_settings(directory: str) -> Dict:
    """"""
    if not is_replik_project(directory):
        console.fail(f"Directory {directory} is no replik project")
        exit(0)  # exit program
    replik_fname = join(directory, ".replik")
    with open(replik_fname, "r") as f:
        return json.load(f)