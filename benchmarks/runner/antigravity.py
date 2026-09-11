#!/usr/bin/env python3
"""Antigravity CLI harness execution for GravitasBench."""
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

def run_episode(
    cwd: Path,
    prompt: str,
    model_slug: str,
    output_dir: Path,
    timeout_seconds: int = 600,
    sandbox_enabled: bool = True
) -> Dict[str, Any]:
    """Execute a task using the Antigravity CLI and capture stream-json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_events_path = output_dir / "raw-events.jsonl"
    stderr_path = output_dir / "stderr.log"
    
    cmd = [
        "/Users/uday/.local/bin/agy",
        "--model", model_slug,
        "--output-format", "stream-json",
        "--dangerously-skip-permissions",
        "--print", prompt
    ]
    if sandbox_enabled:
        cmd.append("--sandbox")
    
    events: List[Dict[str, Any]] = []
    start_time = time.time()
    
    try:
        with open(stderr_path, "wb") as stderr_file:
            process = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=stderr_file,
                text=True
            )
            
            with open(raw_events_path, "w") as raw_file:
                if process.stdout:
                    for line in process.stdout:
                        raw_file.write(line)
                        raw_file.flush()
                        try:
                            event = json.loads(line.strip())
                            events.append(event)
                        except json.JSONDecodeError:
                            pass
                            
            process.wait(timeout=timeout_seconds)
            terminal_status = f"exited_{process.returncode}"
    except subprocess.TimeoutExpired:
        process.kill()
        terminal_status = "timeout"
    except Exception as e:
        terminal_status = f"error_{str(e)}"
        
    end_time = time.time()
    
    usage = {
        "input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0, 
        "total_tokens": 0, "cache_read_tokens": 0, "turns": 0, "tool_calls": 0
    }
    conversation_id = None
    final_status = None
    
    for event in events:
        if event.get("event") == "init":
            conversation_id = event.get("conversation_id")
            
        if event.get("event") == "step_update":
            su = event.get("step_update", {})
            if su.get("step_type") == "tool" and su.get("state") == "ACTIVE":
                usage["tool_calls"] += 1
                
        if event.get("event") == "result":
            res = event.get("result", {})
            final_status = res.get("status")
            u = res.get("usage", {})
            for k in usage:
                if k in u:
                    usage[k] = u[k]
            if "num_turns" in res:
                usage["turns"] = res["num_turns"]
            
    if terminal_status == "exited_0" and final_status:
        terminal_status = final_status
            
    return {
        "execution": {
            "conversation_id": conversation_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": end_time - start_time,
            "terminal_status": terminal_status,
            "infrastructure_failure": "error" in terminal_status or terminal_status == "timeout"
        },
        "usage": usage,
        "raw_events_count": len(events)
    }
