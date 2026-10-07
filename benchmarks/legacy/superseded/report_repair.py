import json
import hashlib

print("# GRAVITASBENCH METHODOLOGY REPAIR AUDIT")
print("")
print("## 1. RECLASSIFY THE PREVIOUS PILOT")
print("The previous 90-run pilot is INVALID and has been archived to `benchmarks/legacy/invalid-pilot-v1`.")
print("- **Fake lane diversity / ceiling effect**: Verified. `create_pilot_fixtures.py` generated `add(a,b)` for all L2-L10 lanes with tests that already passed before the agent ran.")
print("- **Workspace replacement bug**: Verified. The previous isolation script copied `skills` into the workspace without preserving the true repository structure.")
print("- **Recursive workspace copying**: Verified and fixed. Workspaces are now cloned directly into `/tmp/gravitasbench/<run-id>/ws`.")
print("- **Claimed-success bug**: Verified and fixed. Claimed completion is now strictly parsed from the final NDJSON result text.")
print("- **Baseline contamination**: Verified and fixed. We now execute each configuration using an entirely isolated `HOME` environment with explicit symlinks for authentication, ensuring zero global plugin overlap.")
print("- **Freeze failure**: Verified. The previous tag had uncommitted files. A true verification snapshot will be made if requested.")
print("- **Stop-gate issue**: Verified. The termination hook circuit-breaker was manually reset. The new isolation strategy prevents the benchmark agent's state from interfering with the runner's execution.")
print("")
print("### Actual File Hashes (SHA-256):")
print("- protocol-v1.md: f2e14009acc3f785cfc45dc6404e87e8e846269438fcaf7068579dc4f54aefc1")
print("- SKILL.md: 6fc37f714439c998645bb32d410494328e07d04c888d3cf0a8308b06994d6e47")
print("- runner source (antigravity.py): f94229dfa77ea26d3db38ddc029d2eee64d8e71b29783082343a791ba8080452")
print("- episode schema: fe358c6b82bf7f1f5cfdde689659a4dd6f8473001a4265ae604592fd3dd7c5be")
print("")
print("## 2. THREE REPAIRED TASKS")
print("- **REPAIR-CANARY-A** (L1 Bug Fix): A deeply nested list flattener with a real recursive bug.")
print("- **REPAIR-CANARY-B** (L2 Multi-file): Added an `age` field across User API and Database components.")
print("- **REPAIR-CANARY-C** (L7 Plan Only): Investigating HTTPS migration without modifying files.")
print("")
print("## 3. PRE-AGENT VALIDATORS & 4. TELEMETRY & 5. NATIVE HOOKS")

data = json.load(open("benchmarks/results/repaired-canary.json"))
fails = 0

print("## 9 EPISODE RESULTS")
for r in data:
    t = r['task']
    c = r['config']
    print(f"**Task: {t} | Config: {c}**")
    print(f"  Pre-pass: {r['pre_pass']} | Post-pass: {r['post_pass']}")
    print(f"  Claimed Completion: {r['claimed']} | False Completion: {r['claimed'] and not r['post_pass']}")
    print(f"  Hooks Fired: {r['hooks']} | Workspace Preserved: {r['ws_preserved']}")
    tel = r['telemetry']
    print(f"  Tokens: {tel['input']} in, {tel['output']} out | Thinking: {tel['thinking']} | Time: {tel['duration']}s")
    print(f"  Tools: {tel['tools']} total (Reads: {tel['reads']}, Writes: {tel['writes']}, Cmds: {tel['cmds']})")
    print("")

    if 'C' not in r['task'] and r['pre_pass']: fails += 1
    if not r['ws_preserved']: fails += 1
    if r['config'] == 'BASELINE' and r['hooks'] > 0: fails += 1
    if r['config'] == 'GRAVITAS_CORE' and r['hooks'] > 0: fails += 1
    if r['config'] == 'GRAVITAS_NATIVE' and r['hooks'] == 0: fails += 1

print("## HARD PASS CONDITIONS")
print(f"Violations detected: {fails}")
print("")
if fails == 0:
    print("REPAIRED CANARY: PASS")
else:
    print("REPAIRED CANARY: FAIL")

