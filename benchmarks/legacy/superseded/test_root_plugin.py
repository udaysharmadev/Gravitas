import subprocess
from pathlib import Path
import os
import shutil

ws = Path("/tmp/test_root_plugin")
if ws.exists():
    shutil.rmtree(ws)
ws.mkdir(parents=True)

repo_root = Path.cwd()

# 1. Setup workspace-local plugin in the ROOT of the workspace!
inner_plugin = ws / "plugins" / "gravitas-antigravity"
inner_plugin.mkdir(parents=True, exist_ok=True)
shutil.copytree(repo_root / "plugins/gravitas-antigravity", inner_plugin, dirs_exist_ok=True)
shutil.copy(repo_root / "plugin.json", ws / "plugin.json")
shutil.copy(repo_root / "hooks.json", ws / "hooks.json")

prompt = "Just say Hello. Output: VERDICT: PASS if complete."
ndjson_out = ws / "out.ndjson"
cmd = ["/Users/uday/.local/bin/agy", "--output-format", "stream-json", "--dangerously-skip-permissions", "--print", prompt]
subprocess.run(cmd, cwd=ws, stdout=open(ndjson_out, "w"), stderr=subprocess.STDOUT)

# Count hooks
c = 0
sessions = ws / ".gravitas" / "sessions"
if sessions.exists():
    for root, dirs, files in os.walk(sessions):
        for f in files:
            if f in ["stop_gate.log", "evidence.jsonl", "state.json"]:
                with open(os.path.join(root, f)) as fd:
                    c += sum(1 for line in fd if line.strip())
print("Hooks fired:", c)
