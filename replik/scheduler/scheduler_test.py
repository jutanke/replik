import unittest
import replik.scheduler.scheduler as SCHEDULER
from replik.scheduler.resource_monitor import ResourceMonitor


class TestSchedulingStep(unittest.TestCase):
    def test_scheduling_step(self):

        FAKE_DOCKER = {}

        def fun_docker_kill(uid):
            assert uid in FAKE_DOCKER
            del FAKE_DOCKER[uid]

        # proc1 = SCHED.ReplikProcess(
        #     info={
        #         "cpus": "8",
        #         "memory": "16g",
        #         "gpus": "0",
        #         "minimum_required_running_hours": 1,
        #     },
        #     uid=-1,
        # )
        # proc2 = SCHED.ReplikProcess(
        #     info={
        #         "cpus": "8",
        #         "memory": "16g",
        #         "gpus": "0",
        #         "minimum_required_running_hours": 1,
        #     },
        #     uid=-1,
        # )

        mon = ResourceMonitor(cpu_count=5, gpu_count=5, mem_gb=100)
        scheduler = SCHEDULER.Scheduler(mon, fun_docker_kill=fun_docker_kill)

        self.assertEqual(1, 1)


if __name__ == "__main__":
    unittest.main()