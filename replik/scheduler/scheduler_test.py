import unittest
import replik.scheduler.scheduler as SCHEDULER
import replik.scheduler.schedule as SCHED
from replik.scheduler.resource_monitor import ResourceMonitor
from os.path import isfile


class TestSchedulingStep(unittest.TestCase):
    def test_scheduling_step(self):

        FAKE_DOCKER = {}

        def fun_docker_kill(uid):
            assert uid in FAKE_DOCKER
            del FAKE_DOCKER[uid]

        mon = ResourceMonitor(cpu_count=5, gpu_count=5, mem_gb=100)
        scheduler = SCHEDULER.Scheduler(
            mon, fun_docker_kill=fun_docker_kill, max_id=100
        )

        self.assertEqual(100, len(scheduler.FREE_IDS))
        self.assertEqual(0, len(scheduler.USED_IDS))

        proc1 = scheduler.add_process_to_staging(
            {"cpus": 1, "gpus": 1, "memory": "10g"}, cur_time_in_s=0
        )
        self.assertEqual(99, len(scheduler.FREE_IDS))
        self.assertEqual(1, len(scheduler.USED_IDS))

        proc2 = scheduler.add_process_to_staging(
            {"cpus": 1, "gpus": 1, "memory": "10g"}, cur_time_in_s=0
        )
        self.assertEqual(98, len(scheduler.FREE_IDS))
        self.assertEqual(2, len(scheduler.USED_IDS))

        self.assertEqual(2, len(scheduler.STAGING_QUEUE))
        self.assertEqual(0, len(scheduler.RUNNING_QUEUE))
        for proc in scheduler.STAGING_QUEUE:
            self.assertEqual(SCHED.Place.STAGING, proc.place)

        scheduler.scheduling_step(running_docker_containers=[], current_time_in_s=0)

        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc1.uid)))
        FAKE_DOCKER[proc1.container_name()] = "running"
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc2.uid)))
        FAKE_DOCKER[proc2.container_name()] = "running"

        self.assertEqual(0, len(scheduler.STAGING_QUEUE))
        self.assertEqual(2, len(scheduler.RUNNING_QUEUE))

        for proc, gpus in scheduler.RUNNING_QUEUE:
            self.assertEqual(SCHED.Place.RUNNING, proc.place)

    def test_scheduling_client_fails_to_run(self):

        FAKE_DOCKER = {}

        def fun_docker_kill(uid):
            assert uid in FAKE_DOCKER
            del FAKE_DOCKER[uid]

        mon = ResourceMonitor(cpu_count=5, gpu_count=5, mem_gb=100)
        scheduler = SCHEDULER.Scheduler(
            mon, fun_docker_kill=fun_docker_kill, max_id=100
        )

        self.assertEqual(100, len(scheduler.FREE_IDS))
        self.assertEqual(0, len(scheduler.USED_IDS))

        proc1 = scheduler.add_process_to_staging(
            {"cpus": 1, "gpus": 1, "memory": "10g"}
        )
        self.assertEqual(99, len(scheduler.FREE_IDS))
        self.assertEqual(1, len(scheduler.USED_IDS))

        proc2 = scheduler.add_process_to_staging(
            {"cpus": 1, "gpus": 1, "memory": "10g"}
        )
        self.assertEqual(98, len(scheduler.FREE_IDS))
        self.assertEqual(2, len(scheduler.USED_IDS))

        self.assertEqual(2, len(scheduler.STAGING_QUEUE))
        self.assertEqual(0, len(scheduler.RUNNING_QUEUE))
        for proc in scheduler.STAGING_QUEUE:
            self.assertEqual(SCHED.Place.STAGING, proc.place)

        # -- step 1 --
        scheduler.scheduling_step(running_docker_containers=[], current_time_in_s=0)

        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc1.uid)))
        # proc1 does "crash" and is not scheduled!
        # This has to be picked-up in the next scheduling step!
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc2.uid)))
        FAKE_DOCKER[proc2.container_name()] = "running"

        self.assertEqual(0, len(scheduler.STAGING_QUEUE))
        self.assertEqual(2, len(scheduler.RUNNING_QUEUE))

        # -- step 2 --
        cnt = list(FAKE_DOCKER.keys())
        scheduler.scheduling_step(running_docker_containers=cnt, current_time_in_s=60)
        for proc, gpus in scheduler.RUNNING_QUEUE:
            self.assertEqual(SCHED.Place.RUNNING, proc.place)

        self.assertEqual(0, len(scheduler.STAGING_QUEUE))
        self.assertEqual(1, len(scheduler.RUNNING_QUEUE))

        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc2.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc1.uid)))

        # -- step 3 --
        scheduler.schedule_uid_for_killing(proc2.container_name())
        cnt = list(FAKE_DOCKER.keys())
        scheduler.scheduling_step(running_docker_containers=cnt, current_time_in_s=120)

        self.assertEqual(0, len(scheduler.STAGING_QUEUE))
        self.assertEqual(0, len(scheduler.RUNNING_QUEUE))
        self.assertEqual(0, len(scheduler.KILLING_QUEUE))


if __name__ == "__main__":
    unittest.main()
