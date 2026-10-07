import json
import time
import random
import subprocess
from pathlib import Path
import shutil
import os
import uuid

def run_validator(cmd, ws):
    r = subprocess.run(cmd, shell=True, cwd=ws, capture_output=True)
    return r.returncode == 0

def get_telemetry(ndjson_path):
    tokens_in = 0
    tokens_out = 0
    thinking = 0
    tools = 0
    dur = 0
    reads = 0
    writes = 0
    cmds = 0
    
    if not ndjson_path.exists():
        return {"input":0, "output":0, "thinking":0, "tools":0, "duration":0, "reads":reads, "writes":writes, "cmds":cmds}
        
    with open(ndjson_path) as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
            except:
                continue
            if data.get("event") == "result":
                u = data.get("usage", {})
                tokens_in = u.get("input_tokens", 0)
                tokens_out = u.get("output_tokens", 0)
                thinking = u.get("thinking_tokens", 0)
                dur = data.get("execution", {}).get("duration_seconds", 0)
            elif data.get("event") == "step_update":
                st = data.get("step_update", {}).get("step_type")
                if st == "tool":
                    tools += 1
                    fn = data.get("step_update", {}).get("tool_name")
                    if fn in ["view_file", "search_web", "list_dir", "grep_search", "find_by_name"]:
                        reads += 1
                    elif fn in ["write_to_file", "replace_file_content"]:
                        writes += 1
                    elif fn in ["run_command"]:
                        cmds += 1
                        
    return {"input": tokens_in, "output": tokens_out, "thinking": thinking, "tools": tools, "duration": dur, "reads": reads, "writes": writes, "cmds": cmds}

def setup_global_config(config_mode):
    real_config = Path(os.path.expanduser("~/.gemini/config"))
    if real_config.exists():
        shutil.rmtree(real_config)
    real_config.mkdir(parents=True)
    
    repo_root = Path.cwd()
    
    if config_mode in ["GRAVITAS_CORE", "GRAVITAS_NATIVE"]:
        tgt_skill = real_config / "skills" / "gravitas"
        tgt_skill.mkdir(parents=True, exist_ok=True)
        if (repo_root / "skills/gravitas").exists():
            shutil.copytree(repo_root / "skills/gravitas", tgt_skill, dirs_exist_ok=True)
            
    if config_mode == "GRAVITAS_NATIVE":
        tgt_plugin = real_config / "plugins" / "gravitas"
        tgt_plugin.mkdir(parents=True, exist_ok=True)
        
        if (repo_root / "plugins/gravitas-antigravity").exists():
            inner_plugin = tgt_plugin / "plugins" / "gravitas-antigravity"
            shutil.copytree(repo_root / "plugins/gravitas-antigravity", inner_plugin, dirs_exist_ok=True)
            
        if (repo_root / "plugin.json").exists():
            shutil.copy(repo_root / "plugin.json", tgt_plugin / "plugin.json")
        if (repo_root / "hooks.json").exists():
            shutil.copy(repo_root / "hooks.json", tgt_plugin / "hooks.json")

def check_contamination(config_mode):
    gem_cfg = Path(os.path.expanduser("~/.gemini/config"))
    has_skill = (gem_cfg / "skills" / "gravitas").exists()
    has_plugin = (gem_cfg / "plugins" / "gravitas").exists()
    
    if config_mode == "BASELINE":
        assert not has_skill and not has_plugin, "Baseline contaminated!"
    elif config_mode == "GRAVITAS_CORE":
        assert has_skill and not has_plugin, "Core contaminated!"
    elif config_mode == "GRAVITAS_NATIVE":
        assert has_skill and has_plugin, "Native contaminated!"

def count_native_hooks():
    c = 0
    sessions = Path(os.path.expanduser("~/.gemini/config/plugins/gravitas/.gravitas/sessions"))
    if not sessions.exists():
        return 0
    for root, dirs, files in os.walk(sessions):
        for f in files:
            if f in ["stop_gate.log", "evidence.jsonl", "state.json"]:
                with open(os.path.join(root, f)) as fd:
                    c += sum(1 for line in fd if line.strip())
    return c

