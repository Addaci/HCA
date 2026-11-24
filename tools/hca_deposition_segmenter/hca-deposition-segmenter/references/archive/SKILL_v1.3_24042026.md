---
name: hca-deposition-segmenter
description: 'Segment raw HCA deposition volume files (.txt) into individual depositions with structured metadata. Uses the age formula as primary anchor to detect deposition boundaries, then extracts name, place, occupation, and age from front matter. Two-phase workflow: Phase 1 produces a structured inventory of all depositions found (for human verification); Phase 2 produces annotated output with XML markers at confirmed boundaries. Handles variation in markers, witness block format, language, and transcription quality across the HCA 13 corpus (1570-1685). TRIGGERS: parse depositions, extract depositions, HCA parsing, deposition boundaries, segment depositions, structure HCA volume, HCA segmenter.'
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

**Version:** 1.3
**Date:** 24 April 2026
**Status:** Draft — tested on HCA 13/71 (mid-1650s), ff.1r–99v (two production runs)
**Supersedes:** v1.2 (23 April 2026), archived in `references/archive/`

### Version history

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 1 March 2026 | Initial design document (pre-testing) |
| 1.0 | 22 April 2026 | Post-testing rewrite based on 10 development cycles against HCA 13/71 ff.1r–50v |
| 1.1 | 22 April 2026 | Added Section 7 (Output Preservation): mandatory three-file output structure for every segmenter run, with raw/cleaned/run-notes files saved to `segmenter-runs/`. Updated Section 5.2 to require saving raw output before human review. |
| 1.2 | 23 April 2026 | Added `place_components` structured field to extraction output (Section 5.1 Step 5). Place strings now parsed into `{locality, parish, county, country}` components. Updated Phase 2 annotation format (Section 6.2) and normalisation section (Section 9) accordingly. Driven by downstream requirement: the HCA knowledge graph ingestor needs structured place data to auto-create county-level edges and flag parish-level edges for review. |
| 1.3 | 24 April 2026 | Added case association fields (`case_description`, `case_sequence`, `case_id`, `case_date`) to link depositions to their legal cases (Section 5.1 Steps 4–5). Added `occupation_qualifier` field for compound occupation descriptions. Added per-deposition `confidence` grade (HIGH/MEDIUM/LOW) replacing the binary flag system. Five parser bug fixes from ff.50r–99v production run: "marinner" spelling variant, trailing name punctuation, "-ie" suffix number words, multi-line examined clause false positive, "Cittizen and" livery company pattern. Refactored boundary detection to capture stripped material rather than discarding it. Added `run-log.md` to reference files. |

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
- `references/historic-counties.json` — controlled vocabulary of 86 pre-1832 historic counties (England, Wales, Scotland) with normalised names, country, and spelling variants. Used by the downstream knowledge graph ingestor for county-to-country lookup.

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

### 4.5 Output location

Confirm the output folder for this run. By default, outputs are saved to `WORKSTREAM-HCA/segmenter-runs/`. If the researcher specifies a different location, record it in the run notes. See Section 7 for the mandatory output preservation protocol.

---

## 5. Phase 1 — Segmentation and Structured Report

### 5.1 Detection strategy

The skill uses the **age formula** as its primary anchor for detecting depositions. The age formula — "aged [N] yeares or thereabouts" and its many spelling variants — appears in the front matter of every standard deposition and has distinctive enough phrasing to distinguish it from body text.

**Step 1: Build a folio map.** Scan for page boundaries (`~~~` markers and `HCA 13/XX f.Yr Annotate` headers). Build a mapping from line numbers to folio references. Skip `[BLANK MANUSCRIPT PAGE]` entries.

**Step 2: Scan for age formulae.** Search the text for the age formula pattern. Because the formula frequently splits across two lines, join each line with the next before searching. Deduplicate detections within three lines of each other.

**Step 3: Gather context.** For each detection, gather five lines before the age formula line and one line after. This context block contains the front matter and usually some case-level metadata that needs stripping.

**Step 4: Isolate the front matter and capture case metadata.** Identify the boundary between case-level metadata and the deponent's front matter, using the same boundary markers as before (see `references/deposition-structure.md` Section 3.2 for full detail):

