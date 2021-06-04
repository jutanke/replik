"""
"""
import json
from typing import List, Tuple
from os.path import join, isfile


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
        pass

    return paths