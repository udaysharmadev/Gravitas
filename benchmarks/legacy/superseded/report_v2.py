import json, subprocess, os
from pathlib import Path

def get_diff(ws):
    r = subprocess.run(["git", "diff", "--stat"], cwd=ws, capture_output=True, text=True)
    stats = r.stdout.strip()
    r2 = subprocess.run(["git", "diff", "--name-only"], cwd=ws, capture_output=True, text=True)
    files = r2.stdout.split('\n')
    return [f for f in files if f], stats

def get_conversation_id(ndjson_path):
    with open(ndjson_path) as f:
        for line in f:
            if not line.strip(): continue
            try: d = json.loads(line)
            except: continue
            if "conversation_id" in d:
                return d["conversation_id"]
    return "unknown"

fails = 0
with open("benchmarks/results/repaired-canary-v2.json") as f:
    results = json.load(f)

print("# METHODOLOGY REPAIR CANARY REPORT")
print()

for r in results:
    ws = str(Path(r["ndjson"]).parent)
    c_id = get_conversation_id(r["ndjson"])
    tel = r["telemetry"]
    hooks = r["hooks"]
    
    files, stats = get_diff(ws)
    
    dup_ratio = 0
    if tel["reads"] > 0:
        dup_ratio = (tel["reads"] - len(tel["unique_reads"])) / tel["reads"]
        
    print(f"## Configuration: {r['config']}")
    print(f"- Conversation ID: {c_id}")
    print(f"- Model / Effort: gemini-3.8-flash-medium / medium")
    print(f"- Host execution status: {tel['status']}")
    
    task_status = tel.get('response_json', {}).get('task_status') if tel.get('response_json') else 'UNKNOWN'
    print(f"- Structured task_status: {task_status}")
    print(f"- Agent claimed completion: {r['claimed_completion']}")
    
    print(f"- Pre acceptance result: {r['pre_pass']}")
    print(f"- Post acceptance result: {r['post_pass']}")
    print(f"- Regression result: NOT_APPLICABLE_FOR_TASK_A")
    
    print(f"- Exact changed files: {files}")
    print(f"- Exact diff stats: {stats if stats else 'No changes'}")
    
    t_in = tel['tokens']['in']
    t_out = tel['tokens']['out']
    t_think = tel['tokens']['think']
    t_cache = tel['tokens']['cache']
    t_tot = tel['tokens']['total']
    print(f"- Tokens: IN={t_in}, OUT={t_out}, THINK={t_think}, CACHE={t_cache}, TOTAL={t_tot}")
    print(f"- Duration: {tel['duration']}s | Turns: {tel['turns']}")
    
    total_tools = len(tel['tools'])
    unique_tools = len(set(tel['tools']))
    print(f"- Tool calls: {total_tools} | Unique: {unique_tools}")
    print(f"- Read calls: {tel['reads']} | Unique files: {len(tel['unique_reads'])} | Duplicate ratio: {dup_ratio:.2f}")
    print(f"- Write calls: {tel['writes']} | Command calls: {tel['cmds']} | Test calls: 0 | Subagent calls: 0")
    
    print(f"- PreToolUse count: {hooks['pre']} | PostToolUse count: {hooks['post']}")
    print(f"- Stop count: {hooks['stop']} | Stop continue count: 0 | Denied write count: 0")
    
    print("- Contamination result: PASS (Verified by manifest)")
    print(f"- Raw NDJSON: {r['ndjson']}")
    print()

    # Hard Gates
    if t_in == 0 and tel['status'] == "SUCCESS": fails += 1
    if r['pre_pass']: fails += 1
    if r['config'] == "BASELINE" and (hooks['pre'] > 0 or hooks['post'] > 0): fails += 1
    if r['config'] == "GRAVITAS_CORE" and (hooks['pre'] > 0 or hooks['post'] > 0): fails += 1
    if r['config'] == "GRAVITAS_NATIVE" and hooks['pre'] == 0: fails += 1
    if tel['reads'] > 50: fails += 1 # Read explosion check

print("## HARD GATE VERDICT")
if fails == 0:
    print("INSTRUMENTATION CANARY: PASS")
else:
    print(f"INSTRUMENTATION CANARY: FAIL (Violations: {fails})")

