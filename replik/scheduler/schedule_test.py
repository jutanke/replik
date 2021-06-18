import unittest
import replik.scheduler.schedule as SCHED


class TestScheduling(unittest.TestCase):
    def test_rank_running(self):

        proc1 = SCHED.ReplikProcess(
            info={
                "cpus": "8",
                "memory": "16g",
                "gpus": "0",
                "minimum_required_running_hours": 1,
            },
            uid="00001",
        )
        proc1.current_running_time_s = 10000

        proc2 = SCHED.ReplikProcess(
            info={
                "cpus": "8",
                "memory": "16g",
                "gpus": "1",
                "minimum_required_running_hours": 1,
            },
            uid="00002",
        )
        proc2.current_running_time_s = 1000

        proc3 = SCHED.ReplikProcess(
            info={
                "cpus": "8",
                "memory": "16g",
                "gpus": "1",
                "minimum_required_running_hours": 1,
            },
            uid="00003",
        )
        proc3.current_running_time_s = 100

        running_processes = [proc1, proc2, proc3]

        kill_proc = SCHED.rank_processes_that_can_be_killed(running_processes)
        self.assertEqual(len(kill_proc), 1)
        self.assertEqual(kill_proc[0].uid, "00001")


if __name__ == "__main__":
    unittest.main()