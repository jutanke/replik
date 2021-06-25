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
from replik.scheduler.scheduler import Scheduler, get_mark_file, get_mark_file_staging
import replik.scheduler.docker as docker
from os.path import isfile, join
from os import remove, makedirs
import shutil


class SchedulingThread(threading.Thread):
    def __init__(self, scheduler: Scheduler):
        super().__init__()
        self.scheduler = scheduler
        self.start()

    def run(self):
        """
        handling the entire scheduling process
        """
        global STAGING_QUEUE, RUNNING_QUEUE

        while True:
            time.sleep(5)
            current_docker_containers = docker.get_running_container_names()
            self.scheduler.scheduling_step(current_docker_containers)


def server(n_gpus: int):
    global FREE_IDS, KILLING_QUEUE, STAGING_QUEUE, RUNNING_QUEUE, USED_IDS
    console.info("\n* * * START REPLIK SERVER * * *\n")

    n_cpus = get_system_cpu_count()
    n_mem = get_system_memory_gb()
    resources = ResourceMonitor(cpu_count=n_cpus, gpu_count=n_gpus, mem_gb=n_mem)

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    console.info("server is listining...")

    scheduler = Scheduler(resources, verbose=True)
    scheduling = SchedulingThread(scheduler)

    while True:
        msg = socket.recv_json()

        if MsgType.ALIVE == get_msg_type(msg):
            socket.send_json(get_is_alive_msg())
        elif MsgType.REQUEST_UID == get_msg_type(msg):
            info = msg["info"]
            proc = scheduler.add_process_to_staging(info)
            socket.send_json(
                {
                    "msg": MsgType.SEND_UID,
                    "uid": proc.uid,
                    "container_name": proc.container_name(),
                    "mark": get_mark_file(proc.uid),
                    "staging_mark": get_mark_file_staging(proc.uid),
                }
            )
        elif MsgType.REQUEST_MURDER == get_msg_type(msg):
            uid = msg["uid"]
            scheduler.schedule_uid_for_killing(uid)
            socket.send_json(get_is_alive_msg())
        elif MsgType.REQUEST_STATUS == get_msg_type(msg):
            socket.send_json(
                {
                    "msg": MsgType.RESPOND_STATUS,
                    "status": scheduler.get_resources_infos_as_json(),
                }
            )


if __name__ == "__main__":
    n_gpus = 0
    if len(sys.argv) == 2:
        n_gpus = int(sys.argv[1])

    server(n_gpus)
