# MCP Integration Guide

Connect GRAVITAS agents to real tools via Model Context Protocol (MCP).
This turns GRAVITAS from a behavioral skill into a fully-wired agent system.

---

## What is MCP?

MCP (Model Context Protocol) gives agents access to external tools:
filesystem, git, GitHub, databases, browsers, and more.
GRAVITAS uses MCP to give each specialized agent the right tool access.

---

## Recommended MCP Servers

### 1. Filesystem MCP — for file operations
Gives agents read/write access to your codebase.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"],
      "description": "Read/write project files"
    }
  }
}
```

**GRAVITAS usage:**
- Explore agent: read-only (don't give write access to Explore)
- General agent: read + write
- Verify agent: read-only + run commands

---

### 2. Git MCP — for history and diff
```json
{
  "mcpServers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "/path/to/project"],
      "description": "Git history, diff, blame, log"
    }
  }
}
```

**GRAVITAS usage:** All agents use for recon.
```
git log --oneline -10 -- [file]  → what changed recently
git diff HEAD -- [file]           → uncommitted changes
git blame [file]                  → who changed what line
```

---

### 3. GitHub MCP — for PR/issue context
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token" },
      "description": "GitHub PRs, issues, reviews"
    }
  }
}
```

**GRAVITAS usage:**
- Read issue context before implementing
- Post VERDICT as PR comment
- Check CI status before claiming done

---

### 4. Postgres MCP — for database work
```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"],
      "description": "Run queries, inspect schema"
    }
  }
}
```

**GRAVITAS usage:**
- Check schema before writing migrations
- Verify data before/after data changes
- EXPLAIN ANALYZE for performance work

---

### 5. Shell/Bash MCP — for running tests
```json
{
  "mcpServers": {
    "shell": {
      "command": "npx",
      "args": ["-y", "mcp-shell"],
      "description": "Run shell commands (tests, lint, build)"
    }
  }
}
```

**GRAVITAS usage:** Verify agent runs the full verification chain.

---

## Tool Isolation per Agent

Map MCP tools to agents following GRAVITAS isolation rules:

```json
{
  "agents": {
    "explore": {
      "mcpServers": ["filesystem:read", "git"],
      "note": "Read-only — no write tools"
    },
    "plan": {
      "mcpServers": ["filesystem:read", "git"],
      "note": "Read-only — no write tools"
    },
    "general": {
      "mcpServers": ["filesystem:read-write", "git", "shell"],
      "note": "Full tools — implementation agent"
    },
    "verify": {
      "mcpServers": ["filesystem:read", "shell", "git"],
      "note": "Read + run — no write tools"
    }
  }
}
```

---

## Antigravity MCP Configuration

For Antigravity users, configure in your workspace:

```json
// .antigravity/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "description": "Project filesystem"
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."],
      "description": "Git history and diff"
    },
    "shell": {
      "command": "npx",
      "args": ["-y", "mcp-shell"],
      "allowedCommands": [
        "tsc --noEmit",
        "eslint",
        "vitest run",
        "pytest",
        "cargo test",
        "go test ./...",
        "bash skills/gravitas/scripts/verify.sh"
      ],
      "description": "Run verification commands"
    }
  }
}
```

---

## Full Wiring Example

With MCP configured, the GRAVITAS Explore agent can:

```
1. List all TypeScript files in src/auth/
2. Read src/auth/session.ts:20-30
3. Run: git log --oneline -10 -- src/auth/session.ts
4. Run: grep -rn "SESSION_TIMEOUT" src/
→ Returns structured findings without manual file references
```

And the Verify agent can:

```
1. Run: tsc --noEmit
2. Run: eslint . --max-warnings 0
3. Run: vitest run --reporter=verbose
4. Parse output → issue VERDICT: PASS or VERDICT: FAIL
→ Fully automated verification gate
```

---

## Security Notes

- Filesystem MCP: restrict to project directory only (never `/`)
- Shell MCP: use `allowedCommands` allowlist — never unrestricted shell
- GitHub MCP: use a token with minimum required scopes
- Never give Explore or Plan agents write access to filesystem or shell
