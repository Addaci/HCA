---
name: hca-deposition-parser
description: >
  Parse English High Court of Admiralty deposition volume files (.txt) into
  structured deposition records. Two-phase workflow: Phase 1 produces a
  structured report of all depositions found (for human verification of
  boundaries); Phase 2 produces an annotated file with XML markers inserted
  at confirmed boundaries. Handles variation in markers, witness block format,
  language (English/Latin), and OCR quality across volumes spanning 1570–1685.
  TRIGGERS: parse depositions, extract depositions, HCA parsing, deposition
  boundaries, structure HCA volume, segment depositions.
---

# HCA Deposition Parser — Skill File

**Version:** 0.1 (preliminary draft)
**Date:** 1 March 2026
**Status:** Draft — not yet tested against full volumes

---

## 1. Purpose

This skill guides Claude through parsing a raw HCA deposition volume file (.txt) from the Addaci/HCA GitHub repository into individual depositions with structured metadata. The input is an unstructured text file containing hundreds of transcribed manuscript pages. The output is a structured inventory of every deposition found, with extracted metadata, followed (after human confirmation) by an annotated version of the original text.

The skill is designed to handle the significant variation across volumes in the corpus, which spans nearly a century (1570–1685) and includes both hand-transcribed and machine-transcribed files of varying quality.

---

## 2. What the Skill Does NOT Do

- It does **not** correct OCR errors in the transcribed text. The original text is preserved exactly.
- It does **not** perform scholarly interpretation of the depositions.
- It does **not** extract named entities from testimony text (ships, places, persons). That is a separate NER task to be performed after parsing is confirmed.
- It does **not** translate Latin passages into English.

---

## 3. Structural Markers — What to Expect

### 3.1 Reliable markers (present in all volumes examined)

**Page boundaries:** Lines matching `~~~` separate transcribed pages. Each page opens with a header in the format:

```
HCA 13/XX f.Yr Annotate
```

or `f.Yv` for verso pages. Some headers include additional flags such as `[CHECKED]`. The volume number (`13/XX`), folio number (`Y`), and recto/verso indicator (`r`/`v`) are always present.

**Blank pages:** Some folios contain only `[BLANK MANUSCRIPT PAGE]`, indicating no transcription exists. Skip these entirely.

### 3.2 Partially reliable markers

**Deposition separators:** A line consisting of `----` separates depositions in some volumes (confirmed in HCA 13/71 and HCA 13/44) but is absent in others (HCA 13/31). When present, treat as a strong boundary signal. When absent, rely on the convergence of other indicators (Section 3.3).

### 3.3 Content-based boundary indicators

When `----` markers are absent, identify deposition boundaries by the convergence of two or more of the following signals:

**Date lines.** A new deposition typically opens with a date. Formats vary:

- "The eleaventh of ffebruary 1655." (HCA 13/71, English, spelled out)
- "27o Juilij 1622" (HCA 13/44, Latin ordinal + month)
- "3uoº Julij 1622" (HCA 13/44, abbreviated Latin)
- "1o Auqusti 1622" (HCA 13/44, Latin)
- "Die martis 16 Aprilis 1594" (HCA 13/31, full Latin)
- "Die Jovis 18 Aprilis 1594" (HCA 13/31, full Latin)
- "15 Aprilis 1594" (HCA 13/31, abbreviated)

Look for lines containing a day indicator (ordinal number, Latin day name, or English day) followed by a month (English or Latin) and a four-digit year.

**Signature or mark lines.** A deposition typically closes with the deponent's authentication, appearing shortly before the next date line or `----` marker:

- Full signature: "Aaron Estes [SIGNATURE, RH SIDE]"
- Mark with name: "The marke of [MARKE] John hartford [MARKE, RH SIDE]"
- Initials: "Signum 'H' Henricj Lewys [CENTRE]"
- Simple signature: "Richard Bonner"
- Latin signature: "per me william Riche"

