---
name: hca-deposition-segmenter
description: 'Segment raw HCA deposition volume files (.txt) into individual depositions with structured metadata. Uses the age formula as primary anchor to detect deposition boundaries, then extracts name, place, occupation, and age from front matter. Two-phase workflow: Phase 1 produces a structured inventory of all depositions found (for human verification); Phase 2 produces annotated output with XML markers at confirmed boundaries. Handles variation in markers, witness block format, language, and transcription quality across the HCA 13 corpus (1570–1685). TRIGGERS: parse depositions, extract depositions, HCA parsing, deposition boundaries, segment depositions, structure HCA volume, HCA segmenter.'
---

# HCA Deposition Segmenter

> **Capability:** Document processing
> **Maturity:** Draft
> **Contributor:** Colin Greenstreet
> **Date:** 22 April 2026
> **Period scope:** Early modern (1570–1685)
> **Language scope:** English, with Latin variation in earlier/later volumes
> **Source type:** High Court of Admiralty depositions (HCA 13 series)
> **Platform:** Cowork
> **Related skills:** my-first-knowledge-graph (downstream consumer), hca-ner-identifier (planned; named entity extraction from testimony text, to be performed after segmentation is confirmed)

**Version:** 1.0
**Date:** 22 April 2026
**Status:** Draft — tested on HCA 13/71 (mid-1650s), not yet tested on other volumes
**Supersedes:** hca-deposition-parser v0.1 (1 March 2026), archived in `references/archive/`

---

## 1. Purpose

