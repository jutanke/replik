import multiprocessing
from typing import List
from copy import deepcopy


def get_system_memory_gb():
    meminfo = dict(
        (i.split()[0].rstrip(":"), int(i.split()[1]))
        for i in open("/proc/meminfo").readlines()
    )
    return meminfo["MemTotal"] / 1000000


def get_system_cpu_count():
    return multiprocessing.cpu_count()


class Resources:
    def __init__(self, info):
        super().__init__()
        self.cpus = info["cpus"]
        self.gpus = info["gpus"]
        self.memory = info["memory"]


class FreeResources:
    def __init__(self, cpu_count: int, gpu_count: int, mem_gb: int):
        super().__init__()
        self.mem_gb = mem_gb
        self.cpu_count = cpu_count
        self.gpu_count = gpu_count

    def subtract(self, res: Resources):
        """
        remove the resources
        """
        mem_gb = self.mem_gb - res.memory
        n_cpu = self.cpu_count - res.cpus
        n_gpu = self.gpu_count - res.gpus
        return FreeResources(n_cpu, n_gpu, mem_gb)

    def add(self, res: Resources):
        """
        add back the resources
        """
        mem_gb = self.mem_gb + res.memory
        n_cpu = self.cpu_count + res.cpus
        n_gpu = self.gpu_count + res.gpus
        return FreeResources(n_cpu, n_gpu, mem_gb)

    def fits(self, res: Resources):
        mem_gb = self.mem_gb - res.memory
        n_cpu = self.cpu_count - res.cpus
        n_gpu = self.gpu_count - res.gpus
        return mem_gb >= 0 and n_cpu >= 0 and n_gpu >= 0


class ResourceMonitor:
    def __init__(self, cpu_count: int, gpu_count: int, mem_gb: int, memory_factor=0.80):
        """
        :param memory_factor: down-sizing factor to ensure that there's some mem left on the machine
        """
        super().__init__()

        self.maximal_resources = FreeResources(
            cpu_count=cpu_count, gpu_count=gpu_count, mem_gb=mem_gb * memory_factor
        )

        self.current_processes = {}
        self.gpus = [None] * gpu_count

    def add_process(self, process, gpus: List[int]):
        """
        This is adding the process without checking that it fits!
        This has to be taken care of before!!
        :param process: {replik.scheduler.ReplikProcess}
        """
        assert process.uid not in self.current_processes
        for gpuid in gpus:
            assert self.gpus[gpuid] == None
            self.gpus[gpuid] = process.uid
        self.current_processes[process.uid] = process

    def remove_process(self, process):
        """Remove a process"""
        assert process.uid in self.current_processes
        for gpuid in gpus:
            if self.gpus[gpuid] == process.uid:
                self.gpus[gpuid] = None
        del self.current_processes[process.uid]
        self.available_ids.append(int(process.uid))

    def get_current_free_resources(self) -> FreeResources:
        """"""
        current_res = self.maximal_resources
        for proc in self.current_processes.values():
            current_res = current_res.subtract(proc.resources)
        return current_res

    def schedule_appropriate_resources(self, unscheduling: List, staging: List):
        """
        return {procs_to_kill} ['00001', '00005'], {procs_to_schedule} [('00002', [0]), ('00003', [1, 2])]
        """
        current_res = self.get_current_free_resources()

        # (1) check the resource availabilty if we remove
        # all the 'overdue' processes. For now this is only
        # "virtual"!
        available_resources = current_res
        for proc in unscheduling:
            available_resources.add(proc.resources)

        # (2) try to schedule all processes that are in the
        # waiting queue
        procs_to_schedule = []
        for proc in staging:
            if available_resources.fits(proc.resources):
                available_resources = available_resources.subtract(proc.resources)
                procs_to_schedule.append(proc)

        # (3) check if some of the old processes still fit... if so we will
        # just let them be and let them KEEP their current GPUs!
        procs_to_kill = []
        for proc in reversed(unscheduling):
            if available_resources.fits(proc.resources):
                available_resources = available_resources.subtract(proc.resources)
            else:
                procs_to_kill.append(proc)

        # (4) clean-up the gpu assignments
        gpus = deepcopy(self.gpus)
        for proc in procs_to_kill:
            for i in range(len(gpus)):
                if gpus[i] == proc.uid:
                    gpus[i] = None

        # (5) find gpus for the newly scheduled processes
        procs_to_schedule_ = []
        for proc in procs_to_schedule:
            n_gpus = proc.resources.gpus
            proc_gpus = []
            for _ in range(n_gpus):
                for i in range(len(gpus)):
                    if gpus[i] == None:
                        gpus[i] = proc.uid
                        proc_gpus.append(i)
            assert len(proc_gpus) == n_gpus
            procs_to_schedule_.append((proc, proc_gpus))

        return procs_to_kill, procs_to_schedule_
