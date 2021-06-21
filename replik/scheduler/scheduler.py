import threading
import replik.scheduler.docker as docker
from replik.scheduler.schedule import ReplikProcess
from replik.scheduler.resource_monitor import (
    ResourceMonitor,
    get_system_cpu_count,
    get_system_memory_gb,
)
from typing import List


def get_mark_file(uid):
    return join(const.running_files_dir_for_scheduler(), f"{uid}.json")


def mark_uid_as_running(uid, gpus):
    fname = get_mark_file(uid)
    assert not isfile(fname), fname
    with open(fname, "w") as f:
        json.dump({"start_time": time.time(), "gpus": gpus}, f)


def get_uid_running_mark_elapsed(uid):
    fname = get_mark_file(uid)
    assert isfile(fname), fname
    with open(fname, "r") as f:
        start = json.load(f)["start_time"]
    return time.time() - start


def unmark_uid_as_running(uid):
    fname = get_mark_file(uid)
    assert isfile(fname), fname
    remove(fname)


class Scheduler:
    def __init__(
        self,
        resources: ResourceMonitor,
        max_id: int = 9999,
        verbose: bool = False,
        fun_docker_kill=docker.kill,
    ):
        """
        :param fun_docker_kill: {function} to kill a docker container
        """
        super().__init__()
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
                if proc.uid not in running_docker_containers:
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
        while len(KILLING_QUEUE) > 0:
            uid = KILLING_QUEUE.pop()

            # (2.1) check if the requested process is only in staging
            is_removed_from_staging = False
            for i in range(len(STAGING_QUEUE)):
                proc = STAGING_QUEUE[i]
                if proc.uid == uid:
                    STAGING_QUEUE.pop(i)
                    is_removed_from_staging = True
                    if self.verbose:
                        console.info(f"\tremove {proc.uid} from staging")
                    break

            if not is_removed_from_staging:
                # (2.2) process-to-be-killed is not found in staging
                # we have to kill it properly
                if uid in running_docker_containers:
                    self.fun_docker_kill(uid)
                    unmark_uid_as_running(proc.uid)
                    self.resources.remove_process(proc)
                    if self.verbose:
                        console.info(f"\tremove {proc.uid} from running")

        self.lock.release()

    def create_new_process(self, info):
        """"""
        uid = self.get_next_free_uid()
        return ReplikProcess(info, uid)

    def get_next_free_uid(self):
        """"""
        self.lock.acquire()

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
        self.lock.release()
        return uid

    def add_process_to_staging(self, proc: ReplikProcess):
        """this is being called from different threads!"""
        self.lock.acquire()
        try:
            self.STAGING_QUEUE.append(proc)
            proc.push_to_staging_queue()
        except:
            pass
        self.lock.release()