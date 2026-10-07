import sys
import json
import time
import random
import subprocess
from pathlib import Path
import shutil
import concurrent.futures

from benchmarks.runner.isolation import remove_gravitas, remove_native_hooks
from benchmarks.runner.antigravity import run_episode

random.seed(42)

def load_task(path):
    content = path.read_text()
    task = {}
    for line in content.split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v and k not in ['success_criteria', 'validators', '- id', 'statement', 'command', 'required']:
                task[k] = v
    task['validators'] = ["python3 test_calc.py"]
    if task.get('task_id') == 'PILOT-L7':
        task['validators'].append("git diff --quiet && git diff --staged --quiet")
    return task

def prepare_task_workspace(task, config_mode, run_idx):
    base = Path("benchmarks/results/workspaces")
    ws = base / f"{task['task_id']}_{config_mode}_{run_idx}"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    
    repo_url = task['repository_url'].replace('file://', '')
    subprocess.run(["git", "clone", repo_url, str(ws.resolve())], capture_output=True)
    subprocess.run(["git", "checkout", task['starting_commit']], cwd=ws, capture_output=True)
    
    repo_root = Path.cwd()
    if (repo_root / "skills").exists():
        shutil.copytree(repo_root / "skills", ws / "skills", dirs_exist_ok=True)
    if (repo_root / ".agents").exists():
        shutil.copytree(repo_root / ".agents", ws / ".agents", dirs_exist_ok=True)
    if (repo_root / "plugin.json").exists():
        shutil.copy(repo_root / "plugin.json", ws / "plugin.json")
    if (repo_root / "plugins").exists():
        shutil.copytree(repo_root / "plugins", ws / "plugins", dirs_exist_ok=True)
        
    if config_mode == "BASELINE":
        remove_gravitas(ws)
    elif config_mode == "GRAVITAS_CORE":
        remove_native_hooks(ws)
        
    return ws

def evaluate_validators(ws, validators):
    results = []
    for cmd in validators:
        r = subprocess.run(cmd, shell=True, cwd=ws, capture_output=True)
        results.append(r.returncode == 0)
    return all(results)

def run_single_episode(task, config, r_idx):
    print(f"Starting {task['task_id']} | {config} | Run {r_idx}", flush=True)
    ws = prepare_task_workspace(task, config, r_idx)
    out_dir = Path("benchmarks/results/pilot") / f"{task['task_id']}_{config}_{r_idx}"
    
    res = run_episode(
        cwd=ws,
        prompt=task['description'],
        model_slug="gemini-3.8-flash-medium",
        output_dir=out_dir,
        timeout_seconds=60,
        sandbox_enabled=False
    )
    
    validation_pass = evaluate_validators(ws, task['validators'])
    terminal = res['execution']['terminal_status']
    claimed_success = (terminal == "SUCCESS")
    false_completion = claimed_success and not validation_pass
    
    res['evaluation'] = {
        "validation_pass": validation_pass,
        "claimed_success": claimed_success,
        "false_completion": false_completion
    }
    res['meta'] = {
        "task_id": task['task_id'],
        "config": config,
        "run_index": r_idx
    }
    shutil.rmtree(ws)
    print(f"Finished {task['task_id']} | {config} | Run {r_idx}", flush=True)
    return res

def run_pilot(tasks_to_run, runs_per_task=1, out_file="summary.json"):
    configs = ["BASELINE", "GRAVITAS_CORE", "GRAVITAS_NATIVE"]
    
    schedule = []
    for t in tasks_to_run:
        for r in range(runs_per_task):
            block = configs.copy()
            random.shuffle(block)
            for c in block:
                schedule.append((t, c, r))
                
    Path("benchmarks/results/pilot").mkdir(parents=True, exist_ok=True)
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for (t_path, config, r_idx) in schedule:
            task = load_task(t_path)
            futures.append(executor.submit(run_single_episode, task, config, r_idx))
            
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
        
    (Path("benchmarks/results/pilot") / out_file).write_text(json.dumps(results, indent=2))
    print("Pilot complete.", flush=True)

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "canary"
    all_tasks = sorted(list(Path("eval/tasks").glob("*-PILOT.yaml")))
    
    if stage == "canary":
        tasks = [Path("eval/tasks/L1-PILOT.yaml"), Path("eval/tasks/L2-PILOT.yaml"), Path("eval/tasks/L7-PILOT.yaml")]
        run_pilot(tasks, 1, "summary_canary.json")
    elif stage == "mini":
        run_pilot(all_tasks, 1, "summary_mini.json")
    elif stage == "full":
        run_pilot(all_tasks, 3, "summary_full.json")
