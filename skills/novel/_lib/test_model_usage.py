import unittest
import os
import tempfile
import json
from model_usage import get_generator_models

class TestModelUsage(unittest.TestCase):
    def test_get_generator_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs_dir = os.path.join(tmp, "语义任务")
            os.makedirs(jobs_dir)
            
            with open(os.path.join(jobs_dir, "job1.json"), "w") as f:
                json.dump({"model": "claude-3-5-sonnet"}, f)
                
            with open(os.path.join(jobs_dir, "job2.json"), "w") as f:
                json.dump({"model": "gpt-4o"}, f)
                
            with open(os.path.join(jobs_dir, "job3.json"), "w") as f:
                json.dump({}, f)
                
            models = get_generator_models(tmp)
            self.assertEqual(models, {"claude-3-5-sonnet", "gpt-4o"})

if __name__ == "__main__":
    unittest.main()

