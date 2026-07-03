import json
import os
from typing import Any, Dict, Set

def get_generator_models(root: str) -> Set[str]:
    models: Set[str] = set()
    
    def scan_semantic_jobs(dir_path: str):
        if not os.path.isdir(dir_path):
            return
        for filename in os.listdir(dir_path):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(dir_path, filename)
            try:
                with open(path, encoding="utf-8") as f:
                    job = json.load(f)
                if not isinstance(job, dict):
                    continue
                
                model = job.get("model")
                if model:
                    models.add(str(model))
            except Exception:
                pass
                
    scan_semantic_jobs(os.path.join(root, "语义任务"))
    scan_semantic_jobs(os.path.join(root, "写作任务"))
    
    return models

