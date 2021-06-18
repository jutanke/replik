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


class ReplikProcess:
    def __init__(self, info, uid):
        super().__init__()
        self.info = info
        self.uid = uid
        self.is_running = False
        self.minimum_required_running_hours = info["minimum_required_running_hours"]
        self.maximal_running_hours = (
            info["maximal_running_hours"] if "maximal_running_hours" in info else 12
        )
        self.current_running_time_s = 0
        self.current_waiting_time_s = 0
        self.resources = Resources(info)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        uid = self.uid
        runt = self.running_time_in_h()
        waitt = self.waiting_time_in_h()
        return f"({uid}, running for %04.02fh, waiting for %04.02fh)" % (runt, waitt)

    def running_time_in_h(self):
        return self.current_running_time_s / 3600

    def waiting_time_in_h(self):
        return self.current_waiting_time_s / 3600

    def must_be_killed(self):
        currently_running_h = self.running_time_in_h()
        return currently_running_h > self.maximal_running_hours

    def may_be_killed(self):
        currently_running_h = self.running_time_in_h()
        return currently_running_h > self.minimum_required_running_hours


def rank_processes_that_can_be_killed(
    running_processes: List[ReplikProcess],
) -> List[ReplikProcess]:
    """returns all processes that may be killed!"""
    must_be_killed = []
    may_be_killed = []

    for proc in running_processes:
        if proc.must_be_killed():
            must_be_killed.append(proc)
        elif proc.may_be_killed():
            may_be_killed.append(proc)

    must_be_killed = list(
        sorted(must_be_killed, key=lambda p: p.current_running_time_s)
    )
    may_be_killed = list(sorted(may_be_killed, key=lambda p: p.current_running_time_s))

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
