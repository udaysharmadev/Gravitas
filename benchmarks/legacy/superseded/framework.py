import json, subprocess, os, shutil, uuid, hashlib, sys
from pathlib import Path

def hash_conv(conv_id):
    return hashlib.sha256(conv_id.encode("utf-8")).hexdigest()[:24]

def setup_plugin_state(config, env):
    # We use agy plugin disable/enable, and we enforce ANTIGRAVITY_APP_DATA_DIR
    if config == "GRAVITAS_NATIVE":
        subprocess.run(["/Users/uday/.local/bin/agy", "plugin", "enable", "gravitas"], env=env, check=True)
    else:
        subprocess.run(["/Users/uday/.local/bin/agy", "plugin", "disable", "gravitas"], env=env, check=True)

    # Handle global skills deduplication
    global_skill = Path(os.path.expanduser("~/.gemini/config/skills/gravitas"))
    global_skill_bak = Path(os.path.expanduser("~/.gemini/config/skills/gravitas.bak"))
    
    if config == "GRAVITAS_NATIVE":
        # Native uses plugin's skill, hide global
        if global_skill.exists():
            global_skill.rename(global_skill_bak)
    elif config == "GRAVITAS_CORE":
        # Core uses global skill, restore if hidden
        if global_skill_bak.exists():
            global_skill_bak.rename(global_skill)
    else:
        # BASELINE uses NO skill, hide global
        if global_skill.exists():
            global_skill.rename(global_skill_bak)

def run_smoke_test(env):
    print("Running NATIVE PLUGIN SMOKE TEST...")
    ws = Path("/tmp/gravitas-smoke")
    if ws.exists(): shutil.rmtree(ws)
    ws.mkdir(parents=True)
    (ws / "hello.txt").write_text("Hello world")
    
    conv_id = str(uuid.uuid4())
    # Create contract so it doesn't fail closed!
    session_dir = Path(os.path.expanduser(f"~/.gemini/config/plugins/gravitas/.gravitas/sessions/conversation-{hash_conv(conv_id)}"))
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "contract.json").write_text(json.dumps({
        "mode": "implement",
        "allowed_write_scope": ["hello.txt"]
    }))
    
    setup_plugin_state("GRAVITAS_NATIVE", env)
    
    prompt = "Read hello.txt, replace Hello with Goodbye, and report completion using structured JSON output with task_status=COMPLETE."
    
    cmd = [
        "/Users/uday/.local/bin/agy", 
        "--output-format", "stream-json", 
        "--dangerously-skip-permissions", 
        "--conversation", conv_id,
        "--json-schema", "/Users/uday/Gravitas/schemas/benchmark_output.json",
        "--print", prompt
    ]
    
    print("Executing smoke test...")
    ndjson_out = ws / "out.ndjson"
    subprocess.run(cmd, cwd=ws, env=env, stdout=open(ndjson_out, "w"), stderr=subprocess.STDOUT)
    
    print("Smoke test finished. Checking hook evidence...")
    evidence_file = session_dir / "evidence.jsonl"
    if not evidence_file.exists():
        print("NATIVE PLUGIN SMOKE: FAIL (No evidence.jsonl found)")
        return False
        
    pre = 0
    post = 0
    stop = 0
    with open(evidence_file) as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                src = data.get("source")
                if src == "read": post += 1 # post_tool emits read evidence
                if src == "write": post += 1 # post_tool emits write evidence
                if src == "command": post += 1 # post_tool emits command evidence
            except: pass
            
    gate_log = session_dir / "stop_gate.log"
    if gate_log.exists():
        stop = sum(1 for _ in open(gate_log) if _.strip())
        
    print(f"Hook counts - PreToolUse(estimated): {post}, PostToolUse: {post}, Stop: {stop}")
    
    if post > 0 and stop > 0:
        print("NATIVE PLUGIN SMOKE: PASS")
        return True
    else:
        print("NATIVE PLUGIN SMOKE: FAIL (Counts were zero)")
        return False

def main():
    env = dict(os.environ)
    env["ANTIGRAVITY_APP_DATA_DIR"] = "/Users/uday/.gemini/config"
    
    if not run_smoke_test(env):
        sys.exit(1)

if __name__ == "__main__":
    main()
