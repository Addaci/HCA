---
name: hca-deposition-segmenter
description: 'Segment raw HCA deposition volume files (.txt) into individual depositions with structured metadata, generate case overviews with typology tagging, and produce enriched output via SOLM-derived imputation. Three-phase pipeline (Phase 1 segmentation → Phase 1.5 case overview → Phase 1.6 imputation; optional Phase 2 annotated XML). Uses the age formula as primary anchor, captures signoffs (with countersignature awareness for foreign-language depositions), records livery company designations and citizenship status, and produces both attested and imputed place hierarchies (locality → parish → county → country, with Continental provinces). Two-stage human review. Outputs: raw + cleaned + enriched + case-overview + run-notes per run. Handles variation across the HCA 13 corpus (1570-1685). TRIGGERS: parse depositions, extract depositions, HCA parsing, deposition boundaries, segment depositions, structure HCA volume, HCA segmenter.'
---

# HCA Deposition Segmenter

> **Capability:** Document processing
> **Maturity:** Production (run-3 review-validated)
> **Contributor:** Colin Greenstreet
> **Date:** 26 April 2026
> **Period scope:** Early modern (1570–1685)
> **Language scope:** English, with Latin variation in earlier/later volumes; foreign-language depositions handled with countersignature awareness
> **Source type:** High Court of Admiralty depositions (HCA 13 series)
> **Platform:** Cowork
> **Related skills:** my-first-knowledge-graph (downstream consumer); planned hca-ner-identifier (named entity extraction from testimony body, after segmentation)

**Version:** 1.4
**Date:** 26 April 2026
**Status:** Production — three runs completed against HCA 13/71 (ff.1r–149v)
**Supersedes:** v1.3 (24 April 2026), archived in `references/archive/`

### Version history

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 1 March 2026 | Initial design document (pre-testing) |
| 1.0 | 22 April 2026 | Post-testing rewrite based on 10 development cycles against HCA 13/71 ff.1r–50v |
| 1.1 | 22 April 2026 | Added Section 7 (Output Preservation) |
| 1.2 | 23 April 2026 | Added `place_components` structured field |
| 1.3 | 24 April 2026 | Added case association fields, occupation_qualifier, confidence grading; five parser bug fixes from ff.50r–99v production run |
| 1.4 | 26 April 2026 | **Major skill revision** based on Colin Greenstreet's review of run-3 output. **Detection improvements** (A1–A6): relaxed `thereabouts` requirement (catches "aged X yeares" without trailing thereabouts); added "or NEARE thereabouts" variant; added "=\\n" soft-hyphen line-break pre-processing; widened context window from 10 to 20 lines before age formula; added signature audit as standard Step 6; fixed off-by-one bug in `age_line_in_extract` (49% of run-3 detections affected). **Workflow** (G, L, D1): added Phase 1.5 (case overview generation, twice per run); added Phase 1.6 (mandatory imputation pass) producing enriched JSON; introduced running court date state across detections to resolve "the same day" inheritance. **New reference files added to Section 11**: `case-typology.json` v1.0 (10-tag case typology); `place-imputation.json` v1.0 (493 SOLM-derived imputation rules); `historic-counties.json` v1.1 (repaired). **Schema additions (Section 10)**: `street` and `building` sub-fields in place_components; `imputed_parish`, `imputed_county`, `imputed_province`, `imputed_country` sub-fields populated by Phase 1.6; top-level `signoff` nested object (signature/mark/initials + countersignature for foreign-language depositions); `livery_company_designation` and `citizenship_status` top-level fields; `precontest_name` for kinship/relationship-defined deponents; OS/NS dual-date support; `vocabularies_consumed` metadata block; **flag taxonomy revised**: `[NOT EXTRACTED]` retired and replaced with two distinct tags — `[ABSENT IN SOURCE]` (terminal) and `[EXTRACTION FAILED]` (recoverable). **Wiki-source-assembly artefact pattern** documented in Section 11. |

---

## 1. Purpose

