"""Metrics calculation for GravitasBench."""
import json
from pathlib import Path
from typing import List, Dict, Any

def calculate_episode_metrics(episode: Dict[str, Any]) -> Dict[str, Any]:
    outcome = episode.get("outcome", {})
    usage = episode.get("usage", {})
    execution = episode.get("execution", {})
    quota = episode.get("quota", {})
    
    metrics = {
        "functional_solve": outcome.get("functional_solve", False),
        "false_completion": outcome.get("false_completion", False),
        "regression": outcome.get("regression", False),
        "scope_violation": outcome.get("scope_violation", False),
        "unauthorized_write": outcome.get("unauthorized_write", False),
        "read_before_write_violation": outcome.get("read_before_write_violation", False),
        "recovery_success": outcome.get("recovery_success", False),
        
        "total_tokens": usage.get("total_tokens", 0),
        "thinking_tokens": usage.get("thinking_tokens", 0),
        "duration_seconds": execution.get("duration_seconds", 0),
        "tool_calls": usage.get("tool_calls", 0),
        "subagents": usage.get("subagents_spawned", 0),
        
        "quota_delta": quota.get("observed_delta")
    }
    return metrics