1. Sequence markers (Rp., jus, dt:, numerals)
2. Closing parentheses from case descriptions
3. "Examined upon..." clauses (note: these may span multiple lines — see bug fix note below)
4. Transcription annotations ([CHECK], [XXX], [CENTRE HEADING], ---- separators)
5. "The deposition and answers of..." preamble opener

The key principle: find the **last** boundary marker before "aged," since earlier markers may appear within case descriptions naming other parties.

**New in v1.3:** Instead of discarding the stripped material, **capture it** as case-level metadata. The text above the boundary contains some or all of: a date heading, a case description (long or short form), proctor attributions, an examination clause, and a sequence marker. These are extracted as separate fields in Step 5.

**Bug fix (v1.3):** The examined clause may span multiple lines, particularly when it includes "in the acts of Court" or similar qualifying phrases. The boundary detector must handle multi-line examined clauses to avoid false positives where court procedural language is misidentified as a deponent name.

**Bug fix (v1.3):** "Cittizen and [Occupation]" is a London livery company designation (e.g., "Cittizen and Vintner"). When this pattern appears, "Cittizen and" should be included in the occupation field, not parsed as part of the place string. Add "cittizen" / "citizen" as a recognised prefix that combines with the following occupation term.

**Step 5: Extract metadata fields.** From the isolated front matter and the captured case-level metadata, extract:

| Field | Method | Notes |
|-------|--------|-------|
| `name` | Text before first "of" | Strip titles, ff-convention, trailing adverbs (nowe, late). Strip trailing punctuation (commas, semicolons) |
| `place` | Text between "of" and occupation/aged | May include parish, county, region. Flat string, preserved as-is |
| `place_components` | Parsed from `place` string | Structured object: `{locality, parish, county, country}`. See parsing rules below |
| `occupation` | First recognisable occupation term after place | Match against occupation vocabulary. Handle "Cittizen and [Occupation]" as a combined term |
| `occupation_qualifier` | Text following primary occupation before "aged" | Captures compound descriptions: "late purser of the Galleote the Black dogg", "cheife masters mate and Steevador". Set to `null` when occupation is simple (e.g., just "Mariner") |
| `age` | Numeral or written-out number after "aged" | Parse word-numbers including C17th "-ie" suffix variants (e.g., "fiftie" → 50, "twentie" → 20) |
| `folio_start` | Folio map | First folio of this deposition |
| `folio_end` | Folio map | Last folio before next deposition begins |
| `case_description` | Extracted from stripped material above the front matter boundary | Long form for first deposition in a case; short form for subsequent depositions. May be absent when deposition immediately follows another in the same case. See case association rules below |
| `case_sequence` | Extracted from sequence marker (Rp., 2., 3us., etc.) | The deposition's ordinal position within its case. Parsed from the marker conventions documented in `references/deposition-structure.md` Section 2.4 |
| `case_id` | Assigned by threading logic | A running identifier grouping depositions belonging to the same legal case within a run. See case association rules below |
| `case_date` | Extracted from date heading | The court session date governing this deposition. "The same day" inherits the previous deposition's date. Both raw and ISO forms where parseable |
| `confidence` | Computed from extraction quality | HIGH / MEDIUM / LOW. See Section 5.4 |
| `parser_version` | Recorded in JSON output metadata | The parser script version used for this run |

Mark any field that cannot be confidently extracted as `[NOT EXTRACTED]` with a brief note explaining why.

**Occupation qualifier parsing:**

When `occupation_raw` contains more than the primary occupation term, split it into `occupation` (the normalised primary term) and `occupation_qualifier` (the remaining descriptive text). Examples:

| occupation_raw | occupation | occupation_qualifier |
|---------------|------------|---------------------|
| "Mariner" | Mariner | *null* |
| "Mariner late purser of the Galleote the Black dogg" | Mariner | "late purser of the Galleote the Black dogg" |
| "Mariner late cheife masters mate and Steevador on board the shipp Thomas Bonadventure" | Mariner | "late cheife masters mate and Steevador on board the shipp Thomas Bonadventure" |
| "Mariner a Master of the shipp the Johns Adventure" | Mariner | "a Master of the shipp the Johns Adventure" |
| "Boatswayne of the sayd shipp the Delight" | Boatswain | "of the sayd shipp the Delight" |

