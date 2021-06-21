import sys
import time
import zmq
import json
import replik.console as console
import replik.constants as const
from replik.scheduler.message import MsgType, get_msg_type, get_is_alive_msg
from replik.scheduler.schedule import ReplikProcess, rank_processes_that_can_be_killed
import threading
from replik.scheduler.resource_monitor import (
    ResourceMonitor,
    get_system_cpu_count,
    get_system_memory_gb,
)
from replik.scheduler.scheduler import Scheduler
import replik.scheduler.docker as docker
from os.path import isfile, join
from os import remove, makedirs
import shutil


class SchedulingThread(threading.Thread):
    def __init__(self, resources: ResourceMonitor):
        super().__init__()
        self.resources = resources
        self.start()

    def run(self):
        """
        handling the entire scheduling process
        """
        global STAGING_QUEUE, RUNNING_QUEUE

        while True:
            time.sleep(5)

            console.write(
                f"\n|RUNNING| = {len(RUNNING_QUEUE)}, |STAGING| = {len(STAGING_QUEUE)}"
            )

            # (1) check if we have to update the running queue, e.g. if any of the currently running processes
            # have been killed
            console.info("(1) cleanup externally killed processes")
            running_docker_containers = set(docker.get_running_container_names())
            delete_indices = []
            for idx, (proc, gpus) in enumerate(RUNNING_QUEUE):
                elapsed_secs_since_schedule = proc.running_time_in_s()
                if (
                    elapsed_secs_since_schedule > 30
                ):  # before it might be that its not yet handled by the client
                    if proc.uid not in running_docker_containers:
                        console.warning(f"\tcleanup {proc.uid}")
                        # this process has been killed! Lets gracefully clean up its resources here!
                        self.resources.remove_process(proc)
                        delete_indices.append(idx)
                        unmark_uid_as_running(proc.uid)
            for index in sorted(delete_indices, reverse=True):
                del RUNNING_QUEUE[index]

            # (2) kill processes that are requested to be killed
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
                        console.info(f"\tremove {proc.uid} from staging")
                        break

                if not is_removed_from_staging:
                    # (2.2) process-to-be-killed is not found in staging
                    # we have to kill it properly
                    if uid in running_docker_containers:
                        docker.kill(uid)
                        unmark_uid_as_running(proc.uid)
                        self.resources.remove_process(proc)
                        console.info(f"\tremove {proc.uid} from running")

            # (3) find which processes to kill and which ones to schedule
            console.info("(3) scheduling")
            procs_to_be_killed = rank_processes_that_can_be_killed(
                [t[0] for t in RUNNING_QUEUE]
            )

            (
                procs_to_actually_kill,
                procs_to_schedule,
            ) = self.resources.schedule_appropriate_resources(
                procs_to_be_killed, STAGING_QUEUE
            )

            # murder all the requested processes
            for proc in procs_to_actually_kill:
                docker.kill(proc.uid)
                unmark_uid_as_running(proc.uid)
                self.resources.remove_process(proc)
                console.warning(f"\tkill {proc.uid}")
                # STAGING_QUEUE.append(proc)  # re-schedule
                to_staging(proc)

            # cleanup the running queue
            uid2idx = {}
            for i, (proc, _) in enumerate(RUNNING_QUEUE):
                uid2idx[proc.uid] = i
            delete_indices = [uid2idx[p.uid] for p in procs_to_actually_kill]
            for index in sorted(delete_indices, reverse=True):
                del RUNNING_QUEUE[index]

            # start all the other processes
            for proc, gpus in procs_to_schedule:
                self.resources.add_process(proc, gpus)
                mark_uid_as_running(proc.uid, gpus)
                RUNNING_QUEUE.append((proc, gpus))
                proc.push_to_running_queue()
                console.success(f"\tschedule {proc.uid}")

            # cleanup the staging queue
            uid2idx = {}
            for idx, proc in enumerate(STAGING_QUEUE):
                uid2idx[proc.uid] = idx
            delete_indices = [uid2idx[p.uid] for p, _ in procs_to_schedule]
            for index in sorted(delete_indices, reverse=True):
                del STAGING_QUEUE[index]


def to_staging(proc):
    global STAGING_QUEUE
    STAGING_QUEUE.append(proc)
    proc.push_to_staging_queue()


# USED_IDS = []
# FREE_IDS = list(range(9999))
# KILLING_QUEUE = (
#     []
# )  # anything here is supposed to be killed! [R/W] for {Comm} and {Sched}. Contains uid's
# STAGING_QUEUE = (
#     []  # [{proc}]
# )  # anything here is supposed to be staged [R/W] for {Comm} and {Sched}. Contains procs
# RUNNING_QUEUE = (
#     []  # [{proc}, {gpus}, {time}]
# )  # currently running processes, READONLY for {Comm}, [R/W] for {Sched}. Contains (procs, gpus)


def server(n_gpus: int):
    global FREE_IDS, KILLING_QUEUE, STAGING_QUEUE, RUNNING_QUEUE, USED_IDS
    console.info("\n* * * START REPLIK SERVER * * *\n")

    # -- empty the handing dir --
    shutil.rmtree(const.running_files_dir_for_scheduler())
    makedirs(const.running_files_dir_for_scheduler())
    # --

    n_cpus = get_system_cpu_count()
    n_mem = get_system_memory_gb()
    resources = ResourceMonitor(cpu_count=n_cpus, gpu_count=n_gpus, mem_gb=n_mem)

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    console.info("server is listining...")

    scheduler = Scheduler()
    scheduling = SchedulingThread(resources)

    while True:
        msg = socket.recv_json()

        if MsgType.ALIVE == get_msg_type(msg):
            socket.send_json(get_is_alive_msg())
        elif MsgType.REQUEST_UID == get_msg_type(msg):
            info = msg["info"]
            proc = scheduler.create_new_process(info)
            socket.send_json(
                {"msg": MsgType.SEND_UID, "uid": proc.uid, "mark": get_mark_file(uid)}
            )
            scheduler.add_process_to_staging(proc)

        print(msg)


if __name__ == "__main__":
    n_gpus = 0
    if len(sys.argv) == 2:
        n_gpus = int(sys.argv[1])

    server(n_gpus)
