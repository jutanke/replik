import pwd
import os
import json
from os.path import join, isfile
from typing import Dict
from datetime import datetime


import replik.console as console


VERSION = "0.6.0"

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


def check_if_string_contains_forbidden_symbols(txt: str) -> bool:
    global FORBIDDEN_CHARACTERS
    for c in FORBIDDEN_CHARACTERS:
        if c in txt:
            return True
    return False


def running_files_dir_for_scheduler() -> str:
    return "/srv/replik_schedule/running"


def staging_files_dir_for_scheduler() -> str:
    return "/srv/replik_schedule/staging"


def get_dockerdir(directory: str) -> str:
    return join(directory, "docker")


def get_local_replik_dir(directory: str) -> str:
    return join(directory, ".replik")


def replik_root_file(directory: str) -> str:
    """
    {root}/.replik
    """
    return join(directory, ".replik/info.json")


def is_replik_project(directory: str) -> bool:
    """"""
    return isfile(replik_root_file(directory))


def get_username():
    """"""
    return pwd.getpwuid(os.getuid()).pw_gecos


def is_broken_project(directory: str) -> bool:
    """"""
    return isfile(join(directory, "docker/Dockerfile.bkp"))


def get_stdout_file_in_container(directory: str, outfile_name: str = "") -> str:
    now = datetime.now()
    dt_string = now.strftime("%Y%m%d_%H%M%S")
    if len(outfile_name) == 0:
        return f"/home/user/.replik/logs/stdout_{dt_string}.log"
    else:
        return f"/home/user/.replik/logs/{outfile_name}_{dt_string}.log"


def get_replik_settings(directory: str) -> Dict:
    """"""
    if not is_replik_project(directory):
        console.fail(f"Directory {directory} is no replik project")
        exit(0)  # exit program
    replik_fname = replik_root_file(directory)
    with open(replik_fname, "r") as f:
        return json.load(f)
