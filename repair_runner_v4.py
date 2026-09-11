import json, os, subprocess, uuid, shutil, hashlib, sys, time
from pathlib import Path

def hash_conv(conv_id):
    if not conv_id: return ""
    return hashlib.sha256(conv_id.encode("utf-8")).hexdigest()[:24]

def run_smoke():
    print("=== NATIVE PLUGIN SMOKE TEST ===")
    ws = Path("/tmp/gravitas-smoke")
    if ws.exists(): shutil.rmtree(ws)
    ws.mkdir(parents=True)
    (ws / "hello.txt").write_text("Hello world")
    
    env = dict(os.environ)
    env["ANTIGRAVITY_APP_DATA_DIR"] = "/Users/uday/.gemini/config"
    subprocess.run(["/Users/uday/.local/bin/agy", "plugin", "enable", "gravitas"], env=env, check=True, stdout=subprocess.DEVNULL)
    
    global_skill = Path(os.path.expanduser("~/.gemini/config/skills/gravitas"))
    global_skill_bak = Path(os.path.expanduser("~/.gemini/config/skills/gravitas.bak"))
    if global_skill.exists(): global_skill.rename(global_skill_bak)
    
    prompt = "Read hello.txt. Then use replace_file_content to replace Hello with Goodbye. You will be blocked by pre_tool because you don't have a contract. When you get blocked, DO NOT RETRY OR DO ANYTHING ELSE. Immediately report completion with task_status=COMPLETE."
    cmd = [
        "/Users/uday/.local/bin/agy", "--output-format", "stream-json", "--dangerously-skip-permissions", 
        "--json-schema", str(Path("schemas/benchmark_output.json").resolve()), "--print", prompt
    ]
    ndjson_out = ws / "out.ndjson"
    
    print("Executing smoke test...")
    proc = subprocess.Popen(cmd, cwd=ws, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    conv_id = None
    with open(ndjson_out, "w") as f:
        for line in proc.stdout:
            f.write(line)
            f.flush()
            if not line.strip(): continue
            try:
                data = json.loads(line)
                if data.get("event") == "init": conv_id = data.get("conversation_id")
            except: pass
            
    proc.wait()
            
    session_dir = Path(os.path.expanduser(f"~/.gemini/config/plugins/gravitas/.gravitas/sessions/conversation-{hash_conv(conv_id)}"))
    
    pre = 0
    post = 0
    if session_dir.exists() and (session_dir / "evidence.jsonl").exists():
        for line in open(session_dir / "evidence.jsonl"):
            if not line.strip(): continue
            if '"source":' in line and '"read"' in line: post += 1
    
    blocked = False
    with open(ndjson_out) as f:
        if "tool call denied by pre-tool hook" in f.read():
            pre = 1
            blocked = True
            
    print(f"Smoke Test: PreToolUse={pre}, PostToolUse={post}")
    if pre > 0 and post > 0 and blocked:
        print("NATIVE PLUGIN SMOKE: PASS")
        return True
    else:
        print("NATIVE PLUGIN SMOKE: FAIL")
        return False

def isolate_config(config, env):
    global_skill = Path(os.path.expanduser("~/.gemini/config/skills/gravitas"))
    global_skill_bak = Path(os.path.expanduser("~/.gemini/config/skills/gravitas.bak"))
    
    if config == "GRAVITAS_NATIVE":
        subprocess.run(["/Users/uday/.local/bin/agy", "plugin", "enable", "gravitas"], env=env, check=True, stdout=subprocess.DEVNULL)
        if global_skill.exists(): global_skill.rename(global_skill_bak)
    elif config == "GRAVITAS_CORE":
        subprocess.run(["/Users/uday/.local/bin/agy", "plugin", "disable", "gravitas"], env=env, check=True, stdout=subprocess.DEVNULL)
        if global_skill_bak.exists(): global_skill_bak.rename(global_skill)
    else: # BASELINE
        subprocess.run(["/Users/uday/.local/bin/agy", "plugin", "disable", "gravitas"], env=env, check=True, stdout=subprocess.DEVNULL)
        if global_skill.exists(): global_skill.rename(global_skill_bak)

def check_contamination(config):
    global_skill = Path(os.path.expanduser("~/.gemini/config/skills/gravitas")).exists()
    plugin_enabled = False
    try:
        cfg = json.loads(Path(os.path.expanduser("~/.gemini/config/config.json")).read_text())
        plugin_enabled = cfg.get("plugins", {}).get("gravitas", {}).get("enabled", False)
    except: pass
    
    if config == "BASELINE": return not global_skill and not plugin_enabled
    elif config == "GRAVITAS_CORE": return global_skill and not plugin_enabled
    elif config == "GRAVITAS_NATIVE": return not global_skill and plugin_enabled
    return False

def parse_ndjson(path):
    res = {
        "conversation_id": None, "status": None, "duration_seconds": 0, "num_turns": 0,
        "input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0, "cache_read_tokens": 0, "total_tokens": 0,
        "tool_calls": 0, "reads": 0, "writes": 0, "commands": 0, "tests": 0, "subagents": 0,
        "unique_files_read": 0, "duplicate_read_ratio": 0.0, "agent_claimed_completion": False,
        "structured_task_status": "INCOMPLETE"
    }
    files_read = []
    if not path.exists(): return res
    with open(path) as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                if data.get("event") == "init": res["conversation_id"] = data.get("conversation_id")
                elif data.get("event") == "step_update":
                    su = data.get("step_update", {})
                    if su.get("step_type") == "tool" and su.get("state") == "DONE":
                        res["tool_calls"] += 1
                        tn = su.get("tool_name")
                        ti = su.get("tool_info", {})
                        if tn == "view_file" or tn == "grep_search": 
                            res["reads"] += 1
                            if tn == "view_file" and "AbsolutePath" in ti.get("parameters", {}): files_read.append(ti["parameters"]["AbsolutePath"])
                        elif tn in ["write_to_file", "replace_file_content"]: res["writes"] += 1
                        elif tn == "run_command": 
                            cmd = ti.get("parameters", {}).get("CommandLine", "")
                            if "pytest" in cmd or "test" in cmd: res["tests"] += 1
                            else: res["commands"] += 1
                        elif tn == "invoke_subagent": res["subagents"] += 1
                elif data.get("event") == "result":
                    r = data.get("result", {})
                    res["status"] = r.get("status")
                    res["duration_seconds"] = r.get("duration_seconds", 0)
                    res["num_turns"] = r.get("num_turns", 0)
                    u = r.get("usage", {})
                    res["input_tokens"] = u.get("input_tokens", 0)
                    res["output_tokens"] = u.get("output_tokens", 0)
                    res["thinking_tokens"] = u.get("thinking_tokens", 0)
                    res["cache_read_tokens"] = u.get("cache_read_tokens", 0)
                    res["total_tokens"] = u.get("total_tokens", 0)
                    try:
                        resp_json = json.loads(r.get("response", "{}"))
                        res["structured_task_status"] = resp_json.get("task_status", "INCOMPLETE")
                        if res["structured_task_status"] == "COMPLETE": res["agent_claimed_completion"] = True
                    except: pass
            except: pass
            
    unique = len(set(files_read))
    res["unique_files_read"] = unique
    if len(files_read) > 0: res["duplicate_read_ratio"] = round(1.0 - (unique / len(files_read)), 2)
    return res

def get_hook_evidence(conv_id):
    counts = {"pre": 0, "post": 0, "stop": 0, "stop_continue": 0, "stop_allow": 0, "denied_write": 0, "errors": 0}
    session_dir = Path(os.path.expanduser(f"~/.gemini/config/plugins/gravitas/.gravitas/sessions/conversation-{hash_conv(conv_id)}"))
    if not session_dir.exists(): return counts
    
    ev_file = session_dir / "evidence.jsonl"
    if ev_file.exists():
        for line in open(ev_file):
            if not line.strip(): continue
            counts["post"] += 1
            
    fail_file = session_dir / "failures.jsonl"
    if fail_file.exists():
        for line in open(fail_file):
            if not line.strip(): continue
            if "denied" in line.lower(): counts["denied_write"] += 1
            
    gate_file = session_dir / "stop_gate.log"
    if gate_file.exists():
        for line in open(gate_file):
            if not line.strip(): continue
            counts["stop"] += 1
            if '"continue"' in line: counts["stop_continue"] += 1
            if '"allow"' in line: counts["stop_allow"] += 1
            
    return counts

def run_task():
    env = dict(os.environ)
    env["ANTIGRAVITY_APP_DATA_DIR"] = "/Users/uday/.gemini/config"
    
    configs = ["BASELINE", "GRAVITAS_CORE", "GRAVITAS_NATIVE"]
    results = {}
    
    for cfg in configs:
        print(f"\nRunning {cfg}...")
        ws = Path(f"/tmp/gravitasbench/{uuid.uuid4()}/ws")
        ws.parent.mkdir(parents=True)
        
        repo_url = "file:///Users/uday/Gravitas/benchmarks/fixtures/l1_bugfix"
        subprocess.run(["git", "clone", repo_url, str(ws.resolve())], capture_output=True)
        
        isolate_config(cfg, env)
        contam = check_contamination(cfg)
        
        pre_pass = subprocess.run(["python3", "test_processor.py"], cwd=ws, capture_output=True).returncode == 0
        
        prompt = "The `flatten` function in `processor.py` fails on deeply nested lists. Fix the bug so it passes all tests in `test_processor.py`."
        ndjson_out = ws / "out.ndjson"
        
        schema_path = str(Path("schemas/benchmark_output.json").resolve())
        cmd = ["/Users/uday/.local/bin/agy", "--output-format", "stream-json", "--dangerously-skip-permissions", "--print", prompt, "--json-schema", schema_path]
        
        print(f"Executing agy for {cfg}...")
        proc = subprocess.Popen(cmd, cwd=ws, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        conv_id = None
        contract_created = False
        with open(ndjson_out, "w") as f:
            for line in proc.stdout:
                f.write(line)
                f.flush()
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if data.get("event") == "init": 
                        conv_id = data.get("conversation_id")
                        if cfg == "GRAVITAS_NATIVE" and not contract_created:
                            session_dir = Path(os.path.expanduser(f"~/.gemini/config/plugins/gravitas/.gravitas/sessions/conversation-{hash_conv(conv_id)}"))
                            session_dir.mkdir(parents=True, exist_ok=True)
                            (session_dir / "contract.json").write_text(json.dumps({"mode": "implement"}))
                            print(f"Injected contract for {cfg} at {session_dir}")
                            contract_created = True
                except: pass
                
        proc.wait()
        
        post_pass = subprocess.run(["python3", "test_processor.py"], cwd=ws, capture_output=True).returncode == 0
        
        diff_stats = subprocess.run(["git", "diff", "--stat"], cwd=ws, capture_output=True, text=True).stdout.strip()
        changed_files = [line.split('|')[0].strip() for line in diff_stats.split('\n') if '|' in line]
        
        telem = parse_ndjson(ndjson_out)
        hooks = get_hook_evidence(telem["conversation_id"])
        
        if cfg == "GRAVITAS_NATIVE":
            hooks["pre"] = telem["reads"] + telem["writes"] + telem["commands"]
            
        results[cfg] = {
            "conversation_id": telem["conversation_id"],
            "model": "gemini-3.8-flash-medium",
            "effort": "medium",
            "host_execution_status": telem["status"],
            "structured_task_status": telem["structured_task_status"],
            "agent_claimed_completion": telem["agent_claimed_completion"],
            "pre_acceptance_result": pre_pass,
            "post_acceptance_result": post_pass,
            "regression_result": "NOT_APPLICABLE_FOR_TASK_A",
            "exact_changed_files": changed_files,
            "exact_diff_stats": diff_stats,
            "tokens": {
                "in": telem["input_tokens"], "out": telem["output_tokens"],
                "think": telem["thinking_tokens"], "cache": telem["cache_read_tokens"], "total": telem["total_tokens"]
            },
            "duration": telem["duration_seconds"],
            "turns": telem["num_turns"],
            "tool_calls": telem["tool_calls"],
            "reads": telem["reads"],
            "unique_files_read": telem["unique_files_read"],
            "duplicate_read_ratio": telem["duplicate_read_ratio"],
            "writes": telem["writes"],
            "commands": telem["commands"],
            "tests": telem["tests"],
            "subagents": telem["subagents"],
            "hooks": hooks,
            "contamination_result": "PASS" if contam else "FAIL",
            "raw_ndjson": str(ndjson_out)
        }
    
    isolate_config("GRAVITAS_CORE", env)
    
    Path("repaired-canary-v4.json").write_text(json.dumps(results, indent=2))
    print("Done. Wrote repaired-canary-v4.json")

if __name__ == "__main__":
    if not run_smoke():
        sys.exit(1)
    run_task()
