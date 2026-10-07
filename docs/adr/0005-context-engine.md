# ADR-0005: Deterministic Context Engine

Date: 2026-10-07 · Status: accepted

## Context

`impact_graph.py` matched caller files by stem-substring (noisy), scanned
the whole tree per changed file, knew no symbols/imports, and only saw
root-level configs. Session resume dropped decisions, validators, risks,
and scope. No retrieval ranking, no output elision, no durable summary.

## Decisions

1. `gravitas_repo`: single per-root index (mtime+size invalidation, versioned,
   cached at `.gravitas/repo-index.json`) with normalized relations --
   defines/imports/imported-by/callers/tested-by/configured-by/co-changed
   (bounded git log). Symbol/import extraction is regex-based and portable;
   relations are ranking inputs, never completion gates.
2. No vector DB: deterministic retrieval first. `rank_related` returns
   ordinal scores with explicit reasons; `context_for` implements
   target/dependency/subsystem progressive disclosure capped at 60 files.
   Vector retrieval joins only with benchmark evidence it earns.
3. `impact_graph` upgraded in place (same CLI, same legacy keys plus
   importers/symbols/co_changed). Test callers now correctly include
   importing test files -- the pinned expectation was updated deliberately.
4. `elide_output` keeps head/tail plus error lines verbatim and declares
   drops (counts + digest); never paraphrases identifiers.
5. `summarize_session` emits the full durable state (criteria + statuses,
   scope, decisions, failed approaches with causes, validators with event
   hashes, risks, next action); `resume_session` and `gravitas summarize`
   serve it. Free text is quoted verbatim or marked truncated.

## Verification

76 unit tests OK (12 new context tests incl. git co-change, cache refresh,
CLI round-trips); full CI-equivalent gate green.
