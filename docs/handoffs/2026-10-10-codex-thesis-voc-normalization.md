# Handoff: Normalize thesis LISTEN UNDERSTAND ACT attribution
- Date: 2026-10-10 local
- From: codex
- To: any
- Branch / worktree: codex/activity-center; primary checkout
- Milestone: User document annotation on VoC methodology attribution
- Status: done

## Done
- Delivered `docs/thesis/Khoa-luan-Le-Dang-Tan-11236199-VoC.docx`.
- Revised introduction, research method, section 2.1 and conclusion: LISTEN–UNDERSTAND–ACT is adopted from VoC practice within CX/XM; taxonomy governance, agent budgets and approval gates are project implementation choices.
- Added verified Qualtrics Voice of Customer Software reference, renumbered bibliography/citation fields in first-appearance order 1–19.
- Clarified ACT supports decisions; complete improvement execution and CX impact measurement remain unverified.

## Evidence
- Input SHA256 matches prior condensed handoff: 171249270d8c9fe4c1f53e3734735a6501686e68d5c9b05feb156015ace5d65d.
- Primary source: https://www.qualtrics.com/en-au/customer-experience/voice-of-customer/ (accessed 2026-10-10), explicit Listen, Understand, Act sections.
- Bundled render_docx.py failed: soffice.exe missing. Word COM with elevated execution updated fields and exported QA PDF; pypdfium2 rendered all 37 pages.
- Reviewed all-page contact sheets plus full-size introduction, section 2.1 and first references page. No clipping/overlap observed.
- Python assertions passed ZIP integrity, unchanged cover/style XML/section geometry/image content and extents, 6 tables, 19 references, first-citation order, all REF bookmark targets, 37 PDF pages and absence of field error strings.
- Delivered file byte-identical to rendered staging DOCX; SHA256 and details in `tmp/thesis-revision/voc-verification.json`.

## Not done / gaps
- Original filename remains unchanged: Word write lock prevented replacement. Revised sibling file supplied and user informed.
- No application changes, commits or application tests. Existing unrelated changes preserved.
- DOCX remains authoritative; outdated Markdown/build script must not overwrite it.

## Next steps
1. Review revised VoC file; use it as the current manuscript or replace original after closing Word.
