# HCA Deposition Segmenter — Changelog

**Version:** 1.3
**Date:** 24 April 2026

This file records substantive changes to the HCA Deposition Segmenter skill. Minor corrections (typos, formatting) are not logged. Each entry notes what changed and why.

---

## v1.3 — 24 April 2026

**Added case association threading, occupation qualifiers, and confidence grading.** Depositions are now linked to their legal cases. Compound occupation descriptions are split into primary occupation and qualifier. Each deposition receives a confidence grade (HIGH/MEDIUM/LOW) replacing the binary flag system. Five parser bug fixes from the ff.50r-99v production run.

Key changes from v1.2:

- **Section 5.1 Step 4 refactored.** "Isolate the front matter and capture case metadata" — stripped material above the boundary is now captured rather than discarded, providing the raw material for case association fields.
- **Section 5.1 Step 5 expanded.** Extraction table now includes seven new fields: `occupation_qualifier`, `case_description`, `case_sequence`, `case_id`, `case_date`, `confidence`, `parser_version`.
- **Occupation qualifier parsing rules added.** Compound descriptions (e.g., "Mariner late purser of the Galleote the Black dogg") are split into primary occupation and qualifying detail, with five worked examples.
- **Case association rules added.** Three-signal threading: explicit case description -> new case_id; sequence-only -> inherit from predecessor; short-form -> match to existing case by party names. `case_id` is a running integer within a single run, not persistent across runs.
- **Section 5.3 updated.** New quality flag: `[CASE UNCERTAIN]` for ambiguous case associations.
- **Section 5.4 added: Confidence grade.** HIGH/MEDIUM/LOW summary grade based on extraction quality and flag count. Supplements (does not replace) the individual quality flags.
- **Section 6.2 updated.** Phase 2 annotation format now includes `case_id`, `case_sequence`, and `occupation_qualifier` attributes.
- **Section 8.5 updated.** Liv