The qualifier preserves the scribe's exact wording. It is valuable for downstream NER (ship names, commanders' names, role details) and for understanding the deponent's relationship to the case.

**Case association rules:**

Case threading connects depositions to their legal cases using three signals:

1. **Explicit case description.** When the stripped material above a deposition's front matter contains a case description (identified by closing parentheses and case terms such as "against", "behalfe", "claime", "owners", "concerning"), extract it as `case_description` and assign a new `case_id`.

2. **Sequence-only inheritance.** When a deposition has only a sequence marker (e.g., "2.", "2us") and no case description, it inherits the `case_id` of the immediately preceding deposition. The sequence marker value becomes its `case_sequence`.

3. **Short-form matching.** When a deposition has a short-form case description (naming parties but not restating the full subject matter), match it to an existing `case_id` from earlier in the run by comparing party names. If no match is found, assign a new `case_id`.

The `case_id` is a running integer (1, 2, 3...) assigned within a single run. It does not persist across runs — cross-run case matching is a downstream task.

Where case association cannot be confidently determined, set `case_id` to `null` and flag with `[CASE UNCERTAIN]`.

**Place component parsing rules:**

The `place_components` field breaks the flat `place` string into four hierarchical components. Each component is either a string or `null` if not determinable from the text.

```json
{
  "locality": "Wapping",
  "parish": null,
  "county": "Middlesex",
  "country": null
}
```

Parsing logic:

- **`county`**: Extract from explicit "in the County of [X]" or "in [County]" phrases. Only assign when the text states the county. Do not infer from locality alone.
- **`parish`**: Extract from explicit "of the parish of [X]" or "in the parish of [X]" phrases. Do not infer parish from locality — parish assignments are historically ambiguous (localities straddled parish boundaries) and are handled downstream by the knowledge graph ingestor's review process.
- **`locality`**: The most specific named place after "of" that is not a parish or county qualifier. May be a hamlet, township, ward, liberty, or city name.
- **`country`**: Extract only from explicit textual cues (e.g., "in Zeeland", "in the kingdom of Spaine"). Do not default to "England" — a significant minority of deponents (10–15%, higher in wartime volumes) resided outside England. Set to `null` when the text does not state or clearly imply a country.

When a deponent gives only "of London" with no further specification, set `locality` to `"London"`, `parish` to `null`, `county` to `null` (London was not in a county in the conventional sense), `country` to `null` (the text does not explicitly state "England").

Where a component cannot be confidently parsed, set it to `null` and add a note to the quality flags. The flat `place` string is always preserved alongside `place_components` for manual review.

### 5.2 Human checkpoint — boundary review

**STOP HERE.** Before presenting the report to the researcher for review, **save the raw Phase 1 output** as the raw output file (see Section 7). This file must not be edited after saving. All subsequent corrections happen in the cleaned copy.

Present the researcher with the Phase 1 report. The report includes:

- **Volume summary:** volume number, folio range processed, number of depositions found, number of blank pages skipped, number of uncertain extractions
- **Deposition table:** all depositions with key metadata columns (id, name, occupation, place, age, folio range)
- **Flags section:** listing all extraction failures, uncertain boundaries, and quality notes

The researcher reviews the table against their knowledge of the volume and any available ground truth. They may correct boundaries, identify missed depositions, or flag false positives. All corrections are recorded in the cleaned output file and summarised in the run notes (see Section 7).

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
- `[CASE UNCERTAIN]` — case association could not be confidently determined

### 5.4 Confidence grade

Each deposition receives a summary confidence grade based on extraction quality:

- **HIGH** — all fields extracted cleanly; no quality flags; case association determined
- **MEDIUM** — deposition boundary is solid but one or more metadata fields are uncertain or could not be extracted; or case association is uncertain
- **LOW** — boundary itself is uncertain, multiple fields failed extraction, or the record may be a false positive

