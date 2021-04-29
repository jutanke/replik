import time
from os import listdir, remove
from os.path import isfile, join


def sec2mins(secs):
    return secs / 60


def lock(path, uid):
    fname = join(path, uid + ".lock")
    if isfile(fname):
        remove(fname)
    with open(fname, "w") as f:
        f.write(str(time.time()))


def unlock(path, uid):
    fname = join(path, uid + ".lock")
    if isfile(fname):
        remove(fname)


def is_locked(path, uid):
    """path is locked if it contains .lock"""
    is_locked = False
    for f in listdir(path):
        fname = join(path, f)
        if uid in fname:
            # we ignore our own locks
            continue
        if isfile(fname) and fname.endswith(".lock"):
            with open(fname, "r") as f:
                created = float(f.readline())

            elapsed_mins = sec2mins(time.time() - created)
            if elapsed_mins < 0.5:
                is_locked = True
            else:
                remove(fname)
    return is_locked
