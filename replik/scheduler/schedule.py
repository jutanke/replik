import sys
import json
import time
import replik.console as console
import replik.scheduler.client as client
import replik.constants as const
import replik.run as RUN
import replik.build as build
from typing import List
from replik.scheduler.resource_monitor import Resources
from os.path import isfile
from subprocess import call
from enum import IntEnum


class Place:
    NOT_PLACED = 0
    STAGING = 1
    RUNNING = 2
    KILLED = 3  # this will be gc'd soon!


def get_container_name(uid):
    return "replik_%08d" % uid


class ReplikProcess:
    def __init__(self, info, uid):
        super().__init__()
        self.info = info
        self.uid = uid
        # self.uid = "replik_%04d" % uid
        self.is_running = False
        self.minimum_required_running_hours = (
            info["minimum_required_running_hours"]
            if "minimum_required_running_hours" in info
            else 1
        )
        self.maximal_running_hours = (
            info["maximal_running_hours"] if "maximal_running_hours" in info else 12
        )
        self.staging_started_time = -1
        self.running_started_time = -1
        self.resources = Resources(info)
        self.place = Place.NOT_PLACED

    def container_name(self):
        return get_container_name(self.uid)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        uid = self.uid
        return f"[{uid}, " + str(self.resources) + "]"

    def running_time_in_h(self, cur_time_in_s=None):
        return self.running_time_in_s(cur_time_in_s) / 3600

    def running_time_in_s(self, cur_time_in_s=None):
        if cur_time_in_s is None:
            cur_time_in_s = time.time()
        assert self.place == Place.RUNNING
        running_time_in_s = cur_time_in_s - self.running_started_time
        return running_time_in_s

    def waiting_time_in_h(self, cur_time_in_s=None):
        if cur_time_in_s is None:
            cur_time_in_s = time.time()
        assert self.place == Place.STAGING
        waiting_time_in_s = cur_time_in_s - self.staging_started_time
        return waiting_time_in_s / 3600

    def push_to_running_queue(self, cur_time_in_s=None):
        if cur_time_in_s is None:
            cur_time_in_s = time.time()
        assert self.place != Place.RUNNING, "place: " + str(self.place)
        self.place = Place.RUNNING
        self.running_started_time = cur_time_in_s
        self.staging_started_time = -1

    def push_to_staging_queue(self, cur_time_in_s=None):
        if cur_time_in_s is None:
            cur_time_in_s = time.time()
        assert self.place != Place.STAGING
        self.place = Place.STAGING
        self.staging_started_time = cur_time_in_s
        self.running_started_time = -1

    def push_to_kill(self):
        self.running_started_time = -1
        self.staging_started_time = -1
        self.place = Place.KILLED

    def must_be_killed(self, cur_time_in_s=None):
        currently_running_h = self.running_time_in_h(cur_time_in_s)
        return currently_running_h > self.maximal_running_hours

    def may_be_killed(self, cur_time_in_s=None):
        currently_running_h = self.running_time_in_h(cur_time_in_s)
        return currently_running_h > self.minimum_required_running_hours


def rank_processes_that_can_be_killed(
    running_processes: List[ReplikProcess], current_time_in_s: None
) -> List[ReplikProcess]:
    """returns all processes that may be killed!"""
    must_be_killed = []
    may_be_killed = []

    for proc in running_processes:
        if proc.must_be_killed(current_time_in_s):
            must_be_killed.append(proc)
        elif proc.may_be_killed(current_time_in_s):
            may_be_killed.append(proc)

    must_be_killed = list(
        sorted(must_be_killed, key=lambda p: p.running_time_in_h(current_time_in_s))
    )
    may_be_killed = list(
        sorted(may_be_killed, key=lambda p: p.running_time_in_h(current_time_in_s))
    )

    return must_be_killed + may_be_killed


def execute(directory: str, script: str, final_docker_exec_command: str):
    if const.is_replik_project(directory):
        # -- build the dockerfile --
        info = const.get_replik_settings(directory)
        build.execute(directory, script, info)

        # -- start actual scheduling --

        console.info("start scheduling...")

        if not client.check_server_status():
            console.fail("exiting")
            sys.exit(1)

        info = const.get_replik_settings(directory)
        tag = info["tag"]
        uid, mark_file = client.request_uid(info)

        console.info(f"schedule as {uid}")

        while True:
            time.sleep(3)
            if isfile(mark_file):
                # if the file exists the server allowed the scheduling!
                with open(mark_file, "r") as f:
                    mark = json.load(f)
                    gpus = mark["gpus"]

                docker_exec_command = "docker run" + RUN.set_shm_cpu_memory(info)
                if len(gpus) > 0:
                    docker_exec_command += '--gpus  "device='
                    for i, gpuid in enumerate(gpus):
                        if i > 0:
                            docker_exec_command += ","
                        docker_exec_command += str(gpuid)
                    docker_exec_command += '" '

                docker_exec_command += RUN.set_all_paths(directory, info)
                docker_exec_command += f"--rm -it {tag} " + final_docker_exec_command

                out = call(docker_exec_command, shell=True)
                if out == 0:
                    console.success(f"finished {uid}!")
                    exit(0)

        # client.request_scheduling(uid, info)
    else:
        console.warning("Not a valid replik repository")
