import threading
import json
import replik.scheduler.docker as docker
import replik.constants as const
import replik.console as console
from replik.scheduler.schedule import (
    ReplikProcess,
    rank_processes_that_can_be_killed,
    get_container_name,
    Place,
)
from replik.scheduler.resource_monitor import (
    ResourceMonitor,
    get_system_cpu_count,
    get_system_memory_gb,
)
from typing import List
from os.path import join, isfile
from os import remove, makedirs, listdir
import shutil
import time


def get_mark_file(uid):
    return join(const.running_files_dir_for_scheduler(), "%09d.json" % uid)


def get_mark_file_staging(uid):
    return join(const.staging_files_dir_for_scheduler(), "%09d.json" % uid)


def mark_uid_as_staging(uid, current_time_in_s=None):
    if current_time_in_s is None:
        current_time_in_s = time.time()
    fname = get_mark_file_staging(uid)
    assert not isfile(fname), fname
    with open(fname, "w") as f:
        json.dump({"start_time": current_time_in_s}, f)


def mark_uid_as_running(uid, gpus, current_time_in_s=None):
    if current_time_in_s is None:
        current_time_in_s = time.time()
    fname = get_mark_file(uid)
    assert not isfile(fname), fname
    with open(fname, "w") as f:
        json.dump({"start_time": current_time_in_s, "gpus": gpus}, f)


def get_uid_staging_mark_elapsed(uid, current_time_in_s=None):
    if current_time_in_s is None:
        current_time_in_s = time.time()
    fname = get_mark_file_staging(uid)
    assert isfile(fname), fname
    with open(fname, "r") as f:
        start = json.load(f)["start_time"]
    return current_time_in_s - start


def get_uid_running_mark_elapsed(uid, current_time_in_s=None):
    if current_time_in_s is None:
        current_time_in_s = time.time()
    fname = get_mark_file(uid)
    assert isfile(fname), fname
    with open(fname, "r") as f:
        start = json.load(f)["start_time"]
    return current_time_in_s - start


def unmark_uid_as_staging(uid):
    fname = get_mark_file_staging(uid)
    assert isfile(fname), fname
    remove(fname)


def unmark_uid_as_running(uid):
    fname = get_mark_file(uid)
    assert isfile(fname), fname
    remove(fname)


