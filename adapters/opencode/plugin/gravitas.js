/**
 * Gravitas enforcement shim for OpenCode.
 *
 * Maps OpenCode tool calls onto the normalized Gravitas action model and
 * asks `gravitas guard` (Python policy engine) for a decision. Denials
 * throw, which blocks the tool call. There is no "ask" channel in
 * tool.execute.before, so force_ask resolves to a hard deny here -- a
 * documented, deliberate difference from Antigravity.
 *
 * OpenCode V1/V2 both invoke `tool.execute.before` as
 * `(input {tool, sessionID, callID}, output {args})`. Tool arguments live
 * in the SECOND parameter; reading them from `input` yields `{}` and would
 * silently bypass enforcement, so this shim requires `(input, output)`.
 *
 * Failure policy (fail-closed): when protection is enabled, an unreachable
 * guard binary, timeout, nonzero exit, unparseable output, or unknown
 * verdict DENIES the call. Read-only tools with explicit empty args are
 * still evaluated by the guard; mutating tools (bash/edit/write/patch)
 * with missing arguments are denied locally without consulting the guard.
 * The shim never shells to itself (it invokes `gravitas guard` only).
 *
 * Path identity: file paths are forwarded verbatim and canonicalized by
 * the guard (realpath + volume-aware case/Unicode folding, see
 * canonical_path/path_key in gravitas_action.py). Do not normalize here:
 * a lexical `..` collapse ignores symlinks, and NFC/lowercase folding
 * names a different file on Linux, so either would let an out-of-scope
 * write look in-scope.
 *
 * Requires `gravitas` (pip install gravitas) and python3 on PATH.
 */