Look for lines near the end of a testimony block that contain a proper name (often matching the deponent's name) with optional `[SIGNATURE]`, `[MARKE]`, or `Signum` indicators.

**Witness identification blocks.** Each deposition contains a block identifying the deponent. The format varies by period and language:

*English format (common in later volumes, 1640s–1680s):*
```
Aron Estes of Deale in kent Mariner aged
24 yeares or thereabouts sworne and exámined
```

Pattern: `[Name] of [Place] in [County/Region] [Occupation] aged [N] yeares or thereabouts sworne and examined`

*English with judicial preamble (1620s–1630s):*
```
Richard Bonner of Redrith in the County of Surria
Marriner late Master of the shippe the Dorcas...
sworne and examined before the right worshipfull
Sir Heney Marten Knight Judge of his Majesties highe Court
of Admiralty
```

*Latin format (1590s):*
```
Wilhelmus Rich Civitatis London
haberdasher in vico vocat Breadstreete moram
trahens et com̅orans Natus Annorum xlᵗⁱ Testis
```

Pattern: `[Latin name] [Civitatis/de] [Place] [Occupation] ... Natus Annorum [Roman/Arabic numeral] Testis`

**Case headings.** Many depositions open with a case heading identifying the parties, often in a distinctive format with closing parentheses:

```
Williams and Company against Rowse)
and others)
```

or

```
George Witherly against Robert yeomans)
and William Willott and all others etcetera)
```

**Examination notes.** Lines such as "Examined upon the foresaid allegation" or "Examined upon the bill given in on the behalfe of..." signal the start of testimony within a deposition.

### 3.4 Boundary detection logic

Apply the following rules in order:

1. If `----` is present in the file, use it as the primary boundary marker. Verify each boundary by checking for a date line or witness block nearby.
2. If `----` is absent or inconsistent, identify boundaries by the convergence of: (a) a signature/mark line followed by (b) a date line, with the boundary falling between them.
3. If neither pattern is clear (e.g., heavily garbled OCR), flag the passage as `[BOUNDARY UNCERTAIN]` with a confidence note explaining which signals are present and which are missing.

---

## 4. Phase 1 — Structured Report

### 4.1 Procedure

1. **Receive the input.** The user provides a .txt file or a section of a .txt file from the Addaci/HCA repository.

2. **Scan for page boundaries.** Identify all `~~~` markers and extract the folio reference from each page header. Build a page index: `[{folio: "f.1r", line_start: N, line_end: M}, ...]`. Skip `[BLANK MANUSCRIPT PAGE]` entries.

3. **Scan for deposition boundaries.** Apply the boundary detection logic (Section 3.4). For each boundary found, record:
   - The folio where the deposition begins
   - The folio where it ends
   - Which boundary signals were present (date line, signature, `----`, witness block)
   - Confidence: HIGH (three or more signals converge), MEDIUM (two signals), LOW (one signal or ambiguous)

4. **Extract metadata from each deposition.** For each identified deposition, extract the following fields. Mark any field that cannot be confidently extracted as `[NOT EXTRACTED]` with a brief note.

   | Field | Source | Notes |
   |-------|--------|-------|
   | `date` | Date line | Normalise to ISO 8601 (YYYY-MM-DD). Note original form. For Old Style dates, preserve the original year. |
   | `case_heading` | Case heading lines | Preserve original spelling. May be absent in some depositions. |
   | `deponent_name` | Witness identification block | Preserve original spelling. |
   | `deponent_parish` | Witness identification block | May be absent. |
   | `deponent_county` | Witness identification block | May be absent. |
   | `deponent_occupation` | Witness identification block | Preserve original term (e.g., "Marriner", "Merchant Tailor", "haberdasher"). |
   | `deponent_age` | Witness identification block | Extract numeric value where possible. Note original phrasing. |
   | `authentication_type` | Signature/mark line | One of: `signature`, `mark`, `initials`, `not found` |
   | `authentication_text` | Signature/mark line | The name or mark as it appears |
   | `repeated_before` | Repetition line | Judge name, e.g., "doctor Godolphin" |
   | `folio_start` | Page boundary | e.g., "f.1r" |
   | `folio_end` | Page boundary | e.g., "f.3r" |

5. **Produce the report.** Output a markdown document with:
   - A **volume summary** (volume number, folio range, number of depositions found, number of blank pages, number of uncertain boundaries)
   - A **deposition table** listing all depositions with key metadata columns
   - A **detailed section** for each deposition showing all extracted fields
   - A **flags section** listing all uncertain boundaries, extraction failures, and quality notes

### 4.2 Quality flags

Flag the following conditions in the report:

- `[BOUNDARY UNCERTAIN]` — deposition boundary could not be confidently determined
- `[OCR DAMAGE]` — witness block or date line is garbled; extraction attempted but unreliable
- `[LATIN]` — witness block or date line is in Latin; extraction attempted with lower confidence
- `[MULTI-PAGE DEPOSITION]` — deposition spans more than four folios (flag for human attention as potential misboundary)
- `[NO WITNESS BLOCK]` — no recognisable witness identification pattern found
- `[NO DATE]` — no date line found for this deposition
- `[BLANK PAGES SKIPPED]` — one or more blank pages within or adjacent to this deposition

---

## 5. Phase 2 — Annotated Output

**Do not proceed to Phase 2 until the user has reviewed the Phase 1 report and confirmed or corrected the deposition boundaries.**

### 5.1 Procedure

1. Take the confirmed boundary list from Phase 1 (with any corrections the user has made).

2. Produce a new version of the text with XML-style markers inserted. The original text is preserved exactly — markers are added around it, not substituted for it.

### 5.2 Annotation format

```xml
<deposition id="1" folio_start="f.1r" folio_end="f.3r" confidence="HIGH">
<date original="The eleaventh of ffebruary 1655" iso="1655-02-11"/>
<case>Williams and Company against Rowse and others</case>
<deponent name="Aron Estes" parish="Deale" county="Kent"
  occupation="Mariner" age="24" auth_type="signature" auth_text="Aaron Estes"/>

[ORIGINAL TEXT PRESERVED EXACTLY AS IN SOURCE]

</deposition>
```

Page boundaries (`~~~` and folio headers) are preserved within the annotated text. The `<deposition>` wrapper spans across page boundaries where a deposition crosses folios.

### 5.3 Handling uncertain passages

Where the user has not resolved an uncertain boundary from Phase 1, wrap the passage in:

```xml
<uncertain_boundary reason="no ---- marker; date line present but witness block garbled">
[PASSAGE TEXT]
</uncertain_boundary>
```

---

## 6. Known Limitations and Volume-Specific Notes

### 6.1 OCR quality variation

Machine-transcribed volumes (e.g., HCA 13/44) contain significant OCR errors. The skill does not attempt to correct these. In witness blocks where OCR damage obscures the deponent's name, occupation, or age, extract what is legible and flag the rest as `[OCR DAMAGE]`.

### 6.2 Latin passages

Earlier volumes (1590s) contain substantial Latin, including witness identification blocks, legal formulae, and article headers. The skill extracts metadata from Latin blocks where the pattern is recognisable (e.g., `Natus Annorum` for age, `Civitatis` for place of residence) but flags these as `[LATIN]` with lower confidence.

### 6.3 Deposition fragments

Some depositions at the start or end of a volume file may be incomplete (beginning mid-testimony or ending without a signature). Flag these as `[FRAGMENT — START]` or `[FRAGMENT — END]`.

### 6.4 Scale constraints

A full volume file (e.g., HCA 13/71 at 3.99 MB) is too large to process in a single pass within Cowork's context window. Process in sections of approximately 20–30 folios at a time, maintaining a running deposition index across sections. The Phase 1 report accumulates across all sections before being presented for review.

---

## 7. Relationship to Other Skills and Tools

This skill feeds into the **HCA MCP Server** (see `MCP/HCA_MCP_Server_Design_Memo_v0.1_01032026.md`). The structured output from Phase 2 is a candidate input for the MCP server's deposition-level search index (Option B in the design memo).

The **NER extraction** of ships, places, and persons from testimony text is a separate downstream task, not covered by this skill. It should be performed afte