def clear_dir(directory: str):
    """delete all files in this directory"""
    for f in [join(directory, f) for f in listdir(directory) if f.endswith(".json")]:
        remove(f)


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
        clear_dir(const.running_files_dir_for_scheduler())
        clear_dir(const.staging_files_dir_for_scheduler())
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

    def get_resources_infos_as_json(self):
        """gather all the resources so that we can display them!"""
        self.lock.acquire()
        res_free = self.resources.get_current_free_resources()
        res_total = self.resources.maximal_resources
        RUN = []
        for proc, gpus in self.RUNNING_QUEUE:
            gpus = list(sorted(gpus))
            RUN.append(
                {
                    "info": proc.to_json(),
                    "gpus": gpus,
                    "running_in_h": proc.running_time_in_h(),
                }
            )
        STAG = []
        for proc in self.STAGING_QUEUE:
            STAG.append(
                {
                    "info": proc.to_json(),
                    "waiting_in_h": proc.waiting_time_in_h(),
                }
            )

        self.lock.release()

        return {
            "free": res_free.to_json(),
            "total": res_total.to_json(),
            "running": RUN,
            "staging": STAG,
        }

    def remove_from_running_queue(self, remove_procs: List[ReplikProcess]):
        """"""
        if len(remove_procs) > 0:
            delete_indices = []
            uid_is_marked_for_del = set()
            for proc in remove_procs:
                uid_is_marked_for_del.add(proc.uid)

            del_indices = []
            for idx, (proc, _) in enumerate(self.RUNNING_QUEUE):
                if proc.uid in uid_is_marked_for_del:
                    del_indices.append(idx)

            if len(del_indices) > 0:
                for index in sorted(del_indices, reverse=True):
                    del self.RUNNING_QUEUE[index]

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

        if self.verbose:
            console.info(
                f"Scheduling step, running:{len(self.RUNNING_QUEUE)}, staging:{len(self.STAGING_QUEUE)}, #free ids:{len(self.FREE_IDS)}"
            )

        # (1) check if we have to update the running queue, e.g. if any of the currently running processes
        # have been killed
        delete_procs = []
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
                    delete_procs.append(proc)
                    unmark_uid_as_running(proc.uid)
                    proc.push_to_kill()

        self.remove_from_running_queue(delete_procs)

        # (2) kill processes that are requested to be killed
        delete_procs_from_running = []

        already_killed_uid = set()  # make sure we don't kill duplicates
        while len(self.KILLING_QUEUE) > 0:
            uid = self.KILLING_QUEUE.pop()
            if uid in already_killed_uid:
                continue
            already_killed_uid.add(uid)

            container_name = get_container_name(uid)

            # (2.1) check if the requested process is only in staging
            is_removed_from_staging = False
            for i in range(len(self.STAGING_QUEUE)):
                proc = self.STAGING_QUEUE[i]
                if proc.uid == uid:
                    self.STAGING_QUEUE.pop(i)
                    unmark_uid_as_staging(proc.uid)
                    proc.push_to_kill()
                    is_removed_from_staging = True
                    if self.verbose:
                        console.info(f"\tremove {proc.uid} from staging")
                    break

            if not is_removed_from_staging:
                # (2.2) process-to-be-killed is not found in staging
                # we have to kill it properly
                for proc, _ in self.RUNNING_QUEUE:
                    if proc.uid == uid and container_name in running_docker_containers:
                        self.kill(proc)
                        proc.push_to_kill()
                        delete_procs_from_running.append(proc)
                        break

        self.remove_from_running_queue(delete_procs_from_running)

        # (3) find which processes to kill and which ones to schedule
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

        # it is important that we mark all the processes that we gonna
        # kill for staging BEFORE we kill them so that they know that
        # they have to re-schedule!
        for proc in procs_to_staging:
            self.STAGING_QUEUE.append(proc)
            get_mark_file_staging(proc.uid)  # re-schedule!
            proc.push_to_staging_queue(cur_time_in_s=current_time_in_s)

        # murder all the requested processes
        for proc in procs_to_actually_kill:
            self.kill(proc)

        self.remove_from_running_queue(procs_to_actually_kill)

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

        # cleanup the staging folder
        self.sync_staging_dir_with_staging_queue(current_time_in_s)

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

    def sync_staging_dir_with_staging_queue(self, cur_time_in_s):
        """"""
        assert self.lock.locked()
        valid_uids = {}  # (uid -> has_a_staging_file?)
        for proc in self.STAGING_QUEUE:
            assert proc.uid not in valid_uids
            valid_uids[proc.uid] = False
        all_files = {}
        for uid in [
            int(f[:9])
            for f in listdir(const.staging_files_dir_for_scheduler())
            if f.endswith(".json")
        ]:
            if uid in valid_uids:
                valid_uids[uid] = True
            else:
                unmark_uid_as_staging(uid)
        for uid, has_a_staging_file in valid_uids.items():
            if not has_a_staging_file:
                mark_uid_as_staging(uid, current_time_in_s=cur_time_in_s)

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

    def schedule_uid_for_killing(self, uid: int, cur_time_in_s=None):
        """"""
        self.lock.acquire()
        self.sync_staging_dir_with_staging_queue(cur_time_in_s)
        self.KILLING_QUEUE.append(uid)
        self.lock.release()

    def add_process_to_staging(self, info, cur_time_in_s=None):
        """this is being called from different threads!"""
        self.lock.acquire()
        self.sync_staging_dir_with_staging_queue(cur_time_in_s)
        try:
            uid = self.get_next_free_uid()
            proc = ReplikProcess(info, uid)
            self.STAGING_QUEUE.append(proc)
            proc.push_to_staging_queue(cur_time_in_s)
            mark_uid_as_staging(uid, cur_time_in_s)
        except:
            pass
        self.lock.release()
        return proc
