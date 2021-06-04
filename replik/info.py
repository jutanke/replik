import replik.console as console
import replik.constants as const
from replik.paths import load_all_extra_paths
from os.path import isdir


def execute(directory: str):
    if const.is_replik_project(directory):
        info = const.get_replik_settings(directory)
        name = info["name"]
        version = info["replik_version"]
        is_simple = info["is_simple"]
        console.write("\n~ ~ ~ ~ ~ ~ ~ ~ ~ ~")
        console.info(f"path: \t\t{directory}")
        console.info(f"name: \t\t{name}")
        if is_simple:
            console.info(f"is simple: \t[y]")
        else:
            console.info(f"is simple: \t[n]")
        console.info(f"version:\t{version}")

        console.write("\ncheck paths:")
        for path_host, _ in load_all_extra_paths(directory):
            if isdir(path_host):
                console.success(f"'{path_host}' is valid")
            else:
                console.warning(f"'{path_host}' does not exist")
        print("\n")
        console.write("~ ~ ~ ~ ~ ~ ~ ~ ~ ~\n")

    else:
        console.warning("Not a valid replik repository")
