"""
"""
import json
from typing import List, Tuple
from os.path import join, isfile, basename


def get_simple_path_fname(directory: str):
    """
    ["/path/to/file1", "/path/to/file2", ...]
    """
    return join(directory, ".replik_paths.json")


def load_all_extra_paths(directory: str) -> List[Tuple[str, str]]:
    """
    returns list with:
        ('path/on/host', 'path/in/container')
    """
    paths = []
    extra_paths = get_simple_path_fname(directory)
    if isfile(extra_paths):
        with open(extra_paths, "r") as f:
            for path_host in json.load(f):
                if "/" not in path_host:
                    path_host = join(directory, path_host)
                path_container = join("/home/user", basename(path_host))
                paths.append((path_host, path_container))
    return paths
