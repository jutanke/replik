"""
A process is defined as follows:

proc_id.json:
{
    "start_time": time.time(),
    "gpus": [0],
    "owner": "Julian Tanke",
    "directory": "/.../...",
    "script": "demo.py"
}

"""
import json
import hashlib
import time
from random import randint
from os.path import isdir, join
import random
from os import listdir
import pwd
import os
from os.path import isfile
import replik.console as console
import subprocess
import replik.lock as lock
from subprocess import call
import json


REPLIK_SHEDULE_FOLDER = "/srv/replik_schedule"
REPLIK_SHEDULE_STAGING_FOLDER = "/srv/replik_schedule/staging"
VALID_GPU_IDS = []
if len(VALID_GPU_IDS) == 0:
    FILTER_GPU_NAMES = ["geforce gt 730"]
    # find all valid gpus
    result = subprocess.run(["nvidia-smi", "-L"], stdout=subprocess.PIPE)
    for gpu in result.stdout.decode("utf-8").lower().split("\n"):
        if len(gpu) > 0:
            is_filtered = False
            for filter in FILTER_GPU_NAMES:
                if filter in gpu:
                    is_filtered = True
                    break
            if not is_filtered:
                VALID_GPU_IDS.append(
                    (int(gpu[4]), gpu[gpu.find(":") + 1 : gpu.find("(")])
                )


def load_schedule_settings(directory):
    """
    {
        "n_gpus": 1
    }
    """
    fname = join(directory, "scheduling.json")
    if isfile(fname):
        with open(fname, "r") as f:
            settings = json.load(f)
    else:
        settings = {"n_gpus": 1}
        with open(fname, "w") as f:
            f.write(json.dumps(settings, sort_keys=True, indent=4))
    return settings


def remove_from_staging(scheduler_id):
    global REPLIK_SHEDULE_STAGING_FOLDER
    fname = join(REPLIK_SHEDULE_STAGING_FOLDER, f"{scheduler_id}.json")
    if isfile(fname):
        os.remove(fname)


def is_unscheduled(scheduler_id):
    global REPLIK_SHEDULE_FOLDER

    # clean up all old unscheduled markers
    now = time.time()
    for fname in [
        join(REPLIK_SHEDULE_FOLDER, f)
        for f in listdir(REPLIK_SHEDULE_FOLDER)
        if f.endswith(".unschedule")
    ]:
        with open(fname, "r") as f:
            age_in_seconds = now - float(f.readline())
            if sec2h(age_in_seconds) > 0.25:
                # housekeeping: clean out old kill switches
                os.remove(fname)

    fname_kill = join(REPLIK_SHEDULE_FOLDER, f"{scheduler_id}.unschedule")
    return isfile(fname_kill)


def is_in_staging(scheduler_id):
    global REPLIK_SHEDULE_STAGING_FOLDER
    fname = join(REPLIK_SHEDULE_STAGING_FOLDER, f"{scheduler_id}.json")
    return isfile(fname)


def place_process_onto_running(directory, script, scheduler_id, gpus):
    global REPLIK_SHEDULE_FOLDER
    fname = join(REPLIK_SHEDULE_FOLDER, f"{scheduler_id}.json")
    assert not isfile(fname)
    proc = {
        "start_time": time.time(),
        "gpus": gpus,
        "owner": get_username(),
        "directory": directory,
        "script": script,
    }
    with open(fname, "w") as f:
        f.write(json.dumps(proc))


def place_process_onto_staging(directory, script, scheduler_id, settings, verbose=True):
    """"""
    if not is_in_staging(scheduler_id):
        if verbose:
            console.info("\tplaced onto staging...")
        global REPLIK_SHEDULE_STAGING_FOLDER
        proc = {
            "settings": settings,
            "start_waiting_time": time.time(),
            "owner": get_username(),
            "directory": directory,
            "script": script,
        }
        fname = join(REPLIK_SHEDULE_STAGING_FOLDER, f"{scheduler_id}.json")
        with open(fname, "w") as f:
            f.write(json.dumps(proc))


