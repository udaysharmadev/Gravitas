import json, time, subprocess, shutil, os, uuid, hashlib
from pathlib import Path

def get_hash(path):
    if not os.path.exists(path): return "none"
    if os.path.isdir(path): return "dir"
    m = hashlib.sha256()
    with open(path, "rb") as f:
        m.update(f.read())
    return m.hexdigest()

def dump_manifest(config_mode):
    # Capture state of plugins and skills
    gem_cfg = Path(os.path.expanduser("~/.gemini/config"))
    manifest = {
        "mode": config_mode,
        "config_json": get_hash(gem_cfg / "config.json"),
        "plugins": {},
        "skills": {}
    }
    for p in (gem_cfg / "plugins").glob("*"):
        manifest["plugins"][p.name] = "exists"
    for s in (gem_cfg / "skills").glob("*"):
        manifest["skills"][s.name] = "exists"
    
    # Read config.json to see if gravitas is disabled
    try:
        with open(gem_cfg / "config.json") as f:
            c = json.load(f)
            manifest["config_plugins"] = c.get("plugins", {})
    except:
        manifest["config_plugins"] = {}
        
    return manifest

def isolate_config(config_mode):
    gem_cfg = Path(os.path.expanduser("~/.gemini/config"))
    # 1. Handle skills
    skills = ["gravitas", "gravitas-python", "gravitas-typescript"]
    if config_mode == "BASELINE":
        for s in skills:
            p = gem_cfg / "skills" / s
            if p.exists(): os.rename(p, gem_cfg / "skills" / (s + ".bak"))
    else:
        # Core and Native both need the skill
        pass
        
    # 2. Handle plugin (disable in config.json)
    if config_mode in ["BASELINE", "GRAVITAS_CORE"]:
        c = {}
        if (gem_cfg / "config.json").exists():
            with open(gem_cfg / "config.json") as f:
                c = json.load(f)
        if "plugins" not in c: c["plugins"] = {}
        if "gravitas" not in c["plugins"]: c["plugins"]["gravitas"] = {}
        c["plugins"]["gravitas"]["enabled"] = False
        with open(gem_cfg / "config.json", "w") as f:
            json.dump(c, f, indent=2)

def restore_config(config_mode):
    gem_cfg = Path(os.path.expanduser("~/.gemini/config"))
    skills = ["gravitas", "gravitas-python", "gravitas-typescript"]
    if config_mode == "BASELINE":
        for s in skills:
            bak = gem_cfg / "skills" / (s + ".bak")
            if bak.exists():
                orig = gem_cfg / "skills" / s
                if orig.exists(): shutil.rmtree(orig)
                os.rename(bak, orig)
                
    if config_mode in ["BASELINE", "GRAVITAS_CORE"]:
        if (gem_cfg / "config.json").exists():
            with open(gem_cfg / "config.json") as f:
                c = json.load(f)
            if "plugins" in c and "gravitas" in c["plugins"]:
                c["plugins"]["gravitas"]["enabled"] = True
            with open(gem_cfg / "config.json", "w") as f:
                json.dump(c, f, indent=2)

def check_contamination(manifest, config_mode):
    # Baseline must have gravitas skill as .bak or missing, and plugin disabled
    if config_mode == "BASELINE":
        assert "gravitas" not in manifest["skills"], "Baseline has active skill"
        plug_cfg = manifest["config_plugins"].get("gravitas", {})
        assert plug_cfg.get("enabled", True) == False, "Baseline has active plugin"
    elif config_mode == "GRAVITAS_CORE":
        assert "gravitas" in manifest["skills"], "Core missing skill"
        plug_cfg = manifest["config_plugins"].get("gravitas", {})
        assert plug_cfg.get("enabled", True) == False, "Core has active plugin"
    elif config_mode == "GRAVITAS_NATIVE":
        assert "gravitas" in manifest["skills"], "Native missing skill"
        plug_cfg = manifest["config_plugins"].get("gravitas", {})
        assert plug_cfg.get("enabled", True) == True, "Native missing active plugin"

