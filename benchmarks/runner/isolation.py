"""Workspace isolation and verification for GravitasBench."""
import os
import shutil
from pathlib import Path
from typing import Dict, Any

def create_isolated_workspace(base_repo: Path, target_dir: Path, config: str) -> Path:
    """Create a pristine copy of the repo configured for the target scenario."""
    if target_dir.exists():
        shutil.rmtree(target_dir)
    
    # Simple copy for now; in production use `git clone --local` or worktree
    shutil.copytree(base_repo, target_dir, ignore=shutil.ignore_patterns('.git', 'benchmarks/results'))
    
    # Apply configuration
    if config == "BASELINE" or config == "CLAUDE_REFERENCE":
        # Remove any Gravitas skills or hooks to prevent contamination
        remove_gravitas(target_dir)
    elif config == "GRAVITAS_CORE":
        # Keep portable skill, remove native hooks
        remove_native_hooks(target_dir)
    elif config == "GRAVITAS_NATIVE":
        # Keep everything
        pass
        
    return target_dir

def remove_gravitas(workspace: Path):
    """Remove all Gravitas traces from the workspace."""
    for path in ["skills/gravitas", ".agents/skills/gravitas", "plugins/gravitas-antigravity", ".github/workflows/gravitas.yml", "plugin.json"]:
        p = workspace / path
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

def remove_native_hooks(workspace: Path):
    """Remove native hooks but keep portable skill."""
    for path in ["plugins/gravitas-antigravity", "plugin.json"]:
        p = workspace / path
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

def verify_isolation(workspace: Path, config: str) -> bool:
    """Verify that the workspace matches the expected isolation level."""
    gravitas_exists = (workspace / "skills/gravitas").exists() or (workspace / ".agents/skills/gravitas").exists()
    native_exists = (workspace / "plugins/gravitas-antigravity").exists() or (workspace / "plugin.json").exists()
    
    if config == "BASELINE" or config == "CLAUDE_REFERENCE":
        if gravitas_exists or native_exists:
            return False
    elif config == "GRAVITAS_CORE":
        if not gravitas_exists or native_exists:
            return False
    elif config == "GRAVITAS_NATIVE":
        if not gravitas_exists or not native_exists:
            return False
            
    return True
