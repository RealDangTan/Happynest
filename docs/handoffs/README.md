# `docs/handoffs/` — Agent Handoff Records

Append-only records passed between AI coding agents (Claude Code ↔ Codex ↔ Cursor ↔ Gemini/Antigravity ↔ human).

**Protocol of record:** [`.claude/skills/agent-handoff/SKILL.md`](../../.claude/skills/agent-handoff/SKILL.md) — read it before writing here.

Quick rules:

1. One file per handoff: `YYYY-MM-DD-<from-agent>-<slug>.md`
2. Never edit or delete another agent's entry; corrections = new entry referencing the old one.
3. Every session that starts/stops mid-milestone leaves an entry — including "no progress" entries.
4. Verify incoming claims (`git log`, tests) before trusting them; report contradictions instead of silently fixing.
5. Sign your commits with trailer `Assisted-by: <agent-name>`; no PII in handoffs, ever.
