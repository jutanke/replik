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
        proc1.push_to_running_queue(cur_time_in_s=0)

        proc2 = SCHED.ReplikProcess(
            info={
                "cpus": "8",
                "memory": "16g",
                "gpus": "1",
                "minimum_required_running_hours": 1,
            },
            uid="00002",
        )
        proc2.push_to_running_queue(cur_time_in_s=500)

        proc3 = SCHED.ReplikProcess(
            info={
                "cpus": "8",
                "memory": "16g",
                "gpus": "1",
                "minimum_required_running_hours": 1,
            },
            uid="00003",
        )
        proc3.push_to_running_queue(cur_time_in_s=1000)

        cur_time = 4000

        running_processes = [proc1, proc2, proc3]

        kill_proc = SCHED.rank_processes_that_can_be_killed(
            running_processes, current_time_in_s=cur_time
        )
        self.assertEqual(len(kill_proc), 1)
        self.assertEqual(kill_proc[0].uid, "00001")


if __name__ == "__main__":
    unittest.main()