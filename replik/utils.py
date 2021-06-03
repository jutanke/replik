import replik.constants as const
from shutil import copyfile, move
from os.path import join


def copy2target(fname: str, templates_dir: str, directory: str):
    src_file = join(templates_dir, fname)
    tar_file = join(directory, fname)
    copyfile(src_file, tar_file)


def handle_broken_project(directory):
    if const.is_broken_project(directory):
        console.warning(
            "\nThis repo seems to be broken (interrupt during Docker build)"
        )
        fname_bkp = join(directory, "docker/Dockerfile.bkp")
        fname_broken = join(directory, "docker/Dockerfile")
        move(fname_bkp, fname_broken)
        console.success("\tfixed!\n")