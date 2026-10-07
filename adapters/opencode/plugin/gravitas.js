/**
 * Gravitas enforcement shim for OpenCode.
 *
 * Maps OpenCode tool calls onto the normalized Gravitas action model and
 * asks `gravitas guard` (Python policy engine) for a decision. Denials
 * throw, which blocks the tool call. There is no "ask" channel in
 * tool.execute.before, so force_ask resolves to a hard deny here -- a
 * documented, deliberate difference from Antigravity.
 *
 * Requires `gravitas` (pip install gravitas) and python3 on PATH. If the
 * guard is unreachable, the call is allowed with a warning and the reason
 * is logged -- check `gravitas doctor` in the project root.
 */

import { execFileSync } from "node:child_process";

export function toEnvelope(tool, args, directory) {
  const envelope = {
    tool: String(tool || ""),
    args: args && typeof args === "object" ? args : {},
    conversation_id: "",
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
    case "list":
      envelope.tool = "list_dir";
      break;
    default:
      break;
  }
  return envelope;
}

function decide(directory, tool, args) {
  const envelope = toEnvelope(tool, args, directory);
  try {
    const out = execFileSync("gravitas", ["guard", "--envelope", JSON.stringify(envelope)], {
      encoding: "utf8",
      timeout: 10000,
      cwd: directory,
    });
    return JSON.parse(out);
  } catch (error) {
    return { decision: "allow", warning: `gravitas guard unreachable: ${error.message}` };
  }
}

export const GravitasPlugin = async ({ directory }) => {
  return {
    "tool.execute.before": async (input) => {
      const verdict = decide(directory, input.tool, input.output?.args ?? input.args ?? {});
      if (verdict && verdict.decision === "deny") {
        throw new Error(`Gravitas denied ${input.tool}: ${verdict.reason || "policy decision"}`);
      }
    },
  };
};