def unschedule(scheduler_id):
    global REPLIK_SHEDULE_FOLDER
    if len(scheduler_id) != 8:
        console.warning(
            f"Invaid schedule id {scheduler_id}. Must be exactly 8 integers"
        )
    else:
        console.info(f"unscheduing {scheduler_id}...")
        while True:
            # -- lock stage 1 --
            if not lock.is_locked(REPLIK_SHEDULE_FOLDER, scheduler_id):
                lock.lock(REPLIK_SHEDULE_FOLDER, scheduler_id)
                # -- lock stage 2 --
                # random delay to ensure we lock correctly:
                # Technically, this is not 100% thread-safe but with the expected
                # amount of usage it can be pretty much considered thread safe
                delay_seconds = random.uniform(0.3, 1.4)
                time.sleep(delay_seconds)
                if lock.is_locked(REPLIK_SHEDULE_FOLDER, scheduler_id):
                    lock.unlock(REPLIK_SHEDULE_FOLDER, scheduler_id)
                else:
                    # locked
                    # set kill-switch
                    fname_kill = join(
                        REPLIK_SHEDULE_FOLDER, f"{scheduler_id}.unschedule"
                    )
                    with open(fname_kill, "w") as f:
                        f.write(str(time.time()))
                    if scheduler_id in get_names_of_running_docker_containers():
                        fname = join(REPLIK_SHEDULE_FOLDER, f"{scheduler_id}.json")
                        assert isfile(fname)
                        call(f"docker kill {scheduler_id}", shell=True)
                        os.remove(fname)

                    lock.unlock(REPLIK_SHEDULE_FOLDER, scheduler_id)
                    exit()  # exit successfully
            delay_seconds = random.uniform(0.3, 1.4)
            time.sleep(delay_seconds)


def schedule(
    directory, script, scheduler_id, docker_exec_command, final_docker_exec_command
):
    """
    This function blocks as long as the script is not started
    """
    global REPLIK_SHEDULE_FOLDER
    if not isdir(REPLIK_SHEDULE_FOLDER):
        console.fail(f"Cannot schedule as path {REPLIK_SHEDULE_FOLDER} not available")
        exit(0)

    docker_exec_command += f"--name {scheduler_id} "

    settings = load_schedule_settings(directory)

    while True:
        # -- lock stage 1 --
        if not lock.is_locked(REPLIK_SHEDULE_FOLDER, scheduler_id):
            lock.lock(REPLIK_SHEDULE_FOLDER, scheduler_id)

            # -- lock stage 2 --
            # random delay to ensure we lock correctly:
            # Technically, this is not 100% thread-safe but with the expected
            # amount of usage it can be pretty much considered thread safe
            delay_seconds = random.uniform(0.3, 1.4)
            time.sleep(delay_seconds)
            if lock.is_locked(REPLIK_SHEDULE_FOLDER, scheduler_id):
                lock.unlock(REPLIK_SHEDULE_FOLDER, scheduler_id)

                # add to staging
                place_process_onto_staging(directory, script, scheduler_id, settings)
            else:
                # -- we are clear: no concurrent process! --
                if is_unscheduled(scheduler_id):
                    console.warning("unscheduled")
                    remove_from_staging(scheduler_id)
                    exit()

                free_gpus = get_free_gpus()
                if len(free_gpus) >= settings["n_gpus"]:
                    remove_from_staging(scheduler_id)

                    docker_command = docker_exec_command
                    if settings["n_gpus"] > 0:
                        docker_command += "--gpus '\"device="
                        gpus = []
                        for i in range(settings["n_gpus"]):
                            gpuid = free_gpus[i]
                            gpus.append(gpuid)
                            if i > 0:
                                docker_command += ","
                            docker_command += str(gpuid)
                        docker_command += "\"' "
                    docker_command += final_docker_exec_command
                    place_process_onto_running(directory, script, scheduler_id, gpus)
                    OUT = call(docker_command, shell=True)
                    if OUT == 0:
                        console.success("\nJob successfully finished\n")
                        exit(0)
                    else:
                        console.warning("\nJob interrupted...\n")
                        if is_unscheduled(scheduler_id):
                            console.info("unscheduled.. exiting")
                            exit(0)
                        else:
                            place_process_onto_staging(
                                directory, script, scheduler_id, settings
                            )
                else:
                    place_process_onto_staging(
                        directory, script, scheduler_id, settings
                    )
        else:
            place_process_onto_staging(directory, script, scheduler_id, settings)

        time.sleep(random.uniform(2.5, 22.5))


def get_username():
    return pwd.getpwuid(os.getuid()).pw_gecos


def sec2h(secs):
    return secs / 3600


def get_staging_processes():
    """"""
    global REPLIK_SHEDULE_STAGING_FOLDER
    procs = []
    for name in [
        f for f in listdir(REPLIK_SHEDULE_STAGING_FOLDER) if f.endswith(".json")
    ]:
        fname = join(REPLIK_SHEDULE_STAGING_FOLDER, name)
        with open(fname, "r") as f:
            proc = json.load(f)
            proc["schedule_id"] = name[:-5]

        procs.append(proc)
    procs = sorted(procs, key=lambda x: x["start_waiting_time"])
    return procs


