import unittest
from ClarityTasks import Task

class TestTask(unittest.TestCase):
    def test_overdue(self):
        t = Task(title="Demo", done=False, due="2000-01-01")
        self.assertTrue(t.is_overdue())

if __name__ == "__main__":
    unittest.main()