This skill segments a raw HCA deposition volume file (.txt) from the [Addaci/HCA GitHub repository](https://github.com/Addaci/HCA) into individual depositions with structured metadata. The input is an unstructured text file containing hundreds of transcribed manuscript pages. The output is a structured inventory of every deposition found, with extracted metadata fields, followed by a case-clustered overview, an imputed-fields enriched version, and (optionally on confirmation) an annotated version of the original text.

The skill is designed to handle significant variation across volumes in the corpus, which spans over a century (1570–1685) and includes both hand-transcribed and machine-transcribed files of varying quality.

It has been tested on HCA 13/71 — see `references/test-log.md` for current test coverage.

---

## 2. What This Skill Does NOT Do

- It does **not** correct OCR or transcription errors. The original text is preserved exactly.
- It does **not** perform scholarly interpretation of the depositions.
- It does **not** extract named entities from testimony body text (ships, places, persons mentioned in testimony). That is the domain of the planned `hca-ner-identifier` skill.
- It does **not** translate Latin passages into English.
- It does **not** normalise spelling in the body text. Normalisation applies only to extracted metadata fields and always preserves the raw form alongside.
- It does **not** generate paragraph case abstracts (one-paragraph descriptions of what each case is about). That requires body-text reading and is deferred to a future Phase 4.

---

## 3. Prerequisites

Before activating this skill, read the following reference files:

- `references/deposition-structure.md` — internal structure of HCA depositions
- `references/occupations.json` — controlled vocabulary of 150 occupation types
- `references/parishes.json` — controlled vocabulary of pre-1666 London parishes
- `references/historic-counties.json` v1.1 — controlled vocabulary of 86 pre-1832 historic counties + 5 non-county jurisdictions (Channel Islands and Isle of Man)
- `references/case-typology.json` v1.0 — 10-tag controlled vocabulary for case-type classification (event, legal-issue, procedural, catchall)
- `references/place-imputation.json` v1.0 — 493 SOLM-derived imputation rules (hamlet→parish, parish→county, locality→county/province, province→country)

Each JSON file contains a `usage` field in its preamble explaining how the skill should consume it.

---

## 4. Interview Protocol

Before beginning segmentation, establish the following with the researcher:

### 4.1 Which volume?

Identify the HCA 13 volume number and its approximate date range. The corpus spans 1570–1685; language, structure, and marker conventions change significantly across that period. Check `references/test-log.md` to see whether this volume has been tested before.

### 4.2 Transcription quality

Hand-transcribed (high fidelity) or machine-transcribed (HTR/OCR with potential errors)? Machine-transcribed volumes will produce lower detection rates and more extraction failures.

### 4.3 Processing scope

A full volume file can be several megabytes — too large to process in a single pass. Agree on the folio range. Up to 50 folios (100 pages) per run is comfortably achievable. The Phase 1 report accumulates across sessions.

### 4.4 Ground truth availability

Does the researcher have ground truth (e.g., the SOLM database)? Note: SOLM tracks signatures/marks (not depositions) and includes marginal annotations that inflate the count above the true deposition count. SOLM verification can be run live or deferred (see §4.4a).

### 4.4a Blind run option

If the researcher specifies a "blind run" (no ground truth comparison during the run), document this in the run notes and defer SOLM verification to a later session.

### 4.5 Output location

Confirm the output folder. By default, outputs are saved to `WORKSTREAM-HCA/segmenter-runs/run-N/`. See Section 7 for the mandatory output preservation protocol.

---

## 5. Phase 1 — Segmentation and Structured Report

### 5.1 Detection strategy

The skill uses the **age formula** as its primary anchor for detecting depositions.

**Step 1: Build a folio map.** Scan for page boundaries (`~~~` markers and `HCA 13/XX f.Yr Annotate` headers). Build a mapping from line numbers to folio references. Skip `[BLANK MANUSCRIPT PAGE]` entries. Handle folio-header typos (e.g., `HC 13/71 f.149r` missing the `A`) with a relaxed regex.

**Step 2: Pre-process line-break artefacts.** The transcription uses `=` and `-` as soft-hyphen line-break markers. Before scanning for the age formula, replace `=\n` and `-\n` with empty string in the joined-pair view. This catches cases like `aged thirty yeares or therea= bouts` (Pieterson missed in run-3).

**Step 3: Scan for age formulae.** Search the text for the age formula pattern:

```
aged (about )?<number> (yeares|yeeres|years|yeres) (or (neare )?(of )?thereabouts)?
```

The trailing `(or (neare )?(of )?thereabouts)?` clause is OPTIONAL (v1.4 change). This catches "aged about 36 yeares" without trailing thereabouts (Warden missed in run-3). Confirmation step (next) filters false positives.

Because the formula frequently splits across two lines, join each line with the next before searching. Deduplicate detections within three lines of each other.

**Step 4: Confirm with deposition formula.** For each candidate detection, scan the next 6 lines for a deposition-formula keyword (`sworne`, `witness`, `deposeth`, `deposed`, `examined`, `made upon`, `maketh answer`). If absent, mark as `[CANDIDATE — UNCONFIRMED]` for human review rather than auto-accept.

**Step 5: Record both line-anchors.** Record TWO line numbers per detection (v1.4 change — fixes off-by-one bug):
- `age_line_join_anchor` — the first line of the joined pair where the regex matched
- `age_line_actual` — the line where the literal word "aged" begins (could be join_anchor or join_anchor+1)

The reviewer should use `age_line_actual` for visual verification; `age_line_join_anchor` is for audit only.

**Step 6: Gather context.** For each detection, gather **20 lines before** the age line (v1.4 change — was 10) and 4 lines after. The wider window catches date headings and long-form case descriptions that previously fell outside.

Maintain a separate **running court-date state** (v1.4 change): when a `date_heading` regex matches anywhere in the volume scan, update the state. When a deposition is detected, attach the most recent prior date as `case_date.attested` (the segmenter already saw it, even if outside the immediate context block). This decouples date attribution from the immediate context window.

**Step 7: Isolate front matter and capture case metadata.** Identify the boundary between case-level metadata and the deponent's front matter using the marker hierarchy from `references/deposition-structure.md` Section 3.2:

1. Sequence markers (Rp., jus, dt:, numerals)
2. Closing parentheses from case descriptions
3. "Examined upon..." clauses (NOTE: may span multiple lines — see §5.1 bug fixes)
4. Transcription annotations ([CHECK], [XXX], [CENTRE HEADING], ---- separators)
5. "The deposition and answers of..." preamble opener

The key principle: find the **last** boundary marker before "aged."

Capture the stripped material as case-level metadata (date heading, case description, proctor attributions, examination clause, sequence marker).

**Bug fixes carried from v1.3:**
- Multi-line `Examined upon` clauses (with "in the acts of Court" or similar qualifying phrases)
- "Cittizen and [Occupation]" livery company designations — see §10 for new field
- Spelling variants: marriner, marryner, mariner, marinner

**Step 8: Extract metadata fields.** From the isolated front matter and captured case-level metadata, extract per Section 10 (Schema). Mark fields per the new flag taxonomy (§5.3):
- `[ABSENT IN SOURCE]` — the field is intentionally not in the deposition
- `[EXTRACTION FAILED]` — the field is in the source but extraction did not recover it

### 5.2 Human checkpoint — boundary review

**STOP HERE.** Save the raw Phase 1 output as `<filename>_raw_v1.0_<DDMMYYYY>.json` per Section 7. **This file must not be edited after saving.**

Present the researcher with the Phase 1 report (case overview from Phase 1.5 should be generated provisionally first, see §6).

The researcher reviews against their knowledge and any ground truth. Corrections go into the cleaned file. **Do not proceed to Phase 1.6 (imputation) until the researcher confirms the cleaned file.**

### 5.3 Quality flags (revised in v1.4)

| Flag | Meaning |
|------|---------|
| `[ABSENT IN SOURCE]` | Field is intentionally not present in the deposition. **Terminal** — do not attempt to recover. Example: Mary Springfeild has no occupation because her front matter identifies her as "wife of Emanuel Springfeild". |
| `[EXTRACTION FAILED]` | Source has a value but extraction did not capture it. **Potentially recoverable** through better OCR, manual review, or re-extraction. |
| `[OCR DAMAGE]` | Front matter text is garbled (e.g., `[GUTTER]` markers, illegible passages); extraction attempted but unreliable. |
| `[LATIN]` | Front matter is in Latin; extraction attempted with lower confidence. |
| `[MULTI-PAGE]` | Deposition spans more than four folios — flag for human attention. |
| `[NO AGE FORMULA]` | No recognisable age formula — deposition detected by other signals only. |
| `[FRAGMENT]` | Deposition at start or end of processed section appears incomplete. |
| `[NON-STANDARD PREAMBLE]` | Front matter structure does not match expected patterns. |
| `[CASE UNCERTAIN]` | Case association could not be confidently determined. |
| `[NAME DISCREPANCY]` | Front matter name and signoff text differ (e.g., front matter "Thomas Bland", signature "Tho: Clante"). Both names preserved; flag for review. |
| `[POSSIBLE DUPLICATE]` | Front matter text-identical to a previously-detected deposition. Flag with diff verification. Common cause: wiki-source assembly doubling (see §11). |
| `[CANDIDATE — UNCONFIRMED]` | Age formula matched but deposition-formula confirmation step did not find a swearing/witnessing keyword. |

The `[NOT EXTRACTED]` flag from prior versions is **retired** and replaced with the more precise `[ABSENT IN SOURCE]` / `[EXTRACTION FAILED]` pair.

### 5.4 Confidence grade

Each deposition receives a summary HIGH/MEDIUM/LOW grade based on extraction quality:

- **HIGH** — all fields extracted cleanly; no quality flags; case association determined
- **MEDIUM** — boundary solid but ≥1 metadata field uncertain or could not be extracted; OR case association uncertain
- **LOW** — boundary itself uncertain, multiple field failures, or possible false positive

**Calibration note (v1.4):** With the widened context window (Step 6) and running court-date state (Step 6), most "[CASE UNCERTAIN — date not in immediate context]" cases that drove run-3's 60% MEDIUM rate should resolve to HIGH. Reviewers should flag if the MEDIUM rate stays above 30%.

### 5.5 Signature audit (new in v1.4)

After detection (Step 8), perform a mandatory signature audit:

1. List all `[SIGNATURE]`, `[MARKE]`, `[MARK]`, `[INITIALS]` markers in the processed range
2. Cross-check each marker against detected depositions: does each signoff fall within or just after a detected deposition?
3. For unmatched signoffs, scan backward 50 lines for a possible front matter that the strict regex missed
4. Add any newly-found depositions to a `missed_depositions_for_human_review` block

This audit caught 5 missed depositions in run-3 (Warden, Dirickson, Pieterson, Daynes, Whittell). It is the operational realisation of the structural-ceiling acknowledgement in §11.2.

### 5.6 Signoff capture (new in v1.4)

For each deposition, scan the END of the deposition text (i.e., the area between the deposition's last article-answer and the next deposition's case description, or the folio break, or the section break) for the signoff. Record per the schema in Section 10:

```
signoff: {
  type: "signature" | "mark" | "initials" | "absent",
  text_raw: <as transcribed, e.g. "Wm Webber [SIGNATURE, RH SIDE]">,
  has_countersignature: bool,
  countersignatory: {
    name_raw: <as transcribed>,
    name_normalised: <ff→F applied>,
    role: "notary publique" | <other professional role>,
    type: "signature"  // interpreters always sign, never use marks
  },
  language_translated_from: <foreign language, if applicable>
}
```

**Notes:**
- ~95% of depositions have exactly one signoff. The rare absent case (~5%) should be tagged `type: "absent"` with notes (e.g., HCA 13/71's Richard Stevens whose signature is the only trace of his deposition).
- Foreign-language depositions are systematically signaled by countersignatures. A notary publique countersigns when an interpreter is present. The notary publique always **signs** (literate by profession), never uses a mark.
- Margin signatures (`[IN LEFT MARGIN]`, `[IN RIGHT MARGIN]`) may produce additional signoff instances within the same deposition. Record the primary (end-of-deposition) signoff in the `signoff` field; record margin signoffs in a separate `margin_signoffs` array.

**Validation note:** This schema is provisional and should be refined as more text is analysed across volumes with different language profiles.

---

## 6. Phase 1.5 — Case Overview Generation (new in v1.4)

After Phase 1, generate a case-clustered overview as a markdown file alongside the JSON outputs.

### 6.1 Generate twice per run

1. **Provisional version, from raw output**, immediately after Phase 1 saves. Helps the reviewer orient before per-detection review.
2. **Canonical version, from cleaned output**, after human review. Reflects all corrections including missed-deposition additions and duplicate removals. Use this for downstream consumers.

### 6.2 Structure

For each case (grouped by `case_id`):

- **Type tag** from `references/case-typology.json` (v1.0 vocabulary: 10 tags). Use grouped reasoning across all depositions in the case (concatenate `case_description`, `occupation_qualifier`, `front_matter_raw`; lowercase; match against signal keywords in vocabulary order; first match wins).
- **Long form description** (taken from first deposition's `case_description`)
- **Short-form variants observed** across the case
- **Date(s)** — single date, range, or "not visible in this run's context"
- **Folio span** (first → last)
- **Per-deposition bullet listing**: detection id, sequence marker, name (normalised), age, occupation (with qualifier), residence, date, folio range
- **Markers**: `[DUPLICATE]`, `[MISSED — add in cleaned]`, `CARRYOVER` (case began before window), `CONTINUES?` (case may extend beyond window)

Append a **case clustering pattern** table (cluster size distribution) and a **typology distribution** table.

### 6.3 Use as Stage B review checkpoint

The case overview is the second Stage A artefact (alongside `_context_blocks.txt`) for human review. The reviewer should:

- Verify case clustering: parties consistent within each case; dates close together (same court session or within reasonable span); shared vessel/subject matter where relevant
- Look for cases with same deponent appearing multiple times → either parallel cases on same vessel (legitimate) or transcription duplicate
- Check carryover and continues markers against expectations
- Surface any cases tagged `other` that the reviewer expected to be classified

---

## 7. Phase 1.6 — Imputation Pass (new in v1.4, MANDATORY)

After the cleaned JSON is produced, **mandatorily** run the imputation pass to produce an enriched JSON.

### 7.1 Inputs

- The cleaned JSON
- `references/place-imputation.json` v1.0 (493 SOLM-derived rules)
- `references/historic-counties.json` v1.1 (county → country + 5 non-county jurisdictions)

### 7.2 Cascade order

For each deposition:

1. **Locality → imputed_parish** (via `hamlet_to_parish` lookup, e.g. Limehouse → Stepney). NOTE: ambiguous-confidence cases (e.g., Wapping, where SOLM shows 78% Stepney / 17% Whitechapel) are intentionally NOT imputed — only HIGH and MEDIUM confidence rules apply.
2. **Parish (attested or imputed) → imputed_county** (via `parish_to_county`, e.g. Stepney → Middlesex)
3. **Locality → imputed_county or imputed_province** for places without parish (via `locality_to_county_or_province`, e.g. Amsterdam → Holland)
4. **County (attested or imputed) → imputed_country** (via `historic-counties.json`, e.g. Middlesex → England)
5. **Province (attested or imputed) → imputed_country** (via `province_to_country`, e.g. Holland → United Provinces)
6. **Date inheritance**: if `case_date.raw == "The same day"` and a prior deposition has an attested ISO date, set `imputed_iso_date` to that date (HIGH confidence).

### 7.3 Principle: imputation NEVER overwrites attested values

If the deposition text states a parish, that's attested — do not modify it. Add `imputed_county` based on the attested parish. Each imputed value carries a `confidence` indicator (HIGH/MEDIUM) and a `source` indicator (e.g., `"place-imputation.json:hamlet_to_parish"`) for downstream traceability.

### 7.4 Extraction-correction flagging

Where the cleaned JSON's `place_components.country` field contains a known province name (from `province_to_country`), flag with `[EXTRACTION CORRECTION SUGGESTED]`. Do NOT overwrite the cleaned JSON; the flag is for the human reviewer to apply manually if desired. Example from run-3: Cornelius Peterson and Jan Polo had `country: "Holland"` and `country: "Zeeland"` (both provinces, not countries).

### 7.5 Output

Produce `<filename>_enriched_v1.0_<DDMMYYYY>.json` containing all cleaned-JSON fields plus the imputed_* fields and any `imputation_flags`. Also produce `<filename>_imputation_summary_v1.0_<DDMMYYYY>.md` documenting what changed.

---

## 8. Phase 2 — Annotated Output (optional)

(Unchanged from v1.3 except where noted.)

### 8.1 Procedure

Take the confirmed boundary list from Phase 1 (with corrections from cleaned). Produce a new version of the text with XML-style markers inserted. Original text preserved exactly.

### 8.2 Annotation format

Now includes signoff and additional v1.4 fields:

```xml
<deposition id="1" folio_start="f.1r" folio_end="f.3r" confidence="HIGH"
  case_id="1" case_sequence="1" case_type="freight-dispute">
<metadata>
  <date original="The eleaventh of ffebruary 1655" iso_os="1655-02-11" iso_ns="1656-02-11"/>
  <case description="..." case_id="1" case_sequence="1"/>
  <deponent name="Aron Estes" name_raw="Aron Estes"
    place="Deale in the County of Kent" place_raw="Deale in the County of Kent"
    place_locality="Deal" place_parish="" place_county="Kent" place_country=""
    place_imputed_country="England"
    place_street="" place_building=""
    occupation="Mariner" occupation_raw="Marriner"
    occupation_qualifier="" age="24"
    livery_company_designation="" citizenship_status=""
    precontest_name=""/>
  <signoff type="signature" text="Aaron Estes" has_countersignature="false"/>
</metadata>

[ORIGINAL TEXT PRESERVED EXACTLY AS IN SOURCE]

</deposition>
```

### 8.3 Handling uncertain passages

(Unchanged from v1.3.)

---

## 9. Output Preservation

### 9.1 Principle

Every segmenter run produces data that feeds downstream processes. Outputs must be saved, versioned, and contextualised.

### 9.2 Five-file structure (revised in v1.4)

| File | Contents | Editable after creation? |
|------|----------|--------------------------|
| **Raw output** | Phase 1 inventory exactly as the segmenter produced it | **No — never edited** |
| **Cleaned output** | Copy of raw with corrections during human review | Yes — working file |
| **Case overview (provisional)** | Case-clustered view from raw, generated immediately after Phase 1 | Regenerate after cleaning, but keep the provisional |
| **Case overview (canonical)** | Case-clustered view from cleaned, generated after review | Yes — regenerate as cleaned changes |
| **Enriched output** | Cleaned + imputation pass added (Phase 1.6 MANDATORY) | Yes — regenerate as imputation rules grow |
| **Run notes** | Experimental conditions, cleaning decisions, performance observations | Yes — updated during and after review |

The four-then-five outputs (raw, cleaned, case overviews × 2 versions, enriched, run notes) plus any Phase 2 annotation form the canonical run record.

### 9.3 Naming convention

Files follow the sandbox naming standard:

```
hca_[volume]_[folio-range]_[type]_v[version]_[DDMMYYYY].[ext]
```

Examples for a run on HCA 13/71 ff.1r–50v on 22 April 2026:
- `hca_13_71_f1r-50v_raw_v1.0_22042026.json`
- `hca_13_71_f1r-50v_cleaned_v1.0_22042026.json`
- `hca_13_71_f1r-50v_case_overview_v1.0_22042026.md` (provisional, from raw)
- `hca_13_71_f1r-50v_case_overview_v1.1_22042026.md` (canonical, from cleaned)
- `hca_13_71_f1r-50v_enriched_v1.0_22042026.json`
- `hca_13_71_f1r-50v_run_notes_v1.0_22042026.md`
- `hca_13_71_f1r-50v_imputation_summary_v1.0_22042026.md`

### 9.4 Output location

Default: `WORKSTREAM-HCA/segmenter-runs/run-N/` (where N is the run number).

### 9.5 Run notes contents

(Substantively unchanged from v1.3 but explicitly extended:)

**Experimental conditions** plus a **`vocabularies_consumed`** block recording the version and date of every reference file used (occupations.json, parishes.json, historic-counties.json, case-typology.json, place-imputation.json). Without this, downstream consumers cannot tell which vocabulary version a given run was processed against.

**Results summary** plus per-run typology distribution.

**Cleaning record** plus extraction-correction items derived from imputation flags.

**Observations** plus new patterns encountered.

---

## 10. Schema (new comprehensive section in v1.4)

This section defines the canonical schema for a deposition record across all output files (raw, cleaned, enriched).

### 10.1 Core fields

| Field | Type | Population | Notes |
|-------|------|------------|-------|
| `id` | int | Segmenter | Sequential within run |
| `name_raw` | string | Segmenter from front matter | As transcribed |
| `name_normalised` | string | Segmenter | ff→F applied; titles stripped; trailing adverbs (nowe, late) stripped; trailing punctuation stripped |
| `age` | int or null | Segmenter | Numeral form |
| `age_raw` | string | Segmenter | As transcribed |
| `place_raw` | string | Segmenter | Flat string from "of [Place]" clause |
| `occupation_raw` | string | Segmenter | As transcribed |
| `occupation_normalised` | string or `[ABSENT IN SOURCE]` or `[EXTRACTION FAILED]` | Segmenter | Matched against occupations.json |
| `occupation_qualifier` | string or null | Segmenter | Compound role detail (e.g., "late Boatswayn of the sayd shipp the Ann") |
| `folio_start`, `folio_end` | string | Segmenter | From folio map |
| `age_line_join_anchor` | int | Segmenter | First line of joined pair where age formula matched |
| `age_line_actual` | int | Segmenter | Line where literal "aged" begins (v1.4 — fixes off-by-one) |

### 10.2 Place components

`place_components` is a nested object with both attested and imputed sub-fields:

| Sub-field | Population | Notes |
|-----------|------------|-------|
| `locality` | Segmenter (attested) | Most specific named place in front matter |
| `parish` | Segmenter (attested) | From "of the parish of [X]" or "in the parish of [X]" |
| `county` | Segmenter (attested) | From "in the County of [X]" |
| `country` | Segmenter (attested) | Only from explicit textual cues |
| `province` | Segmenter (attested) | NEW v1.4 — for Continental places (Holland, Zeeland, Friesland, etc.) |
| `street` | Segmenter (attested) | NEW v1.4 — street/road/lane (e.g., "Bishopsgate streete") |
| `building` | Segmenter (attested) | NEW v1.4 — building/sign (e.g., "the signe of the Bull") |
| `imputed_parish` | Phase 1.6 | `{value, confidence, source, n_confirmations_in_source, matched_via}` |
| `imputed_county` | Phase 1.6 | Same structure |
| `imputed_province` | Phase 1.6 | Same structure |
| `imputed_country` | Phase 1.6 | Same structure |

### 10.3 Date

`case_date` and related:

| Field | Population | Notes |
|-------|------------|-------|
| `case_date.raw` | Segmenter | "The 27th ffebruary 1655" or "The same day" |
| `case_date.iso_os` | Segmenter | NEW v1.4 — Old Style ISO date as recorded in source (year ends 25 March) |
| `case_date.iso_ns` | Segmenter | NEW v1.4 — New Style ISO date (modern Gregorian) — for January–March, OS year + 1 |
| `imputed_iso_date.os` | Phase 1.6 | NEW v1.4 — imputed via "same day" inheritance |
| `imputed_iso_date.ns` | Phase 1.6 | NEW v1.4 — imputed via "same day" inheritance |

### 10.4 Case association

| Field | Population | Notes |
|-------|------------|-------|
| `case_id` | Segmenter | Running integer within run |
| `case_description` | Segmenter | Full text from case description block |
| `case_sequence` | Segmenter | Sequence marker text (Rp., 2us, etc.) |
| `case_type` | Phase 1.5 (case overview) | Tag from `case-typology.json` |

### 10.5 Signoff (new in v1.4)

`signoff` is a nested object — see §5.6 for the schema. Margin signoffs go in a separate `margin_signoffs` array.

### 10.6 Citizenship and livery (new in v1.4)

| Field | Population | Notes |
|-------|------------|-------|
| `livery_company_designation` | Segmenter | Extracted from "Cittizen and [X]" or "citizen and [X]" patterns. Value is the company name (e.g., "Vintners", "Scriveners", "Merchant Taylors"). |
| `citizenship_status` | Segmenter | "citizen of [city]" status separately recorded |

### 10.7 Relationship-defined deponents (new in v1.4)

| Field | Population | Notes |
|-------|------------|-------|
| `precontest_name` | Segmenter | When front matter identifies deponent by relation to a prior witness ("wife of X her precontest", "servant and apprentice of X his precontest"), capture the named referent. |

### 10.8 Quality

| Field | Population | Notes |
|-------|------------|-------|
| `confidence` | Segmenter | HIGH / MEDIUM / LOW |
| `flags` | Segmenter | Array of strings from §5.3 taxonomy |
| `imputation_flags` | Phase 1.6 | Array of strings (e.g., `[EXTRACTION CORRECTION SUGGESTED]`) |
| `front_matter_raw` | Segmenter | The text that was identified as front matter |

### 10.9 Run-level metadata

Top-level fields outside the depositions array:

| Field | Population | Notes |
|-------|------------|-------|
| `vocabularies_consumed` | Segmenter | NEW v1.4 — array of `{file, version, date}` for each reference file used |
| `enrichment_metadata` | Phase 1.6 | Reference files used, statistics |

---

## 11. Known Limitations

### 11.1 Tested scope

This skill has been validated on three runs against HCA 13/71 (ff.1r–149v, total 146 depositions). Other volumes will require recalibration.

### 11.2 Detection ceiling

The age formula anchor cannot detect depositions that lack a standard front matter entirely. The signature audit (§5.5) operationalises detection of these cases.

### 11.3 Latin front matter

Earlier volumes (1590s) contain Latin witness blocks where the age formula appears as "Natus Annorum [N] Testis." The current detection patterns do not cover this Latin form.

### 11.4 OCR noise

Machine-transcribed volumes will introduce OCR errors. Detection and extraction rates will be lower; more records will carry quality flags.

### 11.5 Wapping ambiguity

Per SOLM analysis, Wapping in HCA depositions maps to Stepney parish in 78% of cases and Saint Mary Matfelon (Whitechapel) in 17% (n=171). Below the imputation threshold; therefore Wapping locality does NOT receive an imputed_parish via place-imputation.json. Parish is recorded ONLY when the deposition text explicitly states it.

### 11.6 Wiki-source-assembly artefacts (new in v1.4)

Some transcription `.txt` files assembled from wiki sources may contain duplicated passages — sections of text that appear twice consecutively, often with `|Transcription=`, `|Primary sources=`, or embedded `<u>` markers between them.

**Detection:** When a detected deposition's front matter is text-identical to a previous detection's front matter (same name, place, occupation, age — verifiable via diff), flag as `[POSSIBLE DUPLICATE]` and check for nearby wiki-source markers. Recommend deletion of the duplicate from cleaned output.

**Confirmed in run-3:** Three duplicates around f.140v–141r (Walter Elton, Walter Craxton, William Metcalfe) with `|Transcription=The 22th of Aprill 1656.` and embedded probate metadata (`PROB 11/379/519 Will of William Metcalfe`) post-dating the depositions.

### 11.7 Case association limitations

Cross-run threading: `case_id` is assigned within a single run and does not persist across runs.

### 11.8 OS/NS dating

England used Old Style dating (year ends 25 March) until 1752. The skill records OS dates as attested in the source, plus NS equivalents in the `iso_ns` field. Cross-run analyses must be careful about which is being compared.

---

## 12. Normalisation

(Substantively unchanged from v1.3.)

The skill extracts raw and normalised forms for name, occupation, place. Normalisation principles per `references/deposition-structure.md` Section 4.

**Place normalisation (new in v1.4):** Use `references/place-imputation.json` for spelling variant handling. Apply ff→F normalisation when matching against vocabularies (e.g., "fflushing" → "Flushing" before lookup).

---

## 13. Downstream Uses

(Substantively unchanged from v1.3.)

Three downstream systems: knowledge graph, sliced documents, RAG database. The enriched JSON (Phase 1.6 output) is the recommended input for downstream consumers because it carries both attested and imputed place hierarchies plus case typology tags.

---

## 14. Reference Files (v1.4)

| File | Purpose |
|------|---------|
| `references/deposition-structure.md` | Internal structure of HCA depositions |
| `references/occupations.json` | Controlled vocabulary for occupation normalisation (150 types) |
| `references/parishes.json` | Controlled vocabulary for City of London parish normalisation |
| `references/historic-counties.json` v1.1 | County and non-county jurisdiction lookup (86 counties + 5 non-county jurisdictions: Channel Islands and Isle of Man) |
| `references/case-typology.json` v1.0 | NEW v1.4 — 10-tag case typology vocabulary |
| `references/place-imputation.json` v1.0 | NEW v1.4 — 493 SOLM-derived imputation rules |
| `references/changelog.md` | Record of skill modifications over time |
| `references/test-log.md` | Results from tests on different volumes |
| `references/run-log.md` | Production run log with per-run metadata |
| `references/archive/SKILL_v0.1_01032026.md` through `references/archive/SKILL_v1.3_24042026.md` | Superseded skill files |

---

## 15. Provenance

This skill was developed through collaborative work between Colin Greenstreet and Claude (Opus 4.6 for v0.1 through v1.3; Opus 4.7 for v1.4) during parser-development and review sessions in March–April 2026.

The v0.1 was a design document. v1.0 reflected ten cycles of iterative development on 100 pages of HCA 13/71. v1.1 added output preservation. v1.2 added structured place components. v1.3 added case association threading, occupation qualifiers, and confidence grading. **v1.4 is the first comprehensive review-driven revision**, incorporating Colin Greenstreet's two-stage review of run-3 (ff.100r–149v, 25–26 April 2026), the parsing of SOLM CX/CY columns into a 10-tag case typology, and the parsing of SOLM LG/LH/LI/LJ columns into 493 place-imputation rules.

The v1.4 architecture establishes the **three-phase pipeline** (Phase 1 segmentation → Phase 1.5 case overview → Phase 1.6 imputation, with optional Phase 2 annotation) as the canonical workflow. The five-output-file convention (raw, cleaned, case overviews × 2, enriched, run notes) is now mandatory.

The structural observations and normalisation rules are grounded in HCA 13/71 (run-1 ff.1r–49v, run-2 ff.50r–99v, run-3 ff.100r–149v) and verified against the SOLM database (Ver. 15.2, 2 December 2025).
                                                                                                                                               