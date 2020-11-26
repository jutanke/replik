import click

import replik.console as console


@click.command()
@click.argument("directory")
@click.argument("tool")
def replik(directory, tool):
    """
    """
    print("\n")
    if tool == "init":
        init(directory)

    print("\n")


def init(directory):
    """ initialize a repository
    """
    console.write(f"initialize at {directory}")


if __name__ == "__main__":
    replik()
