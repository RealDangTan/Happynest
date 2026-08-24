---
name: agent-handoff
description: Use when starting OR ending any work session in this repo as an AI agent (Claude Code, Codex CLI, Cursor, Gemini/Antigravity, human) — establishes the multi-agent handoff protocol check docs/handoffs/ for open work, claim milestone ownership, verify incoming claims before trusting them, and leave an append-only handoff record when stopping. Triggers on "handoff", "take over", "continue from", "codex worked here", "bàn giao", "tiếp tục công việc của agent khác".
---

# Agent Handoff Protocol

Multiple AI agents work on this repo across sessions and tools. This protocol prevents two failure modes: **duplicate/conflicting work** and **trusting unverified claims**.

## Core files

- `docs/handoffs/` — append-only handoff records. One file per handoff; never edit another agent's entry.
- `AGENTS.md` — shared ground rules; always read FIRST.
- Active plan: `docs/plans/` phase table (see AGENTS.md §CURRENT PHASE).

## When STARTING a session

1. Read `AGENTS.md`, then the active mission plan.
2. Read the newest entries in `docs/handoffs/` addressed to you (`To:` = your agent name or `any`). Newest first.
3. **Verify, don't trust.** For every claim that matters to your task:
   - `git log --oneline -15` + `git status` — does reality match the claimed state?
   - Files claimed created/edited exist and contain what's claimed.
   - Run the relevant test command (`uv run pytest` for backend) if the entry claims tests pass.
4. If verification contradicts the entry → do NOT silently fix or delete. Note it in your own new handoff entry and tell the user.
5. Claim ownership out loud (to the user) and in your eventual handoff entry. One agent owns one milestone at a time.

## When STOPPING a session

ALWAYS leave a handoff file — even with zero progress (a "no progress" entry is cheaper than another agent redoing discovery). File naming:

```
docs/handoffs/YYYY-MM-DD-<from>-<slug>.md      e.g. 2026-08-24-claude-code-spike-s2-fallback.md
```

Required template (keep it under ~60 lines):

```markdown
# Handoff: <one-line title>
- Date: YYYY-MM-DD HH:MM local
- From: claude-code | codex | cursor | gemini | human
- To: <agent-name> | any
- Branch / worktree: <branch name or .claude/worktrees/<name>>
- Milestone: <plan file, e.g. docs/plans/02-spikes-core-s1-s2-s3-s6.md>
- Status: done | in-progress | blocked | review-requested

## Done
## Evidence            # commands actually run + outcomes (test counts, exit codes)
## Not done / gaps
## Blocked / risks     # reference docs/decisions.md entries if applicable
## Next steps          # concrete, ordered; enough to resume without re-discovery
```

Also update the Status column of the phase table in `docs/plans/00-index.md` if your milestone status changed.

## Rules

1. **Append-only.** Never rewrite, "clean up", or delete another agent's handoff. Corrections go into a NEW entry referencing the old one.
2. **Commit trailers:** each agent signs its commits with `Assisted-by: <agent-name>` so history shows who did what. Never remove another agent's trailer.
3. **No PII in handoffs** — same boundary as everywhere else (raw feedback content stays out).
4. **Isolation:** parallel agents work in separate git worktrees (see the `using-git-worktrees` skill); never share one working tree simultaneously.
5. **Scope discipline carries over:** a blocker you inherit gets logged in `docs/decisions.md` per AGENTS.md Hard Rule 7 — do not silently expand scope to work around it.
6. Handoff language: English or Vietnamese, whichever is clearest; keep commands/code verbatim.
