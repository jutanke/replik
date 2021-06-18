import sys
import time
import zmq
import replik.console as console
from replik.scheduler.message import MsgType, get_msg_type, get_is_alive_msg
from replik.scheduler.schedule import ReplikProcess
import threading
from replik.scheduler.resource_monitor import (
    ResourceMonitor,
    get_system_cpu_count,
    get_system_memory_gb,
)
import replik.scheduler.docker as docker


class SchedulingThread(threading.Thread):
    def __init__(self, resources: ResourceMonitor):
        super().__init__()
        self.start()

    def run(self):
        """
        handling the entire scheduling process
        """
        global STAGING_QUEUE, RUNNING_QUEUE, RESOURCES

        while True:
            time.sleep(3)

            # (1) check if we have to update the running queue, e.g. if any of the currently running processes
            # have been killed
            running_docker_containers = set(docker.get_running_container_names())
            surviving = []
            for proc, gpus in RUNNING_QUEUE:
                if proc.uid in running_docker_containers:
                    surviving.append(proc)
                else:  # this process has been killed! Lets gracefully clean up its resources here!
                    RESOURCES.remove_process((proc, gpus))
            RUNNING_QUEUE = surviving  # fix the running queue

            # (2) kill processes that are requested to be killed
            while len(KILLING_QUEUE) > 0:
                uid = KILLING_QUEUE.pop()

                # (2.1) check if the requested process is only in staging
                is_killed = False
                for i in range(len(STAGING_QUEUE)):
                    proc = STAGING_QUEUE[i]
                    if proc.uid == uid:
                        STAGING_QUEUE.pop(i)
                        is_killed = True
                        break

                if not is_killed:
                    # (2.2) process-to-be-killed is not found in staging
                    # we have to kill it properly
                    if uid in running_docker_containers:
                        docker.kill(uid)


FREE_IDS = list(range(9999))
IDS_THAT_WERE_REQUESTED = {}  # id: time
KILLING_QUEUE = (
    []
)  # anything here is supposed to be killed! [R/W] for {Comm} and {Sched}. Contains uid's
STAGING_QUEUE = (
    []
)  # anything here is supposed to be staged [R/W] for {Comm} and {Sched}. Contains procs
RUNNING_QUEUE = (
    []
)  # currently running processes, READONLY for {Comm}, [R/W] for {Sched}. Contains (procs, gpus)


def server(n_gpus: int):
    global FREE_IDS, KILLING_QUEUE, STAGING_QUEUE, RUNNING_QUEUE, IDS_THAT_WERE_REQUESTED
    console.info("\n* * * START REPLIK SERVER * * *\n")

    n_cpus = get_system_cpu_count()
    n_mem = get_system_memory_gb()
    resources = ResourceMonitor(cpu_count=n_cpus, gpu_count=n_gpus, mem_gb=n_mem)

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    console.info("server is listining...")

    scheduling = SchedulingThread(resources)

    while True:
        msg = socket.recv_json()

        if MsgType.ALIVE == get_msg_type(msg):
            socket.send_json(get_is_alive_msg())
        elif MsgType.REQUEST_UID == get_msg_type(msg):
            socket.send_json({"msg": MsgType.SEND_UID, "uid": FREE_IDS.pop(0)})
        elif MsgType.SEND_PROCESS == get_msg_type(msg):

            # proc = ReplikProcess(info, )
            socket.send_json(get_is_alive_msg())

        print(msg)

        # exit(0)


if __name__ == "__main__":
    n_gpus = 0
    if len(sys.argv) == 2:
        n_gpus = int(sys.argv[1])

    server(n_gpus)
