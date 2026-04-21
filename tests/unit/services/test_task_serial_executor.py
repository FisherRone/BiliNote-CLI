import threading
import time
import unittest

from app.services.serial_executor import SerialTaskExecutor


class TestTaskSerialExecutor(unittest.TestCase):
    def test_executor_runs_tasks_one_by_one(self):
        executor = SerialTaskExecutor()
        state_lock = threading.Lock()
        state = {"active": 0, "peak_active": 0}

        def critical_work():
            with state_lock:
                state["active"] += 1
                state["peak_active"] = max(state["peak_active"], state["active"])
            time.sleep(0.05)
            with state_lock:
                state["active"] -= 1

        threads = [threading.Thread(target=lambda: executor.run(critical_work)) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(state["peak_active"], 1)


if __name__ == "__main__":
    unittest.main()