def get_names_of_running_docker_containers():
    result = subprocess.run(
        ["docker", "ps", "--format", "'{{.Names}}'"], stdout=subprocess.PIPE
    )
    currently_running_docker_containers = set()
    for name in result.stdout.decode("utf-8").lower().split("\n"):
        if len(name) > 0:
            currently_running_docker_containers.add(name.replace("'", ""))
    return currently_running_docker_containers


def get_running_processes():
    """"""
    currently_running_docker_containers = get_names_of_running_docker_containers()

    global REPLIK_SHEDULE_FOLDER, VALID_GPU_IDS
    procs = []
    for name in [f for f in listdir(REPLIK_SHEDULE_FOLDER) if f.endswith(".json")]:
        fname = join(REPLIK_SHEDULE_FOLDER, name)
        with open(fname, "r") as f:
            proc = json.load(f)
            proc["schedule_id"] = name[:-5]

        # TODO remove the process if its NOT on the docker list
        has_been_removed = False
        if (time.time() - proc["start_time"]) > 90:
            if proc["schedule_id"] not in currently_running_docker_containers:
                # process is dead: lets remove it
                has_been_removed = True
                os.remove(fname)

        if not has_been_removed:
            procs.append(proc)
    procs = sorted(procs, key=lambda x: x["start_time"])
    return procs


def get_free_gpus():
    global VALID_GPU_IDS
    gpus = {}
    for gpuid, gpuname in VALID_GPU_IDS:
        gpus[gpuid] = False

    for running_proc in get_running_processes():
        for gpu in running_proc["gpus"]:
            assert gpu in gpus
            assert not gpus[gpu]
            gpus[gpu] = True

    free_gpus = []
    for gpuid, is_used in gpus.items():
        if not is_used:
            free_gpus.append(gpuid)
    return free_gpus


def info():
    """"""
    global REPLIK_SHEDULE_FOLDER, VALID_GPU_IDS

    gpus = {}
    for gpuid, gpuname in VALID_GPU_IDS:
        gpus[gpuid] = {"in_use": False, "elapsed_h": 0, "name": gpuname}

    console.info("[GPUs]")
    for gpuid in sorted(gpus.keys()):
        gpuname = gpus[gpuid]["name"]
        if gpus[gpuid]["in_use"]:
            console.fail(
                f"\t{gpuid} --> {gpuname} --> [in use for %.2f h]"
                % gpus[gpuid]["elapsed_h"]
            )
        else:
            console.success(f"\t{gpuid} --> {gpuname} --> [free]")

    console.info("\n[STAGING]")
    for staging_proc in get_staging_processes():
        schedule_id = staging_proc["schedule_id"]
        owner = staging_proc["owner"]
        directory = staging_proc["directory"]
        script = staging_proc["script"]
        elapsed_h = sec2h(time.time() - staging_proc["start_waiting_time"])
        n_gpus = staging_proc["settings"]["n_gpus"]
        console.write(
            f"[{schedule_id}]\t{script} <- {directory}  (@{owner})  [needs {n_gpus} gpu(s), waiting for %.2f h]"
            % elapsed_h
        )

    console.info("\n[RUNNING]")
    for running_proc in get_running_processes():
        schedule_id = running_proc["schedule_id"]
        owner = running_proc["owner"]
        directory = running_proc["directory"]
        script = running_proc["script"]
        elapsed_h = sec2h(time.time() - running_proc["start_time"])
        n_gpus = len(running_proc["gpus"])
        for gpu in running_proc["gpus"]:
            assert gpu in gpus
            assert not gpus[gpu]["in_use"]
            gpus[gpu]["in_use"] = True
            gpus[gpu]["elapsed_h"] = elapsed_h
        console.write(
            f"[{schedule_id}]\t{script} <- {directory}  (@{owner})  [{n_gpus} gpu(s) in use for %.2f h]"
            % elapsed_h
        )


def generate_id(directory, script):
    """
    each process gets a unique id
    """
    global REPLIK_SHEDULE_FOLDER
    if not isdir(REPLIK_SHEDULE_FOLDER):
        console.fail(f"Cannot schedule as path {REPLIK_SHEDULE_FOLDER} not available")
        exit(0)

    s = directory + script
    hash = str(int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16) % (10 ** 8))
    val = (hash + str(time.time()) + str(randint(0, 9))).replace(".", "_")
    return str(
        int(hashlib.sha1(("id" + hash + val).encode("utf-8")).hexdigest(), 16)
        % (10 ** 8)
    )
