# HCA Deposition Segmenter — Test Log

**Version:** 1.0
**Date:** 22 April 2026

This file records the results of each test run of the HCA Deposition Segmenter on different volumes, folio ranges, and use cases. It accumulates over time as the skill is tested more widely.

Each entry records: what was tested, what happened, and whether the skill was modified as a result.

---

## Entry format

Each test entry uses the following fields:

- **Volume:** HCA 13/XX
- **Date range of volume:** approximate period covered
- **Folio range tested:** e.g., f.1r–f.50v
- **Transcription quality:** hand-transcribed / HTR / OCR / mixed
- **Tester:** who ran the test
- **Date of test:** when the test was conducted
- **Ground truth source:** e.g., SOLM database, manual count, none
- **Depositions detected:** number found by the segmenter
- **Ground truth count:** number expected (with notes on counting method)
- **Detection rate:** percentage
- **New patterns encountered:** structural features not seen in previous tests
- **New failure modes:** cases where the segmenter failed or produced incorrect output
- **Skill modified as a result?** yes/no, with brief description of changes
- **Notes:** anything else relevant

---

## Test 1: HCA 13/71, f.1r–f.50v

- **Volume:** HCA 13/71
- **Date range of volume:** mid-1650s (Cromwellian Protectorate)
- **Folio range tested:** f.1r–f.50v (100 pages)
- **Transcription quality:** Hand-transcribed, high fidelity. 708,979 word tokens in full volume; 70.8% non-modern spellings, all genuine C17th scribal forms.
- **Tester:** Colin Greenstreet with Claude (Opus 4.6)
- **Date of test:** April 2026 (iterative, across multiple sessions)
- **Ground truth source:** SOLM database Ver. 15.2 (2 December 2025). Note: SOLM tracks signatures/marks/initials, not depositions — one entry per signoff instance. Marginal annotations create additional entries. SOLM count therefore exceeds deposition count.
- **Depositions detected:** 56
- **Ground truth count:** 57 unique deponents in SOLM for this folio range (from 75 SOLM entries)
- **Detection rate:** 55 of 57 unique deponents confirmed (96%). One undetected (Richard Stevens — no front matter in transcription, only a signature). One apparent gap (Burridge/Bowridge) confirmed as a spelling variant of a detected deponent.
- **Name extraction quality:** 56 of 56 records clean after boundary stripping improvements (100%). Previously 10 of 56 had name pollution from case descriptions, examination clauses, or transcription annotations leaking into the name field.
- **Occupation extraction quality:** 49 of 56 records correct (88%). Seven records produced incorrect or empty occupations due to non-standard preamble structures: ship names parsed as occupations (2), empty due to unusual embedding (2), voyage text leaking in (1), complex biography (1), spelling variant (1).
- **New patterns encountered:**
  - Proctor attribution lines (e.g., "Budd: Suckley)") between case description and examination clause
  - Sequence markers: Rp., dt:, jus, and 14 observed variants (see deposition-structure.md Section 2.4)
  - "The deposition and answers of [Name]" preamble opener
  - "there about" as two-word spelling variant of "thereabouts"
  - Date headings with word ordinals ("The first of April 1656")
  - "4 (sic) 4.us" scribe/transcriber correction pattern
  - Trailing adverbs in names ("James Wilson nowe")
  - Bracketed uncertain readings ("[David Bayly]")
- **New failure modes:**
  - Depositions without any front matter (Richard Stevens — structural ceiling)
  - Ship names parsed as occupations when embedded in extended role descriptions
  - Complex biographical preambles that embed former residences and roles
- **Skill modified as a result?** Yes. The v0.1 SKILL.md was entirely rewritten as v1.0 based on these findings. The `deposition-structure.md` reference file was created to capture all structural knowledge gained. The parser code (`hca_parser.py`) was iteratively improved across ten development cycles.
- **Notes:** This was the development test — the skill was built by testing against this volume. HCA 13/71 is an easy case: hand-transcribed, minimal Latin (Protectorate era), consistent formatting. Performance on other volumes is expected to be lower and will require pattern extensions, parti