def check_task_status(ndjson_path):
    if not ndjson_path.exists():
        return False
    with open(ndjson_path) as f:
        for line in reversed(list(f)):
            if not line.strip(): continue
            try:
                data = json.loads(line)
            except:
                continue
            if data.get("event") == "result":
                txt = data.get("output", {}).get("text", "")
                if "VERDICT: PASS" in txt or "VERDICT: FAIL" in txt or "VERDICT:" in txt or "COMPLETE" in txt.upper():
                    return True 
    return False

def run_canary_episode(task_yaml, config):
    run_id = str(uuid.uuid4())
    ws = Path(f"/tmp/gravitasbench/{run_id}/ws")
    ws.mkdir(parents=True, exist_ok=True)
    
    task = {}
    content = Path(task_yaml).read_text()
    for line in content.split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v and k not in ['success_criteria', 'validators', '- id', 'statement', 'command', 'required']:
                task[k] = v
                
    if 'A' in task_yaml.name:
        validators = ["python3 test_processor.py"]
    elif 'B' in task_yaml.name:
        validators = ["python3 test_feature.py"]
    elif 'C' in task_yaml.name:
        validators = ["git diff --quiet && git diff --staged --quiet"]
        
    repo_url = task['repository_url'].replace('file://', '')
    subprocess.run(["git", "clone", repo_url, str(ws.resolve())], capture_output=True)
    
    setup_global_config(config)
    check_contamination(config)
    
    pre_pass = all(run_validator(cmd, ws) for cmd in validators)
    if pre_pass and 'C' not in task_yaml.name:
        print(f"ABORT: {task_yaml.name} validator passed before agent ran!")
        return None
        
    prompt = task['description'] + "\nWhen finished, output: VERDICT: PASS if complete."
    ndjson_out = ws / "out.ndjson"
    
    cmd = ["/Users/uday/.local/bin/agy", "--output-format", "stream-json", "--dangerously-skip-permissions", "--print", prompt]
    
    subprocess.run(cmd, cwd=ws, stdout=open(ndjson_out, "w"), stderr=subprocess.STDOUT)
    
    post_pass = all(run_validator(cmd, ws) for cmd in validators)
    
    claimed = check_task_status(ndjson_out)
    telem = get_telemetry(ndjson_out)
    
    hooks = count_native_hooks()
    
    # Save evidence outside before it gets deleted!
    if hooks > 0:
        evidence_backup = ws / "native_hooks_evidence"
        shutil.copytree(Path(os.path.expanduser("~/.gemini/config/plugins/gravitas/.gravitas/sessions")), evidence_backup, dirs_exist_ok=True)
        
    res = {
        "task": task_yaml.name,
        "config": config,
        "pre_pass": pre_pass,
        "post_pass": post_pass,
        "claimed": claimed,
        "hooks": hooks,
        "telemetry": telem,
        "ws_preserved": (ws / ".git").exists()
    }
    
    return res

if __name__ == "__main__":
    tasks = [Path("eval/tasks/REPAIR-CANARY-A.yaml"), Path("eval/tasks/REPAIR-CANARY-B.yaml"), Path("eval/tasks/REPAIR-CANARY-C.yaml")]
    configs = ["BASELINE", "GRAVITAS_CORE", "GRAVITAS_NATIVE"]
    
    results = []
    for t in tasks:
        for c in configs:
            print(f"Running {t.name} with {c}...")
            r = run_canary_episode(t, c)
            if r:
                print(r)
                results.append(r)
                
    Path("benchmarks/results/repaired-canary.json").parent.mkdir(exist_ok=True)
    Path("benchmarks/results/repaired-canary.json").write_text(json.dumps(results, indent=2))
    print("DONE")
