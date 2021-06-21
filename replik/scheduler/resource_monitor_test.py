import unittest
import replik.scheduler.resource_monitor as RESMON
import replik.scheduler.schedule as SCHED


class TestProcesses(unittest.TestCase):
    def test_scheduling(self):
        proc1 = SCHED.ReplikProcess({"cpus": 1, "gpus": 1, "memory": "10g"}, uid=1)
        proc2 = SCHED.ReplikProcess({"cpus": 1, "gpus": 1, "memory": "10g"}, uid=2)
        proc3 = SCHED.ReplikProcess({"cpus": 1, "gpus": 3, "memory": "10g"}, uid=3)
        proc4 = SCHED.ReplikProcess({"cpus": 1, "gpus": 1, "memory": "10g"}, uid=4)
        proc5 = SCHED.ReplikProcess({"cpus": 1, "gpus": 0, "memory": "50g"}, uid=5)
        mon = RESMON.ResourceMonitor(
            cpu_count=5, gpu_count=5, mem_gb=100, memory_factor=1.0
        )
        res = mon.get_current_free_resources()
        self.assertEqual(5, res.cpu_count)
        self.assertEqual(5, res.gpu_count)
        self.assertEqual(100, res.mem_gb)

        (
            procs_to_kill,
            procs_to_schedule,
            procs_to_staging,
        ) = mon.schedule_appropriate_resources([], [proc1, proc2, proc3, proc4, proc5])
        self.assertEqual(0, len(procs_to_kill))
        self.assertEqual(1, len(procs_to_staging))
        self.assertEqual(4, len(procs_to_schedule))

        self.assertEqual(1, procs_to_schedule[0][0].uid)
        self.assertEqual(2, procs_to_schedule[1][0].uid)
        self.assertEqual(3, procs_to_schedule[2][0].uid)
        self.assertEqual(5, procs_to_schedule[3][0].uid)
        self.assertEqual(4, procs_to_staging[0].uid)

        for proc, gpus in procs_to_schedule:
            mon.add_process(proc, gpus)

        res = mon.get_current_free_resources()
        self.assertEqual(1, res.cpu_count)
        self.assertEqual(0, res.gpu_count)
        self.assertEqual(20, res.mem_gb)

        # -- remove procs from the mon
        mon.remove_process(proc1)
        res = mon.get_current_free_resources()
        self.assertEqual(2, res.cpu_count)
        self.assertEqual(1, res.gpu_count)
        self.assertEqual(30, res.mem_gb)

        mon.remove_process(proc2)
        res = mon.get_current_free_resources()
        self.assertEqual(3, res.cpu_count)
        self.assertEqual(2, res.gpu_count)
        self.assertEqual(40, res.mem_gb)

        mon.remove_process(proc3)
        res = mon.get_current_free_resources()
        self.assertEqual(4, res.cpu_count)
        self.assertEqual(5, res.gpu_count)
        self.assertEqual(50, res.mem_gb)

        mon.remove_process(proc5)
        res = mon.get_current_free_resources()
        self.assertEqual(5, res.cpu_count)
        self.assertEqual(5, res.gpu_count)
        self.assertEqual(100, res.mem_gb)


class TestResources(unittest.TestCase):
    def test_subtraction(self):
        mon = RESMON.FreeResources(cpu_count=5, gpu_count=5, mem_gb=100)
        res = RESMON.Resources({"cpus": 1, "gpus": 1, "memory": "10g"})
        for _ in range(3):
            mon = mon.subtract(res)
        self.assertEqual(mon.cpu_count, 2)
        self.assertEqual(mon.gpu_count, 2)
        self.assertEqual(mon.mem_gb, 70)

    def test_addition(self):
        mon = RESMON.FreeResources(cpu_count=5, gpu_count=5, mem_gb=100)
        res = RESMON.Resources({"cpus": 1, "gpus": 1, "memory": "10g"})
        for _ in range(3):
            mon = mon.add(res)
        self.assertEqual(mon.cpu_count, 8)
        self.assertEqual(mon.gpu_count, 8)
        self.assertEqual(mon.mem_gb, 130)

    def test_notfit(self):
        mon = RESMON.FreeResources(cpu_count=5, gpu_count=5, mem_gb=100)
        res1 = RESMON.Resources({"cpus": 8, "gpus": 1, "memory": "10g"})
        self.assertFalse(mon.fits(res1))
        res2 = RESMON.Resources({"cpus": 1, "gpus": 6, "memory": "10g"})
        self.assertFalse(mon.fits(res2))
        res3 = RESMON.Resources({"cpus": 1, "gpus": 1, "memory": "101g"})
        self.assertFalse(mon.fits(res3))

    def test_fit(self):
        mon = RESMON.FreeResources(cpu_count=5, gpu_count=5, mem_gb=100)
        res1 = RESMON.Resources({"cpus": 4, "gpus": 1, "memory": "10g"})
        self.assertTrue(mon.fits(res1))
        res2 = RESMON.Resources({"cpus": 1, "gpus": 4, "memory": "10g"})
        self.assertTrue(mon.fits(res2))
        res3 = RESMON.Resources({"cpus": 1, "gpus": 1, "memory": "99g"})
        self.assertTrue(mon.fits(res3))


if __name__ == "__main__":
    unittest.main()