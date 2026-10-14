# Handoff: Thesis methodology and IEEE revision
- Date: 2026-10-09 17:15 local
- From: codex
- To: any
- Branch / worktree: codex/activity-center; primary checkout
- Milestone: Owner-requested DOCX revision: LISTEN taxonomy / UNDERSTAND Agent Control / ACT international practices
- Status: done

## Done
- Edited `docs/thesis/Khoa-luan-Le-Dang-Tan-11236199.docx` directly, retaining the owner's existing cover, typography, margins, images and table geometry.
- Aligned introduction, four chapters, conclusion and appendices to the approved three-stage methodology.
- Added SKOS-inspired taxonomy governance, enrichment v3 boundaries, Agent Control runtime/documentation distinction and explicit limits on evidence/budget guarantees.
- ACT distinguishes RICE inspiration from the project's weighted formula. Added discovery, SRE, human–AI interaction, NIST, closed-loop CX and FinOps principles, applicability and limitations.
- 18 verified primary references; IEEE numbering follows first appearance, with 25 linked Word REF fields and bibliography bookmarks.
- Removed unused template material and duplicate Turnitin appendix; repaired scoped TOC, formula list, chapter pagination and repeating table headers using existing styles.
- Final render: 85 physical pages; main text from Mở đầu through Kết luận is 64 pages; 16 tables and 10 original inline images.
- Concurrent ACT v2 changes appeared during this session. Document describes their 18-card/7-lens design and snapshot contract separately from baseline test evidence; does not claim rollout/integration success.

## Evidence
- Frontend `node_modules/.bin/vitest.cmd run`: 10 files / 45 tests passed, exit 0; `tsc --noEmit`: exit 0.
- Backend `.venv/Scripts/python.exe -m pytest -m 'not integration' -q -p no:cacheprovider`: sandbox 86 passed, 1 failed, 5 skipped, 106 deselected (Stanza resource access).
- Same backend command with `STANZA_RESOURCES_DIR=D:/stanza_resources` and sufficient read permissions: 92 passed, 106 deselected, 4 warnings, 65.31 s, exit 0.
- These test runs predate completion of concurrent ACT v2 changes; they are not verification of that extension.
- Bundled document renderer unavailable (no soffice). Used installed Word COM to update fields/save/export, then pypdfium2 to render every page; visual review across the complete manuscript and focused full-size references/formula pages.
- `tmp/thesis-revision/verify_final.py`: PASS ZIP, cover, retained section dimensions/margins, Normal Times New Roman 13/1.3, image bytes/extents, all REF targets, scoped TOC, first-citation order 1–18.
- One table boundary changed by one twip during Word normalization; no material layout change. PDF text check: no field error strings or empty pages.
- Final DOCX SHA256: `bcca8ecc907c499b31fe2baadf4d0d252b99e50da248b18a7ae1fdc67d74a7ec`.

## Not done / gaps
- No new DB integration, full E2E, paid model calls, independent labeled benchmark, causal business-impact study or VPS deployment was performed by this session.
- Signatures and authentic institutional Turnitin report must be supplied by student/institution; no substitutes created.
- Historical FE-12 handoff and `docs/e2e_flow_report.md` claim impact 9→6 with priority 8.10→7.40, inconsistent with default impact weight 0.4. Removed those unverified score values from thesis; original records retained. User informed.

## Blocked / risks
- DOCX is now authoritative for this revision. Older thesis Markdown and `build_docx.py` were not synchronized; rebuilding from them would overwrite current wording, cover and references.
- Numerous unrelated changes/deletions and concurrent application edits already exist; preserved, not committed or reset. No application code was changed by this thesis session.
- Original exact backup: `tmp/thesis-revision/Khoa-luan-before-methodology-2026-10-09.docx` (SHA256 `8b9bf4f32214887298464bcc3aa2d8ae2a78932aad1813d4ce22f80357ca8c03`). QA PDF/PNGs and scripts are under the same temporary directory; not final deliverables.

## Next steps
1. Review the revised DOCX with the supervisor and add real signatures/Turnitin report.
2. When ACT v2 is frozen and independently verified, update only its implementation/evaluation evidence and rerender the same DOCX; do not reuse baseline counts as extension results.
3. If a reproducible document build is desired later, first reconcile its source Markdown and preserve the owner's current format.
