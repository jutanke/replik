from shutil import copyfile
from os.path import join


def copy2target(fname: str, templates_dir: str, directory: str):
    src_file = join(templates_dir, fname)
    tar_file = join(directory, fname)
    copyfile(src_file, tar_file)