The confidence grade summarises the flags — it does not replace them. The individual flags (Section 5.3) provide the detail; the confidence grade provides a quick filter for downstream consumers.

---

## 6. Phase 2 — Annotated Output

### 6.1 Procedure

Take the confirmed boundary list from Phase 1 (with any corrections the researcher has made). Produce a new version of the text with XML-style markers inserted. The original text is preserved exactly — markers are added around it, not substituted for it.

### 6.2 Annotation format

```xml
<deposition id="1" folio_start="f.1r" folio_end="f.3r" confidence="HIGH"
  case_id="1" case_sequence="1">
<metadata>
  <date original="The eleaventh of ffebruary 1655" iso="1655-02-11"/>
  <case description="Williams and Company owners of the ffriendship (Barnaby holding master) against Rowse and others"
    case_id="1" case_sequence="1"/>
  <deponent name="Aron Estes" name_raw="Aron Estes"
    place="Deale in the County of Kent" place_raw="Deale in the County of Kent"
    place_locality="Deal" place_parish="" place_county="Kent" place_country=""
    occupation="Mariner" occupation_raw="Marriner"
    occupation_qualifier="" age="24"
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

## 7. Output Preservation

### 7.1 Principle

Every segmenter run produces data that feeds downstream processes — knowledge graphs, NER pipelines, document slicing. If this data is lost, the provenance chain from primary source to structured output is broken. Segmenter outputs must therefore be saved, versioned, and contextualised as a matter of course, not as an afterthought.

The raw output is also the primary evidence for evaluating the segmenter's performance. Mixing it with human corrections makes it impossible to assess what the tool detected versus what the researcher corrected. Raw and cleaned outputs must remain separate.

### 7.2 Three-file structure

Every segmenter run produces three files:

| File | Contents | Editable after creation? |
|------|----------|--------------------------|
| **Raw output** | Phase 1 inventory exactly as the segmenter produced it | **No — never edited** |
| **Cleaned output** | Copy of the raw output with corrections made during human review | Yes — this is the working file |
| **Run notes** | Experimental conditions, cleaning decisions, and performance observations | Yes — updated during and after review |

### 7.3 Naming convention

Files follow the sandbox naming standard:

```
hca_[volume]_[folio-range]_[type]_v[version]_[DDMMYYYY].[ext]
```

Examples for a run on HCA 13/71 ff.1r–50v on 22 April 2026:

- `hca_13_71_f1r-50v_raw_v1.0_22042026.json`
- `hca_13_71_f1r-50v_cleaned_v1.0_22042026.json`
- `hca_13_71_f1r-50v_run_notes_v1.0_22042026.md`

If the same folio range is re-run (e.g., with an updated skill version or different parameters), increment the version number: `_v2.0_`.

### 7.4 Output location

By default, all three files are saved to:

```
WORKSTREAM-HCA/segmenter-runs/
```

Create this folder if it does not exist. The researcher may specify an alternative location during the interview protocol (Section 4.5); if so, record the actual path in the run notes.

### 7.5 Run notes contents

The run notes file must record, at minimum:

**Experimental conditions:**
- Volume and folio range processed
- Version of the transcription file used (filename and version number)
- Version of the segmenter skill used
- Version of controlled vocabularies used (occupations.json, parishes.json)
- Date of the run
- Who ran it (researcher name)
- Any non-default parameters or settings
- Ground truth source used for verification (if any)

**Results summary:**
- Number of depositions detected
- Number of extraction failures or quality flags
- Detection rate against ground truth (if available)

**Cleaning record:**
- Each correction made to the raw output, with: (a) the deposition id affected, (b) which field was changed, (c) the raw value, (d) the corrected value, (e) the reason for the correction
- Any depositions added that the segmenter missed
- Any false positives removed

**Observations:**
- New patterns encountered not previously documented
- Failure modes that suggest skill improvements
- Notes for future runs on the same or similar volumes

### 7.6 Phase 2 outputs

Phase 2 (annotated text) is a separate output produced after human confirmation. It should also be saved to `segmenter-runs/` using the naming convention:

```
hca_13_71_f1r-50v_annotated_v1.0_22042026.txt
```
Phase 2 outputs are not split into raw/cleaned pairs because they are produced *after* human review — the corrections have already been incorporated. If the researcher later revises boundaries and regenerates the annotated text, save the new version with an incremented version number and note the reason in the run notes.

### 7.7 Accumulation across runs

When a volume is processed in multiple runs (e.g., ff.1r–50v in one session, ff.51r–99v in another), each run produces its own three-file set. A combined inventory may be created as a separate file:

```
hca_13_71_combined_cleaned_v1.0_22042026.json
```

The combined file must record in its metadata which run files it was assembled from, including their version numbers and dates.

---

## 8. Known Limitations

### 8.1 Tested scope

This skill has been tested on **one volume only**: HCA 13/71 (mid-1650s, Cromwellian Protectorate), which is hand-transcribed with high fidelity. See `references/test-log.md` for detailed results. Performance on other volumes — especially machine-transcribed volumes and volumes with heavy Latin — is unknown and will require recalibration.

### 8.2 Detection ceiling

The age formula anchor cannot detect depositions that lack a standard front matter entirely. In HCA 13/71, one deponent (Richard Stevens) appears only as a signature with no preceding front matter. This represents a structural ceiling on detection rate — approximately 1–2% of depositions may be undetectable by this method.

### 8.3 Latin front matter

Earlier volumes (1590s) contain Latin witness blocks where the age formula appears as "Natus Annorum [Roman/Arabic numeral] Testis" rather than "aged N yeares or thereabouts." The current detection patterns do not cover this Latin form. Extending the skill to pre-Commonwealth volumes will require adding Latin detection patterns.

### 8.4 OCR noise

Machine-transcribed volumes will introduce OCR errors that may corrupt the age formula or front matter fields. The skill does not attempt OCR correction. Detection and extraction rates will be lower for these volumes, and more records will carry quality flags.

### 8.5 Occupation extraction

Seven of 56 depositions in the initial test run produced incorrect or empty occupation extractions. These arise from genuinely unusual preamble structures (ship names parsed as occupations, extended biographical descriptions, missing occupations). The v1.3 `occupation_qualifier` field mitigates the compound description problem by separating the primary occupation from qualifying detail, but the underlying extraction still depends on the spelling variant dictionary recognising the primary term.

**Livery company designations** (e.g., "Cittizen and Vintner") are a pattern first observed in ff.50r–99v. The parser must treat "Cittizen and" as a prefix to the occupation, not as part of the place string.

**Spelling variant coverage** is incrementally expanded as new volumes are processed. The variant "marinner" (encountered in ff.50r–99v) was not in the original dictionary. Maintainers should add newly discovered variants to `occupations.json` or the parser's inline variant dictionary after each production run.

### 8.6 Context window constraints

A full volume file (e.g., HCA 13/71 at 3.99 MB) is too large to process in a single pass. Process in sections of up to 50 folios (100 pages), maintaining a running deposition index across sections. The 50-folio limit is driven by human review capacity, not processing capacity — larger runs are technically feasible but produce Phase 1 reports that are difficult to verify.

### 8.7 Case association limitations

Case threading (v1.3) relies on three signals: explicit case descriptions, sequence markers, and short-form matching. Known limitations:

- **Cross-run threading.** `case_id` is assigned within a single run and does not persist across runs. When a case spans the boundary between two runs, it will receive different `case_id` values in each run. Cross-run matching is a downstream task.
- **Ambiguous short forms.** Short-form case descriptions that name only parties (e.g., "Wilkinson against Warren") may match multiple cases if the same parties appear in more than one case. This is flagged as `[CASE UNCERTAIN]`.
- **Missing case descriptions.** Some depositions have neither an explicit case description nor a clear sequence marker. These receive `case_id` of `null`.

---

## 9. Normalisation

The skill extracts both raw (as-transcribed) and normalised forms for three fields: name, occupation, and place. The raw form preserves the scribe's exact spelling. The normalised form enables aggregation and downstream use in knowledge graphs.

Normalisation principles are documented in `references/deposition-structure.md` Section 4. Key conventions:

- **Names:** The "ff" convention (lowercase ff for capital F) is normalised: "ffrancis" → "Francis." Trailing adverbs ("nowe", "late") are stripped. Titles are extracted separately. Trailing punctuation (commas, semicolons) is stripped from the normalised form.
- **Occupations:** Matched against a controlled vocabulary with spelling variant dictionary and fuzzy matching. Accent marks (e.g., "merćhant") are stripped before matching. When the occupation field contains compound descriptions ("Mariner late purser of..."), the primary occupation is extracted as `occupation_normalised` and the qualifying detail as `occupation_qualifier`. Livery company designations ("Cittizen and Vintner") are treated as combined occupation terms.
- **Places:** The flat `place` string is matched against a parish vocabulary (currently City of London parishes only). Places outside the City are correctly flagged as unmatched. Additionally, the `place_components` field parses the place string into structured components (`locality`, `parish`, `county`, `country`) using explicit textual cues — see Section 5.1 Step 5 for parsing rules. Components that cannot be determined from the text are set to `null`; they are never inferred from training knowledge alone.

---

## 10. Downstream Uses

The structured output (JSON records with raw and normalised fields, folio ranges, case associations, and quality flags) feeds into three potential downstream systems, documented in `references/deposition-structure.md` Section 6: knowledge graphs, sliced documents, and RAG databases. The segmenter's output is the common input to all three. Case association data (`case_id`, `case_description`, `case_sequence`) enables downstream systems to group depositions by legal case — essential for knowledge graph construction and for understanding the evidential context of individual depositions.

The planned `hca-ner-identifier` skill will perform named entity extraction from testimony text *after* segmentation boundaries are confirmed. Segmentation first, NER second — the order matters because NER needs to know where each deposition begins and ends.

---

## 11. Reference Files

| File | Purpose |
|------|---------|
| `references/deposition-structure.md` | Internal structure of HCA depositions — what to look for and why |
| `references/occupations.json` | Controlled vocabulary for occupation normalisation (150 types, 14 categories) |
| `references/parishes.json` | Controlled vocabulary for place normalisation (City of London parishes) |
| `references/historic-counties.json` | Controlled vocabulary for county-to-country lookup (86 pre-1832 counties: 39 English, 13 Welsh, 34 Scottish) |
| `references/changelog.md` | Record of skill modifications over time |
| `references/test-log.md` | Results from tests on different volumes and use cases |
| `references/archive/SKILL_v0.1_01032026.md` | Superseded skill file (original design document, pre-testing) |
| `references/archive/SKILL_v1.0_22042026.md` | Superseded skill file (post-testing, before output preservation) |
| `references/archive/SKILL_v1.1_22042026.md` | Superseded skill file (output preservation, before place_components) |
| `references/archive/SKILL_v1.2_23042026.md` | Superseded skill file (place_components, before case associations) |
| `references/run-log.md` | Production run log with per-run metadata, lessons learned, and proposed improvements |

---

## 12. Provenance

This skill was developed through collaborative work between Colin Greenstreet and Claude (Opus 4.6) during parser development sessions in April 2026. The structural observations are grounded in the hand-transcribed text of HCA 13/71 and verified against the SOLM database (Ver. 15.2, 2 December 2025).

The v0.1 SKILL.md (1 March 2026) was a design document written before any parsing work. The v1.0 reflected ten cycles of iterative development on 100 pages of HCA 13/71, producing 56 deposition detections from 57 unique deponents (96% detection rate). The v1.1 added mandatory output preservation (Section 7) to ensure that segmenter outputs are saved, versioned, and contextualised for downstream use and performance evaluation. The v1.2 added structured place component parsing (`place_components` field), driven by the downstream requirement of the HCA knowledge graph ingestor skill, which needs structured locality/parish/county/country data to automate place hierarchy edges and flag ambiguous parish assignments for human review. The v1.3 added case association threading (`case_description`, `case_sequence`, `case_id`, `case_date`), occupation qualifiers (`occupation_qualifier`), and a confidence grading system (HIGH/MEDIUM/LOW), based on two production runs covering ff.1r-99v (81 depositions).
