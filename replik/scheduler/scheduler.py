import threading
import json
import replik.scheduler.docker as docker
import replik.constants as const
from replik.scheduler.schedule import ReplikProcess, rank_processes_that_can_be_killed
from replik.scheduler.resource_monitor import (
    ResourceMonitor,
    get_system_cpu_count,
    get_system_memory_gb,
)
from typing import List
from os.path import join, isfile
from os import remove, makedirs
import shutil
import time


def get_mark_file(uid):
    return join(const.running_files_dir_for_scheduler(), f"{uid}.json")


def mark_uid_as_running(uid, gpus, current_time_in_s=None):
    if current_time_in_s is None:
        current_time_in_s = time.time()
    fname = get_mark_file(uid)
    assert not isfile(fname), fname
    with open(fname, "w") as f:
        json.dump({"start_time": current_time_in_s, "gpus": gpus}, f)


def get_uid_running_mark_elapsed(uid, current_time_in_s=None):
    if current_time_in_s is None:
        current_time_in_s = time.time()
    fname = get_mark_file(uid)
    assert isfile(fname), fname
    with open(fname, "r") as f:
        start = json.load(f)["start_time"]
    return current_time_in_s - start


def unmark_uid_as_running(uid):
    fname = get_mark_file(uid)
    assert isfile(fname), fname
    remove(fname)