import { execFileSync } from "node:child_process";
import { appendFileSync, chmodSync, lstatSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";

const MUTATING_TOOLS = new Set(["bash", "edit", "write", "patch"]);
const READ_EVIDENCE_TOOLS = new Set(["read"]);
const COMPLETION_TOOLS = new Set(["bash", "edit", "write", "patch"]);

function hasMutatingArgs(tool, args) {
  if (!MUTATING_TOOLS.has(tool)) return true;
  if (!args || typeof args !== "object") return false;
  if (tool === "bash") return Boolean(args.command);
  return Boolean(args.filePath || args.path);
}

export function toEnvelope(tool, args, directory, sessionID = "") {
  const envelope = {
    tool: String(tool || ""),
    args: args && typeof args === "object" ? args : {},
    conversation_id: typeof sessionID === "string" ? sessionID : "",
    workspace_roots: directory ? [directory] : [],
    host: "opencode",
    event: "before_action",
  };
  const a = envelope.args;
  switch (envelope.tool) {
    case "read":
      envelope.tool = "view_file";
      envelope.args = { AbsolutePath: a.filePath || a.path || "" };
      break;
    case "edit":
    case "write":
      envelope.tool = "write_to_file";
      envelope.args = { TargetFile: a.filePath || a.path || "" };
      break;
    case "patch":
      envelope.tool = "replace_file_content";
      envelope.args = { target_file: a.filePath || a.path || "" };
      break;
    case "bash":
      envelope.tool = "run_command";
      envelope.args = { CommandLine: a.command || "" };
      break;
    case "grep":
      envelope.tool = "grep_search";
      break;
    case "glob":
      envelope.tool = "find_by_name";
      break;
    case "list":
      envelope.tool = "list_dir";
      break;
    default:
      break;
  }
  return envelope;
}

function decide(directory, tool, args, sessionID = "") {
  const envelope = toEnvelope(tool, args, directory, sessionID);
  let raw;
  try {
    raw = execFileSync("gravitas", ["guard", "--envelope", JSON.stringify(envelope)], {
      encoding: "utf8",
      timeout: 10000,
      cwd: directory,
    });
  } catch (error) {
    const reason = `gravitas guard unreachable (fail-closed): ${error.message}. Run gravitas doctor.`;
    console.error(`[gravitas] deny ${tool}: ${reason}`);
    return { decision: "deny", reason };
  }
  let verdict;
  try {
    verdict = JSON.parse(raw);
  } catch (error) {
    const reason = `gravitas guard output unparseable (fail-closed): ${error.message}`;
    console.error(`[gravitas] deny ${tool}: ${reason}`);
    return { decision: "deny", reason };
  }
  if (!verdict || (verdict.decision !== "allow" && verdict.decision !== "deny")) {
    const reason = `gravitas guard returned unknown verdict (fail-closed): ${raw.slice(0, 200)}`;
    console.error(`[gravitas] deny ${tool}: ${reason}`);
    return { decision: "deny", reason };
  }
  return verdict;
}

function recordOpencodeRead(directory, sessionID, file, succeeded) {
  if (!directory || !file) return;
  if (!succeeded) return; // failed reads must never authorize later writes
  if (typeof sessionID !== "string" || !sessionID) {
    console.error("[gravitas] cannot record read without a session id (fail-closed: no read evidence stored)");
    return;
  }
  try {
    mkdirSync(join(directory, ".gravitas"), { recursive: true });
    appendFileSync(
      join(directory, ".gravitas", "opencode-reads.jsonl"),
      JSON.stringify({ session: String(sessionID || ""), file: String(file), source: "read" }) + "\n"
    );
  } catch {
    // Telemetry must never block the tool call; the guard stays fail-closed
    // on its own path and simply sees no recorded read.
  }
}

function readTargetFor(tool, normalizedEnvelope) {
  if (tool !== "read") return "";
  return normalizedEnvelope?.args?.AbsolutePath || "";
}

function readSucceeded(output) {
  if (!output || typeof output !== "object") return false;
  return output.success !== false && !output.error;
}

function completionArgs(tool, args) {
  if (tool === "bash") {
    const command = typeof args?.command === "string" ? args.command : "";
    return {
      command: command.replace(
        /((?:api[_-]?key|token|password|secret|authorization)\s*[:=]\s*)(["']?)[^\s"'&;]+/gi,
        "$1[REDACTED]"
      ),
    };
  }
  const filePath = args?.filePath || args?.path;
  return typeof filePath === "string" ? { filePath } : {};
}

function recordCompletion(directory, input, output) {
  const tool = input?.tool;
  if (!COMPLETION_TOOLS.has(tool)) return;
  const sessionID = input?.sessionID || input?.sessionId;
  if (typeof sessionID !== "string" || !sessionID) {
    console.error(`[gravitas] cannot record ${tool} completion without a session id`);
    return;
  }
  if (typeof directory !== "string" || !directory) {
    console.error(`[gravitas] cannot record ${tool} completion without a workspace directory`);
    return;
  }
  const args = input?.args ?? output?.args ?? {};
  const result = output && typeof output === "object" ? output : {};
  const event = {
    session_id: sessionID,
    tool,
    args: completionArgs(tool, args),
    success: result.success !== false && !result.error,
    timestamp: new Date().toISOString(),
  };
  const path = join(directory, ".gravitas", "opencode-completions.jsonl");
  try {
    const parent = dirname(path);
    mkdirSync(parent, { recursive: true, mode: 0o700 });
    if (process.platform !== "win32") chmodSync(parent, 0o700);
    try {
      if (lstatSync(path).isSymbolicLink()) {
        throw new Error("completion ledger must not be a symbolic link");
      }
      chmodSync(path, 0o600);
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    appendFileSync(path, `${JSON.stringify(event)}\n`, { encoding: "utf8", mode: 0o600 });
  } catch (error) {
    console.error(`[gravitas] failed to record ${tool} completion: ${error.message}`);
  }
}

export const GravitasPlugin = async ({ directory }) => {
  return {
    "tool.execute.before": async (input, output) => {
      const tool = input?.tool;
      const sessionID = input?.sessionID || input?.sessionId || "";
      const args = output?.args ?? {};
      if (typeof tool !== "string" || !tool) {
        throw new Error("Gravitas denied call: missing tool name in hook input");
      }
      if (!hasMutatingArgs(tool, args)) {
        throw new Error(
          `Gravitas denied ${tool}: mutating tool called with missing arguments (fail-closed)`
        );
      }
      const verdict = decide(directory, tool, args, sessionID);
      if (verdict && verdict.decision === "deny") {
        throw new Error(`Gravitas denied ${tool}: ${verdict.reason || "policy decision"}`);
      }
      if (verdict?.stale_validator_criteria?.length) {
        console.warn(
          `[gravitas] prior validator evidence is stale for: ${verdict.stale_validator_criteria.join(", ")}`
        );
      }
      // Read evidence is recorded only in tool.execute.after on success:
      // recording in .before would authorize writes for reads that then fail.
    },
    "tool.execute.after": async (input, output) => {
      const tool = input?.tool;
      const sessionID = input?.sessionID || input?.sessionId || "";
      const args = output?.args ?? {};
      if (typeof tool === "string" && READ_EVIDENCE_TOOLS.has(tool)) {
        const target = readTargetFor(tool, toEnvelope(tool, args, directory, sessionID));
        recordOpencodeRead(directory, sessionID, target, readSucceeded(output));
      }
      recordCompletion(directory, input, output);
    },
  };
};