def parse_ndjson(path):
    res = {
        "tokens": {"in": 0, "out": 0, "think": 0, "cache": 0, "total": 0},
        "duration": 0,
        "turns": 0,
        "tools": [],
        "reads": 0,
        "writes": 0,
        "cmds": 0,
        "unique_reads": set(),
        "status": None,
        "response_json": None
    }
    if not path.exists(): return res
    with open(path) as f:
        for line in f:
            if not line.strip(): continue
            try: data = json.loads(line)
            except: continue
            
            if data.get("event") == "result":
                r = data.get("result", {})
                res["status"] = r.get("status")
                res["duration"] = r.get("duration_seconds", 0)
                res["turns"] = r.get("num_turns", 0)
                u = r.get("usage", {})
                res["tokens"]["in"] = u.get("input_tokens", 0)
                res["tokens"]["out"] = u.get("output_tokens", 0)
                res["tokens"]["think"] = u.get("thinking_tokens", 0)
                res["tokens"]["cache"] = u.get("cache_read_tokens", 0)
                res["tokens"]["total"] = u.get("total_tokens", 0)
                
                txt = r.get("response", "")
                try: res["response_json"] = json.loads(txt)
                except: pass
                
            elif data.get("event") == "step_update":
                su = data.get("step_update", {})
                if su.get("step_type") == "tool" and su.get("state") == "DONE":
                    name = su.get("tool_name")
                    res["tools"].append(name)
                    if name in ["view_file", "search_web", "list_dir", "grep_search", "find_by_name", "read_url_content", "read_resource"]:
                        res["reads"] += 1
                        info = su.get("tool_info", {}).get("parameters", {})
                        target = info.get("AbsolutePath") or info.get("SearchDirectory") or info.get("DirectoryPath") or info.get("SearchPath") or str(info)
                        res["unique_reads"].add(target)
                    elif name in ["write_to_file", "replace_file_content", "sed_file", "multi_replace_file_content"]:
                        res["writes"] += 1
                    elif name in ["run_command"]:
                        res["cmds"] += 1
                        
    res["unique_reads"] = list(res["unique_reads"])
    return res

def count_hooks(sessions_dir):
    h = {"pre": 0, "post": 0, "stop": 0}
    if not sessions_dir.exists(): return h
    for root, dirs, files in os.walk(sessions_dir):
        if "evidence.jsonl" in files:
            with open(os.path.join(root, "evidence.jsonl")) as f:
                for line in f:
                    if "PreToolUse" in line: h["pre"] += 1
                    if "PostToolUse" in line: h["post"] += 1
        if "stop_gate.log" in files:
            with open(os.path.join(root, "stop_gate.log")) as f:
                h["stop"] += sum(1 for line in f if line.strip())
    return h

def run_canary_episode(config):
    task_yaml = Path("eval/tasks/REPAIR-CANARY-A.yaml")
    run_id = str(uuid.uuid4())
    ws = Path(f"/tmp/gravitasbench/{run_id}/ws")
    ws.mkdir(parents=True, exist_ok=True)
    
    # Extract git url
    repo_url = "https://github.com/udaysharmadev/Gravitas.git" # we use the local bundle
    for line in task_yaml.read_text().split('\n'):
        if 'repository_url:' in line:
            repo_url = line.split(':', 1)[1].strip().strip('"').strip("'").replace('file://', '')
            break
            
    subprocess.run(["git", "clone", repo_url, str(ws.resolve())], capture_output=True)
    
    # Capture hooks before
    plugin_sessions = Path(os.path.expanduser("~/.gemini/config/plugins/gravitas/.gravitas/sessions"))
    if plugin_sessions.exists():
        shutil.rmtree(plugin_sessions)
        
    isolate_config(config)
    manifest = dump_manifest(config)
    check_contamination(manifest, config)
    
    cmd = ["python3", "test_processor.py"]
    pre_pass = subprocess.run(cmd, cwd=ws, capture_output=True).returncode == 0
    
    prompt = "The `flatten` function in `processor.py` fails on deeply nested lists. Fix the bug so it passes all tests in `test_processor.py`."
    ndjson_out = ws / "out.ndjson"
    
    schema_path = str(Path("schemas/benchmark_output.json").resolve())
    cmd = ["/Users/uday/.local/bin/agy", "--output-format", "stream-json", "--dangerously-skip-permissions", "--print", prompt, "--json-schema", schema_path]
    
    subprocess.run(cmd, cwd=ws, stdout=open(ndjson_out, "w"), stderr=subprocess.STDOUT)
    
    post_pass = subprocess.run(["python3", "test_processor.py"], cwd=ws, capture_output=True).returncode == 0
    
    restore_config(config)
    
    # Get telemetry
    telem = parse_ndjson(ndjson_out)
    hooks = count_hooks(plugin_sessions)
    
    r = {
        "config": config,
        "manifest": manifest,
        "pre_pass": pre_pass,
        "post_pass": post_pass,
        "telemetry": telem,
        "hooks": hooks,
        "ndjson": str(ndjson_out),
        "ws_preserved": (ws / ".git").exists()
    }
    
    # Determine claimed completion
    r["claimed_completion"] = False
    if telem["response_json"] and telem["response_json"].get("task_status") == "COMPLETE":
        r["claimed_completion"] = True
        
    return r

if __name__ == "__main__":
    configs = ["BASELINE", "GRAVITAS_CORE", "GRAVITAS_NATIVE"]
    results = []
    try:
        for c in configs:
            print(f"Running {c}...")
            r = run_canary_episode(c)
            results.append(r)
    finally:
        # Failsafe restore
        restore_config("BASELINE")
        
    Path("benchmarks/results/repaired-canary-v2.json").parent.mkdir(exist_ok=True)
    Path("benchmarks/results/repaired-canary-v2.json").write_text(json.dumps(results, indent=2))
    print("DONE")
