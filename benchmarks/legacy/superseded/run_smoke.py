import json
import subprocess
import os
import shutil
import uuid
from pathlib import Path

def test_smoke():
    print("Running smoke test...")
    ws = Path("/tmp/gravitas-smoke")
    if ws.exists(): shutil.rmtree(ws)
    ws.mkdir(parents=True)
    
    (ws / "hello.txt").write_text("Hello world")
    
    ndjson_out = ws / "out.ndjson"
    
    prompt = "Read hello.txt, replace Hello with Goodbye, and report completion using structured JSON output with task_status=COMPLETE."
    
    cmd = [
        "/Users/uday/.local/bin/agy", 
        "--output-format", "stream-json", 
        "--dangerously-skip-permissions", 
        "--json-schema", "/Users/uday/Gravitas/schemas/benchmark_output.json",
        "--print", prompt
    ]
    
    env = dict(os.environ)
    # Use the IDE configuration directory where the plugin is actually installed
    env["ANTIGRAVITY_APP_DATA_DIR"] = "/Users/uday/.gemini/config"
    
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ws, env=env, stdout=open(ndjson_out, "w"), stderr=subprocess.STDOUT)
    
    print("Done executing. Checking NDJSON...")
    # Extract conversation ID from ndjson
    conv_id = None
    with open(ndjson_out) as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                if data.get("event") == "init":
                    conv_id = data.get("conversation_id")
            except:
                pass
                
    print(f"Conversation ID: {conv_id}")
    
    # Check if the file was modified
    print("Modified file content:", (ws / "hello.txt").read_text())
    
    if not conv_id:
        print("FAIL: No conversation ID found in ndjson!")
        return False
        
    # Check plugin hook logs!
    import hashlib
    digest = hashlib.sha256(conv_id.encode("utf-8")).hexdigest()[:24]
    session_dir = Path(os.path.expanduser(f"~/.gemini/config/plugins/gravitas/.gravitas/sessions/conversation-{digest}"))
    
    print(f"Looking for hooks in {session_dir}")
    if not session_dir.exists():
        print("FAIL: Session dir does not exist! Hooks did not fire!")
        return False
        
    evidence_file = session_dir / "evidence.jsonl"
    if not evidence_file.exists():
        print("FAIL: evidence.jsonl does not exist!")
        return False
        
    pre = 0
    post = 0
    with open(evidence_file) as f:
        for line in f:
            print("EVIDENCE:", line.strip())
            if '"source": "read"' in line or '"source": "write"' in line or "command" in line:
                pass
    
    return True

if __name__ == "__main__":
    test_smoke()
