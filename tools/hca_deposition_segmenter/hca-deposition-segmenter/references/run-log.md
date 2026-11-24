# HCA Deposition Segmenter — Run Log

**Version:** 1.0
**Date:** 24 April 2026

This file records each production run of the HCA Deposition Segmenter, capturing the use case, instructions given, results obtained, and lessons learned. It complements the `test-log.md` (which records development/testing runs) by tracking production runs where results are saved for downstream use.

---

## Entry format

Each run entry records:

- **Run ID:** Sequential identifier
- **Date:** When the run was conducted
- **Volume:** HCA 13/XX
- **Folio range:** e.g., f.1r–f.49v
- **Use case:** Why this run was conducted
- **Instructions given:** What the researcher specified
- **Parser version:** Which version of the parser code was used
- **Results file:** Where the output was saved
- **Depositions detected:** Count
- **Flagged records:** Count and details
- **Lessons learned:** What was observed that could improve the skill or parser
- **Proposed improvements:** Specific changes suggested

---

## Run 1: HCA 13/71, f.1r–f.49v (Production)

- **Run ID:** 1
- **Date:** 24 April 2026
- **Volume:** HCA 13/71
- **Folio range:** f.1r–f.49v (98 pages, 49 folios)
- **Use case:** First production run. Previous development runs did not save results. Output intended for downstream knowledge graph ingestion.
- **Instructions given:** Run the segmenter on ff.1r-49v. Do not cross-reference SOLM. Save results in structured JSON for downstream use.
- **Parser version:** hca_parser_v4.py
- **Results file:** `WORKSTREAM-HCA/hca_13_71_phase1.json`
- **Depositions detected:** 52
- **Flagged records:** 1 (Thomas Glover — occupation not extracted; no occupation stated in front matter)

### Lessons learned

1. **Context window is adequate for ~50 folios.** The parser ran comfortably on 6,186 lines (98 pages). No truncation or memory issues. The skill's recommended 50-folio limit is conservative but appropriate for human review capacity.

2. **The parser v4 code is the real deliverable, not the skill file alone.** The skill file describes *what* to do; the Python parser operationalises *how*. Future runs should always specify which parser version was used, because the skill file cannot capture every regex decision.

3. **Occupation extraction remains the weakest link.** One record (Thomas Glover) had no occupation in the front matter at all — a genuine absence, not a parser failure. But the occupation field also carries noise: trailing ship descriptions, role qualifications ("late purser of..."), and biographical extensions. The parser extracts the first occupation match, which is usually correct, but downstream consumers need to know that `occupation_raw` may contain substantial trailing text.

4. **Place extraction is reliable but unsophisticated.** The parser extracts everything between "of" and the first occupation term. This works well for simple cases ("of London") but produces long strings for complex cases ("of the parish of Saint Mary Magdalen Bermondsey in the County of Surrey"). No parish normalisation was applied in this run — the parishes.json vocabulary exists but wasn't wired into the parser.

5. **Name normalisation works well.** The ff-convention ("ffrancis" → "Francis"), title stripping ("Captaine" → stripped), and trailing adverb removal ("nowe" → stripped) all performed correctly. Bracketed uncertain readings ("[David Bayly]") were preserved in raw form and cleaned in normalised form.

6. **The two-phase workflow was collapsed to Phase 1 only.** The researcher's use case (knowledge graph ingestion) required structured JSON, not annotated XML. Phase 2 was not needed. This suggests the skill should explicitly note that Phase 2 is optional — it depends on the downstream consumer.

7. **Folio end calculation uses the next deposition's start line.** This means the last deposition in a batch has its folio_end set to the last page in the processed range. If the actual deposition ends earlier (e.g., followed by a gap before the next case), the folio_end is an overestimate. This is acceptable for an inventory but would need refinement for precise document slicing.

### Proposed improvements

| # | Improvement | Priority | Scope |
|---|-------------|----------|-------|
| 1 | Wire parish normalisation into the parser (match `place_raw` against `parishes.json`) | Medium | Parser |
| 2 | Add `occupation_clean` field that strips trailing ship/role descriptions from `occupation_raw` | Medium | Parser |
| 3 | Make Phase 2 explicitly optional in the skill file (note that JSON-only output is a valid end state) | Low | Skill |
| 4 | Add `parser_version` field to the JSON output metadata | Low | Parser |
| 5 | Record the run-log entry automatically as part of the parser output | Low | Parser/Skill |
| 6 | Add a `place_normalised` field using parish matching | Medium | Parser |
| 7 | Test on ff.50r–99v to discover new patterns in the second half of the volume | High | Next run |

---
