"""
replik creates an easy-to-reuse environment based on docker
"""
import json
import os
import sys
from os import makedirs, remove
from os.path import basename, isdir, isfile, join
from shutil import copyfile, move
from typing import Dict

import click

import replik.console as console
import replik.init as init
import replik.run as run
import replik.info as info
import replik.scheduler.schedule as schedule


def demask_script(script):
    return script.replace("#", " ")


@click.command()
@click.argument("directory")
@click.argument("tool")
@click.option("--script", default="demo_script.py")
@click.option("--extra_paths", default="")
@click.option("--sid", default="")
def replik(directory, tool, script, extra_paths, sid):
    """"""
    script = demask_script(script)

    if tool == "init":
        init.execute(directory, simple=False)
    elif tool == "init-simple":
        init.execute(directory, simple=True)
    elif tool == "run":
        run.execute(
            directory,
            script,
            final_docker_exec_command="/bin/bash /home/user/run.sh",
        )
    elif tool == "enter":
        run.execute(directory, script, final_docker_exec_command="/bin/bash")
    elif tool == "info":
        info.execute(directory)
    elif tool == "schedule":
        schedule.execute(
            directory, script, final_docker_exec_command="/bin/bash /home/user/run.sh"
        )
    else:
        console.warning(f"no command '{tool}'")


if __name__ == "__main__":
    replik()
