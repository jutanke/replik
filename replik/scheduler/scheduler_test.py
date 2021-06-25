import unittest
import replik.scheduler.scheduler as SCHEDULER
import replik.scheduler.schedule as SCHED
from replik.scheduler.resource_monitor import ResourceMonitor
from os.path import isfile


class TestSchedulingStep(unittest.TestCase):
    def assert_is_running(self, proc):
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc.uid)))
        self.assertEqual(proc.place, SCHED.Place.RUNNING)

    def assert_is_staging(self, proc):
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc.uid)))
        self.assertEqual(proc.place, SCHED.Place.STAGING)

    def assert_is_gone(self, proc):
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc.uid)))
        self.assertEqual(proc.place, SCHED.Place.KILLED)

    def WWtest_scheduling_step(self):

        FAKE_DOCKER = {}

        def fun_docker_kill(uid):
            assert uid in FAKE_DOCKER, f"{uid} not in: " + str(FAKE_DOCKER.keys())
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

    def WWtest_scheduling_client_fails_to_run(self):

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

        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc2.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc1.uid)))

        self.assertEqual(98, len(scheduler.FREE_IDS))
        self.assertEqual(2, len(scheduler.USED_IDS))

        self.assertEqual(2, len(scheduler.STAGING_QUEUE))
        self.assertEqual(0, len(scheduler.RUNNING_QUEUE))
        for proc in scheduler.STAGING_QUEUE:
            self.assertEqual(SCHED.Place.STAGING, proc.place)

        # -- step 1 --
        scheduler.scheduling_step(running_docker_containers=[], current_time_in_s=0)
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc2.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc1.uid)))

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

    def test_full_scheduling_cycle(self):

        FAKE_DOCKER = {}

        def fun_docker_kill(uid):
            assert uid in FAKE_DOCKER, f"{uid} not in: " + str(FAKE_DOCKER.keys())
            del FAKE_DOCKER[uid]

        mon = ResourceMonitor(cpu_count=20, gpu_count=3, mem_gb=100)
        scheduler = SCHEDULER.Scheduler(
            mon, fun_docker_kill=fun_docker_kill, max_id=100
        )

        self.assertEqual(100, len(scheduler.FREE_IDS))
        self.assertEqual(0, len(scheduler.USED_IDS))

        # -- add proc1 --
        proc1 = scheduler.add_process_to_staging(
            {"cpus": 5, "gpus": 2, "memory": "10g"}, cur_time_in_s=0
        )
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc1.uid)))

        # = = = = = = = = = = = = = = = = =
        # S T E P 1
        # = = = = = = = = = = = = = = = = =
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=10)

        self.assertEqual(0, len(scheduler.STAGING_QUEUE))
        self.assertEqual(1, len(scheduler.RUNNING_QUEUE))

        # -- check proc1 --
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc1.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc1.uid)))
        FAKE_DOCKER[proc1.container_name()] = "RUNNING"

        # -- add proc2 & proc3 --
        proc2 = scheduler.add_process_to_staging(
            {"cpus": 5, "gpus": 2, "memory": "10g"}, cur_time_in_s=20
        )
        proc3 = scheduler.add_process_to_staging(
            {
                "cpus": 5,
                "gpus": 1,
                "memory": "10g",
                "minimum_required_running_hours": 2,
            },
            cur_time_in_s=30,
        )
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc2.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc3.uid)))
        self.assertEqual(2, len(scheduler.STAGING_QUEUE))
        self.assertEqual(1, len(scheduler.RUNNING_QUEUE))

        # = = = = = = = = = = = = = = = = =
        # S T E P 2
        # = = = = = = = = = = = = = = = = =
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=60)
        self.assertEqual(1, len(scheduler.STAGING_QUEUE))
        self.assertEqual(2, len(scheduler.RUNNING_QUEUE))

        # -- check proc1 & proc2 & pro3 --
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc1.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc1.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc3.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc3.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc2.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc2.uid)))
        FAKE_DOCKER[proc3.container_name()] = "RUNNING"

        # -- add proc4 & proc5 --
        proc4 = scheduler.add_process_to_staging(
            {"cpus": 5, "gpus": 1, "memory": "10g"}, cur_time_in_s=70
        )
        proc5 = scheduler.add_process_to_staging(
            {"cpus": 5, "gpus": 1, "memory": "10g"}, cur_time_in_s=80
        )
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc4.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc5.uid)))
        self.assertEqual(3, len(scheduler.STAGING_QUEUE))
        self.assertEqual(2, len(scheduler.RUNNING_QUEUE))

        # current status:
        # RUNNING: [p1, p3]
        # STAGING: [p2, p4, p5]
        # = = = = = = = = = = = = = = = = =
        # S T E P 3
        # = = = = = = = = = = = = = = = = =
        # do nothing...
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=160)
        self.assertEqual(3, len(scheduler.STAGING_QUEUE))
        self.assertEqual(2, len(scheduler.RUNNING_QUEUE))

        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc1.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc1.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc3.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc3.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc2.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc2.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc4.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc4.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc5.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc5.uid)))

        # = = = = = = = = = = = = = = = = =
        # S T E P 4
        # = = = = = = = = = = = = = = = = =
        # more than 1h has passed: lets re-schedule!
        # * p1 has to be killed and re-scheduled
        # * p3 has to remain as it is not expired yet
        # * p2 has to be scheduled!
        scheduler.scheduling_step(
            list(FAKE_DOCKER.keys()), current_time_in_s=160 + 60 * 60
        )
        self.assertEqual(3, len(scheduler.STAGING_QUEUE))
        self.assertEqual(2, len(scheduler.RUNNING_QUEUE))

        FAKE_DOCKER[proc2.container_name()] = "Running"

        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc3.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc3.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file_staging(proc2.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file(proc2.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc1.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc1.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc4.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc4.uid)))
        self.assertTrue(isfile(SCHEDULER.get_mark_file_staging(proc5.uid)))
        self.assertFalse(isfile(SCHEDULER.get_mark_file(proc5.uid)))

        # current status:
        # RUNNING: [p3, p2(2x)]
        # STAGING: [p4, p5, p1(2x)]

        # = = = = = = = = = = = = = = = = =
        # S T E P 5
        # = = = = = = = = = = = = = = = = =
        # more than 3h has passed: lets re-schedule!
        # * kill p2
        # * schedule p4, p5, keep p3
        scheduler.scheduling_step(
            list(FAKE_DOCKER.keys()), current_time_in_s=160 + 60 * 60 * 3
        )
        self.assertEqual(2, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))

        self.assert_is_staging(proc1)
        self.assert_is_staging(proc2)
        self.assert_is_running(proc3)  # is already running
        self.assert_is_running(proc4)
        FAKE_DOCKER[proc4.container_name()] = "RUNNING"
        self.assert_is_running(proc5)
        FAKE_DOCKER[proc5.container_name()] = "RUNNING"

        # = = = = = = = = = = = = = = = = =
        # S T E P 6 (do nothing)
        # = = = = = = = = = = = = = = = = =
        CUR_TIME = 300 + 60 * 60 * 3
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)
        self.assertEqual(2, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))

        self.assert_is_staging(proc1)
        self.assert_is_staging(proc2)
        self.assert_is_running(proc3)
        self.assert_is_running(proc4)
        self.assert_is_running(proc5)

        # = = = = = = = = = = = = = = = = =
        # S T E P 7 (schedule a new process)
        # = = = = = = = = = = = = = = = = =
        # current status:
        # RUNNING: [p3, p4, p5]
        # STAGING: [p1(2x), p2(2x)]
        CUR_TIME += 150
        proc6 = scheduler.add_process_to_staging(
            {"cpus": 5, "gpus": 1, "memory": "10g"}, cur_time_in_s=CUR_TIME
        )
        self.assertEqual(3, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))
        self.assert_is_staging(proc1)
        self.assert_is_staging(proc2)
        self.assert_is_staging(proc6)
        self.assert_is_running(proc3)
        self.assert_is_running(proc4)
        self.assert_is_running(proc5)

        CUR_TIME += 5
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)
        # proc3 has to be killed as we can now fit a new process onto the system
        # schedule proc6
        self.assertEqual(3, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))
        self.assert_is_staging(proc1)
        self.assert_is_staging(proc2)
        self.assert_is_staging(proc3)
        self.assert_is_running(proc4)
        self.assert_is_running(proc5)
        self.assert_is_running(proc6)
        FAKE_DOCKER[proc6.container_name()] = "RUNNING"
        # current status:
        # RUNNING: [p4, p5, p6]
        # STAGING: [p1(2x), p2(2x), p3]

        # = = = = = = = = = = = = = = = = =
        # S T E P 8 (do nothing)
        # = = = = = = = = = = = = = = = = =
        # RUNNING: [p4, p5, p6]
        # STAGING: [p1(2x), p2(2x), p3]
        CUR_TIME += 50
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)
        self.assertEqual(3, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))
        self.assert_is_staging(proc1)
        self.assert_is_staging(proc2)
        self.assert_is_staging(proc3)
        self.assert_is_running(proc4)
        self.assert_is_running(proc5)
        self.assert_is_running(proc6)

        # = = = = = = = = = = = = = = = = =
        # S T E P 9 (kill p5 & p2)
        # = = = = = = = = = = = = = = = = =
        # RUNNING: [p4, p5, p6]
        # STAGING: [p1(2x), p2(2x), p3]

        scheduler.schedule_uid_for_killing(proc5.uid)
        scheduler.schedule_uid_for_killing(proc2.uid)
        self.assertEqual(2, len(scheduler.KILLING_QUEUE))

        CUR_TIME += 50
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)

        self.assertEqual(0, len(scheduler.KILLING_QUEUE))
        self.assertEqual(1, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))
        self.assert_is_staging(proc1)
        self.assert_is_gone(proc2)
        self.assert_is_running(proc3)
        FAKE_DOCKER[proc3.container_name()] = "RUNNING"
        self.assert_is_running(proc4)
        self.assert_is_gone(proc5)
        self.assert_is_running(proc6)

        # current status
        # RUNNING: [p4, p3, p6]
        # STAGING: [p1(2x)]

        CUR_TIME += 60 * 56  # barely exceed the limit for one!
        # no re-scheduling is possible yet!
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)
        self.assertEqual(0, len(scheduler.KILLING_QUEUE))
        self.assertEqual(1, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))
        self.assert_is_staging(proc1)
        self.assert_is_running(proc3)
        self.assert_is_running(proc4)
        self.assert_is_running(proc6)

        # = = = = = = = = = = = = = = = = =
        # S T E P 10 (reshedule some)
        # = = = = = = = = = = = = = = = = =
        CUR_TIME += 60 * 3

        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)
        self.assertEqual(0, len(scheduler.KILLING_QUEUE))
        self.assertEqual(2, len(scheduler.STAGING_QUEUE))
        self.assertEqual(2, len(scheduler.RUNNING_QUEUE))
        self.assert_is_running(proc1)
        FAKE_DOCKER[proc1.container_name()] = "RUNNING"
        self.assert_is_running(proc3)
        self.assert_is_staging(proc4)
        self.assert_is_staging(proc6)

        # RUNNING: [p3, p1(2x)]
        # STAGING: [p4, p6]
        # = = = = = = = = = = = = = = = = =
        # S T E P 11 (reshedule some)
        # = = = = = = = = = = = = = = = = =
        CUR_TIME += 60 * 3

        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)
        # for proc, _ in scheduler.RUNNING_QUEUE:
        #     print(proc.running_time_in_h(CUR_TIME), proc.may_be_killed(CUR_TIME))
        self.assert_is_running(proc1)
        self.assert_is_running(proc3)
        self.assert_is_staging(proc4)
        self.assert_is_staging(proc6)

        # RUNNING: [p3, p1(2x)]
        # STAGING: [p4, p6]
        # = = = = = = = = = = = = = = = = =
        # S T E P 11 (reshedule some)
        # = = = = = = = = = = = = = = = = =
        CUR_TIME += 60 * 1 * 60

        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)
        self.assertEqual(0, len(scheduler.KILLING_QUEUE))
        self.assertEqual(1, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))
        # RUNNING: [p3, p4, p6]
        # STAGING: [p1(2x)]
        self.assert_is_staging(proc1)
        self.assert_is_running(proc3)
        self.assert_is_running(proc4)
        self.assert_is_running(proc6)
        FAKE_DOCKER[proc4.container_name()] = "RUNNING"
        FAKE_DOCKER[proc6.container_name()] = "RUNNING"

        # current status:
        # RUNNING: [p3, p4, p6]
        # STAGING: [p1(2x)]
        # = = = = = = = = = = = = = = = = =
        # S T E P 12 (reshedule some)
        # = = = = = = = = = = = = = = = = =
        # request to kill p6 & p1
        # p4 & p6 kill themselves before!
        # add p7(3x) and p8
        del FAKE_DOCKER[proc4.container_name()]
        del FAKE_DOCKER[proc6.container_name()]
        CUR_TIME += 60
        scheduler.schedule_uid_for_killing(proc6.uid)
        scheduler.schedule_uid_for_killing(proc1.uid)
        proc7 = scheduler.add_process_to_staging(
            {"cpus": 5, "gpus": 3, "memory": "10g"}, cur_time_in_s=CUR_TIME - 10
        )
        proc8 = scheduler.add_process_to_staging(
            {"cpus": 5, "gpus": 1, "memory": "10g"}, cur_time_in_s=CUR_TIME
        )
        self.assertEqual(2, len(scheduler.KILLING_QUEUE))
        self.assertEqual(3, len(scheduler.STAGING_QUEUE))
        self.assertEqual(3, len(scheduler.RUNNING_QUEUE))

        CUR_TIME += 5
        scheduler.scheduling_step(list(FAKE_DOCKER.keys()), current_time_in_s=CUR_TIME)
        self.assertEqual(0, len(scheduler.KILLING_QUEUE))
        self.assertEqual(2, len(scheduler.STAGING_QUEUE))
        self.assertEqual(1, len(scheduler.RUNNING_QUEUE))

        self.assert_is_gone(proc1)
        self.assert_is_staging(proc3)
        self.assert_is_gone(proc4)
        self.assert_is_gone(proc6)
        self.assert_is_running(proc7)
        self.assert_is_staging(proc8)

        # print_running_queue(scheduler, CUR_TIME)


def print_running_queue(scheduler, CUR_TIME):
    for proc, gpus in scheduler.RUNNING_QUEUE:
        print(
            f"{proc.uid} -> {proc.may_be_killed(CUR_TIME)} ({proc.running_time_in_h(CUR_TIME)}), {gpus}"
        )


if __name__ == "__main__":
    unittest.main()
