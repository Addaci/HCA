# HCA Deposition Segmenter

A Claude skill that splits a volume of High Court of Admiralty depositions (HCA 13) into its individual depositions, and records who gave each one, when, in which case, and where the deponent lived.

**Version:** 1.4, 26 April 2026 · **Status:** in production use, reviewed by the historian over three runs on HCA 13/71 (ff.1r to 149v) · **Author:** Colin Greenstreet, with Claude

## Contents

1. [What it is](#1-what-it-is)
2. [Why it matters: the unit of analysis](#2-why-it-matters-the-unit-of-analysis)
3. [What it does](#3-what-it-does)
4. [How to use it](#4-how-to-use-it)
5. [What it produces](#5-what-it-produces)
6. [How well it works, and its limits](#6-how-well-it-works-and-its-limits)
7. [Files](#7-files)

## 1. What it is

Not a program, but a set of written instructions and reference lists for Claude (in Claude Code or Cowork), in Anthropic's skill format. Claude reads `SKILL.md` and follows it, writing and running its own parsing code as it goes. Everything the skill does is readable in plain English in `SKILL.md`.

Its input is one of the volume text files in this repository, for example `HCA_13_71_Full_Volume_Processed_Text_EDITED_Ver.1.3_16062024.txt`.

## 2. Why it matters: the unit of analysis

A volume file is a run of pages, but the page is an accident of binding: one page can hold the end of one case and the start of another. Historians work with other units:

| Unit | What it is | Good for |
| --- | --- | --- |
| Page | One side of a folio, as photographed and transcribed | Images, HTR, citing back to the MarineLives wiki |
| Deposition | One witness's sworn statement, with its date, case and front matter | Who said what, when, and in which case |
| Answer | The witness's answer to one article of the allegation or one interrogatory | Searching: small enough to stay specific |
| Cause | All the documents of one case: depositions, acts of court, interrogatories, exhibits | Linking people, ships and events |

The segmenter turns pages into depositions, which is the step that makes the other units reachable. A case typically has two to five depositions, not always next to each other in the volume (`references/deposition-structure.md`, section 1).

## 3. What it does

1. **Asks first.** Which volume, which folios, how good the transcription is, and whether there is a ground truth to check against (section 4 of `SKILL.md`).
2. **Phase 1: finds the depositions.** Its main anchor is the deponent's age formula ("aged 24 yeares or thereabouts"). It extracts name, parish, place, occupation, age, date and case for each, and grades its confidence.
3. **Human checkpoint.** The historian reviews the list of depositions found before anything else happens.
4. **Phase 1.5: case overviews.** Groups depositions into cases and tags each case by type.
5. **Phase 1.6: fills gaps in places**, for example a hamlet to its parish, but never overwrites what the deponent said.
6. **Phase 2 (optional): marks up the text**, with XML markers at each confirmed boundary.

## 4. How to use it

1. Copy the folder `hca-deposition-segmenter/` into your skills folder (for Claude Code: `.claude/skills/` in your project).
2. Put the volume file you want to process where Claude can read it.
3. Ask, for example: "Segment HCA 13/71, folios 1r to 49v." Claude will ask its questions, then run Phase 1 and stop for your review.

Work in batches of about 50 folios: that suits both Claude's working memory and a historian's review time.

## 5. What it produces

For each run, a structured file of depositions (JSON) with the fields set out in section 10 of `SKILL.md`, case overviews, run notes recording what was asked and what was found, and optionally the annotated text. Section 9 of `SKILL.md` describes the five output files.

## 6. How well it works, and its limits

- On HCA 13/71, ff.1r to 50v, it found 55 of the 57 deponents known from the SOLM database (96%); names were extracted cleanly for 53 of 56 records (95%) (`references/deposition-structure.md`, section 3.4).
- Tested on HCA 13/71 (1655 to 1656) only. Other volumes, with Latin front matter or raw machine transcription, will need checking (`SKILL.md`, section 11).
- A deposition with no front matter in the transcription cannot be found by its age formula.

## 7. Files

All inside the folder `hca-deposition-segmenter/`. Two reference files are derived from Colin Greenstreet's SOLM-2025 database (Signs of Literacy in Manuscripts, Ver. 15.2, 2 December 2025): they hold aggregate patterns and controlled vocabularies built from it, not SOLM records.

| File | What it holds |
| --- | --- |
| `SKILL.md` | The skill: purpose, interview, phases, schema, limits, provenance |
| `references/deposition-structure.md` | The parts of a deposition and how the court recorded them |
| `references/occupations.json`, `parishes.json`, `historic-counties.json` | Reference lists for normalising occupations and places |
| `references/case-typology.json` | Case types, for the case overviews; informed by SOLM-2025 |
| `references/place-imputation.json` | 493 rules for filling in missing parishes and counties, derived from SOLM-2025 |
| `references/run-log.md`, `test-log.md`, `changelog.md` | What was run, what was tested, what changed |
| `references/archive/` | Earlier versions, kept for the record |