This skill segments a raw HCA deposition volume file (.txt) from the [Addaci/HCA GitHub repository](https://github.com/Addaci/HCA) into individual depositions with structured metadata. The input is an unstructured text file containing hundreds of transcribed manuscript pages. The output is a structured inventory of every deposition found, with extracted metadata fields, followed (after human confirmation) by an annotated version of the original text.

The skill is designed to handle significant variation across volumes in the corpus, which spans over a century (1570–1685) and includes both hand-transcribed and machine-transcribed files of varying quality. However, it has so far been tested only on HCA 13/71 — see `references/test-log.md` for current test coverage.

---

## 2. What This Skill Does NOT Do

- It does **not** correct OCR or transcription errors. The original text is preserved exactly.
- It does **not** perform scholarly interpretation of the depositions.
- It does **not** extract named entities from testimony text (ships, places, persons mentioned in testimony). That is a separate NER task — see the planned `hca-ner-identifier` skill.
- It does **not** translate Latin passages into English.
- It does **not** normalise spelling in the body text. Normalisation applies only to extracted metadata fields (name, occupation, place), and always preserves the raw form alongside the normalised form.

---

## 3. Prerequisites

Before activating this skill, read the following reference files:

- `references/deposition-structure.md` — documents the internal structure of HCA depositions as observed during parser development. Essential for understanding what the skill looks for and why.
- `references/occupations.json` — controlled vocabulary of 150 occupation types from MarineLives, with categories and usage instructions for spelling variant matching.
- `references/parishes.json` — controlled vocabulary of pre-1666 London parishes from MarineLives, with normalised names, geo-coordinates, and usage instructions for matching.

Each JSON file contains a `usage` field in its preamble explaining how the skill should consume it during metadata extraction (Step 5).

---

## 4. Interview Protocol

Before beginning segmentation, establish the following with the researcher:

### 4.1 Which volume?

Identify the HCA 13 volume number and its approximate date range. This matters because the corpus spans 1570–1685 and the language, structure, and marker conventions change significantly across that period. Check `references/test-log.md` to see whether this volume has been tested before.

### 4.2 Transcription quality

Is the volume hand-transcribed (high fidelity, as with HCA 13/71) or machine-transcribed (HTR/OCR, with potential errors)? Machine-transcribed volumes will produce lower detection rates and more extraction failures. Set expectations accordingly.

### 4.3 Processing scope

A full volume file can be several megabytes — too large to process in a single pass within Cowork's context window. Agree on the folio range to process in this session. Up to 50 folios (100 pages, recto + verso) per run is comfortably achievable; larger runs are technically possible but produce Phase 1 reports that are unwieldy for human review. The recommended maximum is 50 folios per run. The Phase 1 report accumulates across sessions.

### 4.4 Ground truth availability

Does the researcher have ground truth data for this volume? The SOLM database (Signs of Literacy in Manuscripts) provides signoff counts for many HCA 13 volumes and can serve as a verification baseline, though it tracks signatures/marks/initials (not depositions) and includes marginal annotations that inflate the count above the true deposition count.

---

## 5. Phase 1 — Segmentation and Structured Report

### 5.1 Detection strategy

The skill uses the **age formula** as its primary anchor for detecting depositions. The age formula — "aged [N] yeares or thereabouts" and its many spelling variants — appears in the front matter of every standard deposition and has distinctive enough phrasing to distinguish it from body text.

**Step 1: Build a folio map.** Scan for page boundaries (`~~~` markers and `HCA 13/XX f.Yr Annotate` headers). Build a mapping from line numbers to folio references. Skip `[BLANK MANUSCRIPT PAGE]` entries.

**Step 2: Scan for age formulae.** Search the text for the age formula pattern. Because the formula frequently splits across two lines, join each line with the next before searching. Deduplicate detections within three lines of each other.

**Step 3: Gather context.** For each detection, gather five lines before the age formula line and one line after. This context block contains the front matter and usually some case-level metadata that needs stripping.

**Step 4: Isolate the front matter.** Strip case-level metadata from each context block using boundary markers. The stripping logic applies patterns in this order (see `references/deposition-structure.md` Section 3.2 for full detail):

1. Sequence markers (Rp., jus, dt:, numerals)
2. Closing parentheses from case descriptions
3. "Examined upon..." clauses
4. Transcription annotations ([CHECK], [XXX], [CENTRE HEADING], ---- separators)
5. "The deposition and answers of..." preamble opener

The key principle: find the **last** boundary marker before "aged," since earlier markers may appear within case descriptions naming other parties.

**Step 5: Extract metadata fields.** From the isolated front matter, extract:

| Field | Method | Notes |
|-------|--------|-------|
| `name` | Text before first "of" | Strip titles, ff-convention, trailing adverbs (nowe, late) |
| `place` | Text between "of" and occupation/aged | May include parish, county, region |
| `occupation` | Last recognisable occupation term before "aged" | Match against occupation vocabulary |
| `age` | Numeral or written-out number after "aged" | Parse word-numbers (e.g., "fifty three" → 53) |
| `folio_start` | Folio map | First folio of this deposition |
| `folio_end` | Folio map | Last folio before next deposition begins |

Mark any field that cannot be confidently extracted as `[NOT EXTRACTED]` with a brief note explaining why.

### 5.2 Human checkpoint — boundary review

**STOP HERE.** Present the researcher with the Phase 1 report before proceeding. The report includes:

- **Volume summary:** volume number, folio range processed, number of depositions found, number of blank pages skipped, number of uncertain extractions
- **Deposition table:** all depositions with key metadata columns (id, name, occupation, place, age, folio range)
- **Flags section:** listing all extraction failures, uncertain boundaries, and quality notes

The researcher reviews the table against their knowledge of the volume and any available ground truth. They may correct boundaries, identify missed depositions, or flag false positives.

**Do not proceed to Phase 2 until the researcher confirms the boundary list.**

### 5.3 Quality flags

Flag the following conditions in the report:

- `[EXTRACTION UNCERTAIN]` — one or more metadata fields could not be confidently extracted
- `[OCR DAMAGE]` — front matter text is garbled; extraction attempted but unreliable
- `[LATIN]` — front matter is in Latin; extraction attempted with lower confidence
- `[MULTI-PAGE]` — deposition spans more than four folios (flag for human attention as potential misboundary)
- `[NO AGE FORMULA]` — no recognisable age formula found (deposition detected by other signals only)
- `[FRAGMENT]` — deposition at start or end of processed section appears incomplete
- `[NON-STANDARD PREAMBLE]` — front matter structure does not match expected patterns

---

## 6. Phase 2 — Annotated Output

### 6.1 Procedure

Take the confirmed boundary list from Phase 1 (with any corrections the researcher has made). Produce a new version of the text with XML-style markers inserted. The original text is preserved exactly — markers are added around it, not substituted for it.

### 6.2 Annotation format

```xml
<deposition id="1" folio_start="f.1r" folio_end="f.3r" confidence="HIGH">
<metadata>
  <date original="The eleaventh of ffebruary 1655" iso="1655-02-11"/>
  <case>Williams and Company against Rowse and others</case>
  <deponent name="Aron Estes" name_raw="Aron Estes" parish="Deale" county="Kent"
    occupation="Mariner" occupation_raw="Marriner" age="24"
    auth_type="signature" auth_text="Aaron Estes"/>
</metadata>

[ORIGINAL TEXT PRESERVED EXACTLY AS IN SOURCE]

</deposition>
```

Page boundaries (`~~~` and folio headers) are preserved within the annotated text. The `<deposition>` wrapper spans across page boundaries where a deposition crosses folios.

Both raw (as-transcribed) and normalised forms are recorded in the metadata attributes.

### 6.3 Handling uncertain passages

Where the researcher has not resolved an uncertain boundary from Phase 1, wrap the passage in:

```xml
<uncertain_boundary reason="no age formula; signature present but front matter garbled">
[PASSAGE TEXT]
</uncertain_boundary>
```

---

## 7. Known Limitations

### 7.1 Tested scope

This skill has been tested on **one volume only**: HCA 13/71 (mid-1650s, Cromwellian Protectorate), which is hand-transcribed with high fidelity. See `references/test-log.md` for detailed results. Performance on other volumes — especially machine-transcribed volumes and volumes with heavy Latin — is unknown and will require recalibration.

### 7.2 Detection ceiling

The age formula anchor cannot detect depositions that lack a standard front matter entirely. In HCA 13/71, one deponent (Richard Stevens) appears only as a signature with no preceding front matter. This represents a structural ceiling on detection rate — approximately 1–2% of depositions may be undetectable by this method.

### 7.3 Latin front matter

Earlier volumes (1590s) contain Latin witness blocks where the age formula appears as "Natus Annorum [Roman/Arabic numeral] Testis" rather than "aged N yeares or thereabouts." The current detection patterns do not cover this Latin form. Extending the skill to pre-Commonwealth volumes will require adding Latin detection patterns.

### 7.4 OCR noise

Machine-transcribed volumes will introduce OCR errors that may corrupt the age formula or front matter fields. The skill does not attempt OCR correction. Detection and extraction rates will be lower for these volumes, and more records will carry quality flags.

### 7.5 Occupation extraction

Seven of 56 depositions in the test run produced incorrect or empty occupation extractions. These arise from genuinely unusual preamble structures (ship names parsed as occupations, extended biographical descriptions, missing occupations). The occupation extraction is the weakest part of the pipeline and will improve as more volumes expose more patterns.

### 7.6 Context window constraints

A full volume file (e.g., HCA 13/71 at 3.99 MB) is too large to process in a single pass. Process in sections of up to 50 folios (100 pages), maintaining a running deposition index across sections. The 50-folio limit is driven by human review capacity, not processing capacity — larger runs are technically feasible but produce Phase 1 reports that are difficult to verify.

---

## 8. Normalisation

The skill extracts both raw (as-transcribed) and normalised forms for three fields: name, occupation, and place. The raw form preserves the scribe's exact spelling. The normalised form enables aggregation and downstream use in knowledge graphs.

Normalisation principles are documented in `references/deposition-structure.md` Section 4. Key conventions:

- **Names:** The "ff" convention (lowercase ff for capital F) is normalised: "ffrancis" → "Francis." Trailing adverbs ("nowe", "late") are stripped. Titles are extracted separately.
- **Occupations:** Matched against a controlled vocabulary with spelling variant dictionary and fuzzy matching. Accent marks (e.g., "merćhant") are stripped before matching.
- **Places:** Matched against a parish vocabulary (currently City of London parishes only). Places outside the City are correctly flagged as unmatched.

---

## 9. Downstream Uses

The structured output (JSON records with raw and normalised fields, folio ranges, and quality flags) feeds into three potential downstream systems, documented in `references/deposition-structure.md` Section 6: knowledge graphs, sliced documents, and RAG databases. The segmenter's output is the common input to all three.

The planned `hca-ner-identifier` skill will perform named entity extraction from testimony text *after* segmentation boundaries are confirmed. Segmentation first, NER second — the order matters because NER needs to know where each deposition begins and ends.

---

## 10. Reference Files

| File | Purpose |
|------|---------|
| `references/deposition-structure.md` | Internal structure of HCA depositions — what to look for and why |
| `references/occupations.json` | Controlled vocabulary for occupation normalisation (150 types, 14 categories) |
| `references/parishes.json` | Controlled vocabulary for place normalisation (City of London parishes) |
| `references/changelog.md` | Record of skill modifications over time |
| `references/test-log.md` | Results from tests on different volumes and use cases |
| `references/archive/SKILL_v0.1_01032026.md` | Superseded skill file (original design document, pre-testing) |

---

## 11. Provenance

This skill was developed through collaborative work between Colin Greenstreet and Claude (Opus 4.6) during parser development sessions in April 2026. The structural observations are grounded in the hand-transcribed text of HCA 13/71 and verified against the SOLM database (Ver. 15.2, 2 December 2025).

The v0.1 SKILL.md 