class Scheduler:
    def __init__(
        self,
        resources: ResourceMonitor,
        max_id: int = 10000,
        verbose: bool = False,
        fun_docker_kill=docker.kill,
    ):
        """
        :param fun_docker_kill: {function} to kill a docker container
        """
        super().__init__()
        # -- empty the handing dir --
        shutil.rmtree(const.running_files_dir_for_scheduler())
        makedirs(const.running_files_dir_for_scheduler())
        # --

        self.lock = threading.Lock()
        self.verbose = verbose
        self.resources = resources
        self.fun_docker_kill = fun_docker_kill

        self.USED_IDS = []
        self.FREE_IDS = list(range(max_id))
        self.KILLING_QUEUE = (
            []
        )  # anything here is supposed to be killed! [R/W] for {Comm} and {Sched}. Contains uid's
        self.STAGING_QUEUE = (
            []  # [{proc}]
        )  # anything here is supposed to be staged [R/W] for {Comm} and {Sched}. Contains procs
        self.RUNNING_QUEUE = (
            []  # [{proc}, {gpus}]
        )  # currently running processes, READONLY for {Comm}, [R/W] for {Sched}. Contains (procs, gpus)

    def scheduling_step(
        self, running_docker_containers: List[str], current_time_in_s=None
    ):
        """
        :param running_docker_containers: list of names of current docker containers
        :param current_time_in_s: for unit testing
        """
        self.lock.acquire()
        if current_time_in_s is None:
            current_time_in_s = time.time()

        # (1) check if we have to update the running queue, e.g. if any of the currently running processes
        # have been killed
        if self.verbose:
            console.info("(1) cleanup externally killed processes")
        delete_indices = []
        for idx, (proc, gpus) in enumerate(self.RUNNING_QUEUE):
            elapsed_secs_since_schedule = proc.running_time_in_s(current_time_in_s)
            if (
                elapsed_secs_since_schedule > 30
            ):  # before it might be that its not yet handled by the client
                if proc.container_name() not in running_docker_containers:
                    if self.verbose:
                        console.warning(f"\tcleanup {proc.uid}")
                    # this process has been killed! Lets gracefully clean up its resources here!
                    self.resources.remove_process(proc)
                    delete_indices.append(idx)
                    unmark_uid_as_running(proc.uid)
        for index in sorted(delete_indices, reverse=True):
            del self.RUNNING_QUEUE[index]

        # (2) kill processes that are requested to be killed
        if self.verbose:
            console.info("(2) kill processes that are scheduled to be killed")
        while len(self.KILLING_QUEUE) > 0:
            uid = self.KILLING_QUEUE.pop()

            # (2.1) check if the requested process is only in staging
            is_removed_from_staging = False
            for i in range(len(self.STAGING_QUEUE)):
                proc = self.STAGING_QUEUE[i]
                if proc.uid == uid:
                    self.STAGING_QUEUE.pop(i)
                    is_removed_from_staging = True
                    if self.verbose:
                        console.info(f"\tremove {proc.uid} from staging")
                    break

            if not is_removed_from_staging:
                # (2.2) process-to-be-killed is not found in staging
                # we have to kill it properly
                if uid in running_docker_containers:
                    self.kill(proc)
                    # we also have to delete this from the running queue!

        # (3) find which processes to kill and which ones to schedule
        if self.verbose:
            console.info("(3) scheduling")
        procs_to_be_killed = rank_processes_that_can_be_killed(
            [t[0] for t in self.RUNNING_QUEUE], current_time_in_s=current_time_in_s
        )

        (
            procs_to_actually_kill,
            procs_to_schedule,
            procs_to_staging,
        ) = self.resources.schedule_appropriate_resources(
            procs_to_be_killed, self.STAGING_QUEUE
        )

        # murder all the requested processes
        for proc in procs_to_actually_kill:
            self.kill(proc)

        for proc in procs_to_staging:
            self.STAGING_QUEUE.append(proc)
            proc.push_to_staging_queue()

        # cleanup the running queue
        uid2idx = {}
        for i, (proc, _) in enumerate(self.RUNNING_QUEUE):
            uid2idx[proc.uid] = i
        delete_indices = [uid2idx[p.uid] for p in procs_to_actually_kill]
        for index in sorted(delete_indices, reverse=True):
            del self.RUNNING_QUEUE[index]

        # start all the other processes
        for proc, gpus in procs_to_schedule:
            self.resources.add_process(proc, gpus)
            mark_uid_as_running(proc.uid, gpus)
            self.RUNNING_QUEUE.append((proc, gpus))
            proc.push_to_running_queue(cur_time_in_s=current_time_in_s)
            if self.verbose:
                console.success(f"\tschedule {proc.uid}")

        # cleanup the staging queue
        uid2idx = {}
        for idx, proc in enumerate(self.STAGING_QUEUE):
            uid2idx[proc.uid] = idx
        delete_indices = [uid2idx[p.uid] for p, _ in procs_to_schedule]
        for index in sorted(delete_indices, reverse=True):
            del self.STAGING_QUEUE[index]

        self.lock.release()

    def kill(self, proc):
        """kill a process"""
        assert self.lock.locked()
        self.fun_docker_kill(proc.container_name())
        unmark_uid_as_running(proc.uid)
        self.resources.remove_process(proc)
        if self.verbose:
            console.warning(f"\tkill {proc.uid}")
        idx = -1
        for i, (oproc, _) in enumerate(self.RUNNING_QUEUE):
            if oproc.uid == proc.uid:
                idx = i
                break
        assert idx > -1
        del self.RUNNING_QUEUE[idx]

    def get_next_free_uid(self):
        """"""
        assert self.lock.locked()
        # - - re-use uid's - -
        ids_still_in_use = set()
        for proc in self.STAGING_QUEUE:
            ids_still_in_use.add(proc.uid)
        for proc, _ in self.RUNNING_QUEUE:
            ids_still_in_use.add(proc.uid)

        delete_indices = []
        for i, uid in enumerate(self.USED_IDS):
            if uid not in ids_still_in_use:
                self.FREE_IDS.append(uid)
                delete_indices.append(i)
        for index in sorted(delete_indices, reverse=True):
            del self.USED_IDS[index]
        # - - - -

        uid = self.FREE_IDS.pop(0)
        self.USED_IDS.append(uid)
        return uid

    def schedule_uid_for_killing(self, uid: int):
        """"""
        self.lock.acquire()
        self.KILLING_QUEUE.append(uid)
        self.lock.release()

    def add_process_to_staging(self, info, cur_time_in_s=None):
        """this is being called from different threads!"""
        self.lock.acquire()
        try:
            uid = self.get_next_free_uid()
            proc = ReplikProcess(info, uid)
            self.STAGING_QUEUE.append(proc)
            proc.push_to_staging_queue(cur_time_in_s)
        except:
            pass
        self.lock.release()
        return proc
