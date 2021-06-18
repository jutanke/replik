import replik.console as console
import replik.scheduler.client as client
import replik.constants as const
from typing import List
from replik.scheduler.resource_monitor import Resources


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
        self.total_running_time_s = 0
        self.current_running_time_s = 0
        self.current_waiting_time_s = 0
        self.total_waiting_time_s = 0
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

    def total_waiting_time_in_h(self):
        return self.total_waiting_time_s / 3600

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


def execute(directory: str):
    if not client.check_server_status():
        exit(0)

    uid = client.request_uid()
    info = const.get_replik_settings(directory)

    client.request_scheduling(uid, info)
