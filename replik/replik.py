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


@click.command()
@click.argument("directory")
@click.argument("tool")
@click.option("--script", default="demo_script.py")
@click.option("--extra_paths", default="")
@click.option("--sid", default="")
def replik(directory, tool, script, extra_paths, sid):
    """"""
    if tool == "init":
        init.execute(directory, simple=False)
    elif tool == "init-simple":
        init.execute(directory, simple=True)


if __name__ == "__main__":
    replik()