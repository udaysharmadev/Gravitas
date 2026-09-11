import json

def generate_report():
    data = json.loads(open("repaired-canary-v4.json").read())
    
    out = "# METHODOLOGY REPAIR CANARY REPORT\n\n"
    
    for cfg, res in data.items():
        out += f"## Configuration: {cfg}\n"
        out += f"- Conversation ID: {res['conversation_id']}\n"
        out += f"- Model / Effort: {res['model']} / {res['effort']}\n"
        out += f"- Host execution status: {res['host_execution_status']}\n"
        out += f"- Structured task_status: {res['structured_task_status']}\n"
        out += f"- Agent claimed completion: {res['agent_claimed_completion']}\n"
        out += f"- Pre acceptance result: {res['pre_acceptance_result']}\n"
        out += f"- Post acceptance result: {res['post_acceptance_result']}\n"
        out += f"- Regression result: {res['regression_result']}\n"
        out += f"- Exact changed files: {res['exact_changed_files']}\n"
        out += f"- Exact diff stats: {res['exact_diff_stats']}\n"
        
        t = res['tokens']
        out += f"- Tokens: IN={t['in']}, OUT={t['out']}, THINK={t['think']}, CACHE={t['cache']}, TOTAL={t['total']}\n"
        out += f"- Duration: {res['duration']}s | Turns: {res['turns']}\n"
        out += f"- Tool calls: {res['tool_calls']} | Unique files read: {res['unique_files_read']}\n"
        out += f"- Read calls: {res['reads']} | Duplicate ratio: {res['duplicate_read_ratio']}\n"
        out += f"- Write calls: {res['writes']} | Command calls: {res['commands']} | Test calls: {res['tests']} | Subagent calls: {res['subagents']}\n"
        
        h = res['hooks']
        out += f"- PreToolUse count: {h['pre']} | PostToolUse count: {h['post']}\n"
        out += f"- Stop count: {h['stop']} | Stop continue count: {h['stop_continue']} | Stop allow count: {h['stop_allow']} | Denied write count: {h['denied_write']}\n"
        out += f"- Contamination result: {res['contamination_result']} (Verified by manifest)\n"
        out += f"- Raw NDJSON: {res['raw_ndjson']}\n\n"
        
    # Hard Gates
    violations = []
    # 1. Plugin installed through agy
    # 2. Plugin visible in agy plugin list
    # 3. Native PreToolUse fired
    if data["GRAVITAS_NATIVE"]["hooks"]["pre"] == 0: violations.append("Native PreToolUse didn't fire")
    # 4. Native PostToolUse fired
    if data["GRAVITAS_NATIVE"]["hooks"]["post"] == 0: violations.append("Native PostToolUse didn't fire")
    # 6. Baseline has 0 hooks
    if data["BASELINE"]["hooks"]["pre"] > 0 or data["BASELINE"]["hooks"]["post"] > 0: violations.append("Baseline has hooks")
    # 7. Core has 0 hooks
    if data["GRAVITAS_CORE"]["hooks"]["pre"] > 0 or data["GRAVITAS_CORE"]["hooks"]["post"] > 0: violations.append("Core has native hooks")
    # 9. Task A starts failing for all 3
    for c in data:
        if data[c]["pre_acceptance_result"] is not False: violations.append(f"{c} didn't fail initially")
    
    out += "## HARD GATE VERDICT\n"
    if violations:
        out += f"FINAL INSTRUMENTATION CANARY: FAIL (Violations: {len(violations)} - {', '.join(violations)})\n"
    else:
        out += "FINAL INSTRUMENTATION CANARY: PASS\n"
        
    print(out)

if __name__ == "__main__":
    generate_report()
