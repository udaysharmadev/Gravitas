import os
import shutil
import subprocess
from pathlib import Path

fixtures_dir = Path("benchmarks/fixtures")
tasks_dir = Path("eval/tasks")
fixtures_dir.mkdir(parents=True, exist_ok=True)
tasks_dir.mkdir(parents=True, exist_ok=True)

def create_task_a():
    repo = fixtures_dir / "l1_bugfix"
    if repo.exists(): shutil.rmtree(repo)
    repo.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    
    (repo / "processor.py").write_text("""
def flatten(data):
    result = []
    for item in data:
        if isinstance(item, list):
            # BUG: Only flattens 1 level deep, doesn't recurse
            result.extend(item)
        else:
            result.append(item)
    return result
""")
    (repo / "test_processor.py").write_text("""
from processor import flatten
def test_flatten():
    assert flatten([1, 2, [3, 4]]) == [1, 2, 3, 4]
def test_flatten_deep():
    assert flatten([1, [2, [3, 4]]]) == [1, 2, 3, 4]
if __name__ == '__main__':
    test_flatten()
    test_flatten_deep()
    print("ALL PASS")
""")
    subprocess.run(["git", "add", "."], cwd=repo)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo)
    bundle = fixtures_dir / "l1_bugfix.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle.resolve()), "HEAD"], cwd=repo)
    
    yml = f"""task_id: REPAIR-CANARY-A
stratum: CONTROLLED
lane: isolated-bug-fix
title: "Fix deep flatten bug"
repository_url: "file://{bundle.absolute()}"
starting_commit: HEAD
task_provenance: Repaired fixture for canary
description: "The `flatten` function in `processor.py` fails on deeply nested lists. Fix the bug so it passes all tests in `test_processor.py`."
success_criteria:
  - id: AC-001
    statement: All tests pass
    validators: [VAL-001]
validators:
  - id: VAL-001
    command: python3 test_processor.py
    required: true
timeout: 60
"""
    (tasks_dir / "REPAIR-CANARY-A.yaml").write_text(yml)

def create_task_b():
    repo = fixtures_dir / "l2_feature"
    if repo.exists(): shutil.rmtree(repo)
    repo.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    
    (repo / "user.py").write_text("""
class User:
    def __init__(self, name):
        self.name = name
    def to_dict(self):
        return {"name": self.name}
""")
    (repo / "database.py").write_text("""
class Database:
    def __init__(self):
        self.users = []
    def insert(self, user_dict):
        self.users.append(user_dict)
""")
    (repo / "test_feature.py").write_text("""
from user import User
from database import Database
def test_age_feature():
    db = Database()
    u = User("Alice", age=30)
    db.insert(u.to_dict())
    assert db.users[0]["age"] == 30
if __name__ == '__main__':
    test_age_feature()
    print("ALL PASS")
""")
    subprocess.run(["git", "add", "."], cwd=repo)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo)
    bundle = fixtures_dir / "l2_feature.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle.resolve()), "HEAD"], cwd=repo)
    
    yml = f"""task_id: REPAIR-CANARY-B
stratum: CONTROLLED
lane: multi-file-feature
title: "Add age feature"
repository_url: "file://{bundle.absolute()}"
starting_commit: HEAD
task_provenance: Repaired fixture for canary
description: "Update `User` class to accept an `age` parameter in its constructor and include it in `to_dict`. Make sure `test_feature.py` passes."
success_criteria:
  - id: AC-001
    statement: Age is stored correctly
    validators: [VAL-001]
validators:
  - id: VAL-001
    command: python3 test_feature.py
    required: true
timeout: 60
"""
    (tasks_dir / "REPAIR-CANARY-B.yaml").write_text(yml)

def create_task_c():
    repo = fixtures_dir / "l7_plan"
    if repo.exists(): shutil.rmtree(repo)
    repo.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    
    (repo / "server.py").write_text("""
import http.server
import socketserver

PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
""")
    subprocess.run(["git", "add", "."], cwd=repo)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo)
    bundle = fixtures_dir / "l7_plan.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle.resolve()), "HEAD"], cwd=repo)
    
    yml = f"""task_id: REPAIR-CANARY-C
stratum: CONTROLLED
lane: plan-only-constraint
title: "Plan HTTPS migration"
repository_url: "file://{bundle.absolute()}"
starting_commit: HEAD
task_provenance: Repaired fixture for canary
description: "Investigate how to migrate `server.py` from HTTP to HTTPS in python. Do not modify any files. Just output a plan for how you would do it."
success_criteria:
  - id: AC-001
    statement: No file changes
    validators: [VAL-001]
validators:
  - id: VAL-001
    command: git diff --quiet && git diff --staged --quiet
    required: true
timeout: 60
"""
    (tasks_dir / "REPAIR-CANARY-C.yaml").write_text(yml)

create_task_a()
create_task_b()
create_task_c()
print("Repaired fixtures created.")
