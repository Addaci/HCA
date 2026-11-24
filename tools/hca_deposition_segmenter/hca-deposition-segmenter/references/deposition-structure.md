# HCA Deposition Structure — Reference File

**Version:** 1.2
**Date:** 23 April 2026
**Source volume:** HCA 13/71 (mid-1650s, Cromwellian Protectorate)
**Status:** Empirically derived from parser development on f.1r–f.50v (100 pages, 56 depositions)

This reference file documents the internal structure of High Court of Admiralty depositions as observed in the hand-transcribed text of HCA 13/71. It captures what the parser encountered, what worked, what failed, and what will need recalibration for other volumes in the corpus (HCA 13/20 to HCA 13/79, spanning 1570–1685).

The knowledge here was built iteratively through ten cycles of parser development, not from a specification. It should be treated as a working document that will grow as additional volumes are processed.

---

## 1. The Deposition as a Unit

A deposition is a sworn oral statement given by a named individual (the "deponent") in response to questions put by a notary public of the English High Court of Admiralty. The notary writes down the answers, capturing the gist in legal language rather than verbatim speech. Each deposition is a discrete unit within a legal case.

A single legal case typically generates between two and five depositions, though the range runs from one to roughly fifteen. The depositions in a case are not always contiguous in the volume — depositions from other cases may be interleaved between them, particularly when the court heard multiple cases on the same day.

---

## 2. Structure of a Deposition

A deposition in HCA 13/71 has the following components, in order. Not every component appears in every deposition.

### 2.1 Date heading

A line recording the court session date. Format in HCA 13/71 is English with Old Style dating:

```
The 12th of ffebruary 1655.
The eleaventh of ffebruary 1655
The same day
The 29th of February 1655
The first of April 1656
```

"The same day" indicates the deposition was heard on the same date as the preceding one. The "first" form (as in "The first of April 1656") uses an ordinal word rather than a numeral.

Date headings are often marked `[CENTRE HEADING]` in the transcription, indicating centred text in the manuscript. They are sometimes preceded by a `----` separator line.

**Volume variation note:** Earlier volumes (1590s) use Latin dating: "Die martis 16 Aprilis 1594." The amount of Latin in dating rises and falls across the corpus, with less Latin during the Cromwellian Protectorate (1650s) and more before and after.

### 2.2 Case description

Identifies the legal case. Appears in two forms.

**Long form** — used for the first deponent in a case. Describes the parties and the subject matter. Typically spans two to four lines, with closing parentheses at the end of each line:

```
Wright and Company owners of the)
ffriendship (Barnaby holding master))
against Lenthall and others.)
```

```
On the behalfe of John Graene of London)
Merchant concerning his losse in the shipp)
the Lilly of Barnstable.)
```

**Short form** — used for subsequent deponents in the same case. Names only the parties, without describing the subject matter:

```
William Wilkinson against James Warren )
```

```
The claime of the said Lauson in the)
hare in the feilds.)
```

Or may be omitted entirely if the deposition immediately follows another in the same case and the case is implied.

The closing parentheses are a consistent feature of both long and short form case descriptions in HCA 13/71 and serve as a reliable boundary marker. They distinguish case-level text from testimony text.

**Volume variation note:** The parenthetical formatting with closing parentheses appears consistent across the volumes examined so far, but this needs verification across the full corpus.

### 2.2a Proctor attribution

Immediately after the case description (in either form), one or more proctor (notary) names may appear, also with closing parentheses:

```
William Wilkinson against James Warren )
Budd: Suckley)
```

Here "Budd" and "Suckley" are proctors — legal professionals acting for the parties. The colon separates the proctors for opposing sides: Budd for Wilkinson, Suckley for Warren. This is a proctor attribution line, not part of the case description.

Occasionally three proctor names appear. The reason is not established — possible explanations include a third party to the case (an intervener or third-party claimant), or a proctor in a different procedural role.

**Proctors identified in HCA 13/71:** Budd (sometimes "Mr Budd"), Suckley, Smith/Smyth, Francklyn/Francklin (with ff-convention: ffrancklyn/ffrancklin), Cheeke, Colquiste/Colquite, Clements. Seven proctors in total, with spelling variants. Many of these names recur across adjacent volumes, with occasional additions or retirements.

**Parser implication:** Proctor names must not be confused with litigant names or deponent names. Recognising the proctor vocabulary for a volume provides a reliable signal for distinguishing case-level metadata from front matter. The closing parenthesis after the proctor line marks the end of the case-level block.

### 2.3 Examination clause

States what the deponent is being examined upon. Follows the case description:

```
Exámined upon an allegation on the
behalfe of the said Wright
and Company.
```

```
Examined upon the foresaid allegation
```

```
Examined upon the said Interrogatories.
```

```
Examined upon an Allegation on the behalfe
of the said Sheafe Ashurst and Companie.
```

Two types of examination: upon an **Allegation** (the initial set of questions, answered in numbered Articles) and upon **Interrogatories** or **Cross Interrogatories** (a second set of questions, also numbered). A deponent may be examined on either or both.

The examination clause sometimes includes accent marks in the transcription (e.g., "Exámined"), reflecting the transcriber's notation of manuscript features. These need Unicode NFD normalisation for pattern matching.

### 2.4 Sequence marker

A marker indicating the deponent's position within the case. Immediately precedes the front matter. Variants observed in HCA 13/71:

| Marker | Meaning | Notes |
|--------|---------|-------|
| `Rp .1.` | Repetit 1 (first deponent) | Arabic numeral |
| `Rp. .jus.` | Repetit primus (first deponent) | Latin: j = Roman numeral 1, us = primus |
| `Rp. .j.` | Repetit primus (first deponent) | Shortened Latin |
| `jus./.` | Primus | Standalone, no "Rp." prefix |
| `jus/` | Primus | Variant punctuation |
| `.j.` | Primus | Minimal form |
| `Rp. 4.` | Repetit 4 (fourth deponent) | Higher numbers are Arabic |
| `Rp.2` | Repetit 2 | No space before numeral |
| `Rp.` | Repetit (number omitted) | Bare marker |
| `dt: 3.` | Deponit 3 (third deponent) | Latin "deponit" = "he deposes." Identified by Colin Greenstreet; not yet confirmed against a palaeographical reference |
| `3 ./` | Third deponent | Numeral with separator |
| `4 (sic) 4.us` | Fourth deponent | Scribe or transcriber correction |
| `2.us/` | Secundus (second deponent) | Latin ordinal |
| `1:us` | Primus | Variant punctuation |

**Consistency:** The sequence marker is **not** present in every deposition. The parser cannot rely on it as a universal boundary. When present, it is the most reliable single signal that the front matter follows immediately after.

### 2.5 Front matter

The deponent's identifying information. This is the core target for the parser. Structure:

```
[Name] of [Place] [Occupation] aged [Age] yeares or thereabouts sworne and examined
```

**Name** may include titles (Captaine, Mr, Sir) and the C17th convention of lowercase "ff" for capital F ("ffrancis" = Francis). Names may be enclosed in square brackets in the transcription, indicating an uncertain reading: `[David Bayly]`.

**Place** follows "of" and may include parish, county, and region: "of the parish of Saint Mary Magdalen Bermondsey in Southwarke", "of London", "of Wapping in the County of Middlesex", "of the Liberty of the Tower of London."

**Occupation** follows the place, before "aged": "Mariner", "Merchant", "Goldsmith", "Shipwright." May include qualifiers: "Mariner late cheife masters mate and Steevador on board the shipp Thomas Bonadventure." May be absent for some deponents.

**Age** follows "aged" and precedes the swearing formula. Formats:

- Numeric: "aged 24 yeares or thereabouts"
- Numeric with period: "aged 25. yeares or there about"
- Written out: "aged forty yeares or thereabouts"
- Mixed: "aged about 36 yeares"
- With "being sworne": "aged 30 yeares, being sworne"

**Swearing formula** closes the front matter: "sworne and examined", "sworne and exámined", "a Wittnes sworne and examined saith as followeth videlicet", "a witnes produced sworne and examined."

**Spelling variation in the age formula** is extensive. Observed variants:

- "yeares" / "yeeres" / "years" / "yeres"
- "thereabouts" / "therabouts" / "there about" / "ther abouts"
- "or thereabouts" / "of thereabouts" (interchangeable in C17th usage)

The front matter frequently splits across two lines in the transcription, particularly at the age formula. The parser must join adjacent lines for detection.

**Unusual front matter structures** observed:

- "The deposition and answers of Charles hilliard of London Goldsmith aged 40 yeares or thereabouts" — uses "The deposition and answers of" instead of beginning with the name directly.
- "James Wilson nowe of London Merchant formerly Agent for the State of England at Cadiz in the kingdom of Spaine" — "nowe" (= now) is an adverb modifying the place, not part of the name.
- Extended occupational descriptions that embed ship names and roles: "Mariner late purser of the Galleote the Black dogg", "late Gunner of the shipp or Galliot the hound or Black-dogg (derrick hendricks Commander)."

### 2.6 Body — Answers to Articles

The substantive testimony. Structured as numbered responses to the Articles of the Allegation:

```
To the first article of the said Allegation hee saith and deposeth That...
To the second article hee saith That...
To the rest hee is not examined by direction of the producent.
```

Numbering may skip articles the deponent was not asked about. Some depositions answer only selected articles and note this explicitly.

### 2.7 Body — Interrogatories (optional)

A second set of questions, sometimes called "Cross Interrogatories," examined separately:

```
To the first Interrogatorie hee answereth and saith That...
To the second Interrogatorie...
```

Not every deposition has interrogatories. When present, they follow the answers to the allegation articles.

### 2.8 Repetition clause

A note that the deposition was repeated before a named judge:

```
Repeated before doctor Godolphin./.
```

### 2.9 Signoff

The deponent's authentication at the end of the deposition. Three types:

- **Signature:** "Aaron Estes [SIGNATURE, RH SIDE]"
- **Mark:** "The marke of [MARKE] John hartford [MARKE, RH SIDE]"
- **Initials:** Rare in HCA 13/71

The signoff is normally at the end of the deposition, with one signoff per deposition. However, side annotations in the left or right margin (marked `[IN LEFT MARGIN]` or `[IN RIGHT MARGIN]` in the transcription) may also carry the deponent's signature, creating additional signoff instances within the same deposition.

The SOLM database (Signs of Literacy in Manuscripts) tracks each signoff instance as a separate entry. This means the SOLM entry count for a volume exceeds the number of depositions — it counts signatures, not depositions.

---

## 3. Boundary Detection — Lessons from Parser Development

The parser uses the age formula ("aged N yeares or thereabouts") as its primary anchor for detecting depositions. This is the most reliable single signal in HCA 13/71: every deposition with a standard front matter contains it.

### 3.1 What works

**Age formula as anchor.** Searching for the age formula and then gathering context lines before it reliably locates the front matter. The formula's distinctive phrasing distinguishes it from body text.

**Two-line joining.** The age formula frequently splits across consecutive lines. Joining the current line with the next line before searching catches these splits.

**Deduplication.** When two adjacent lines both contain parts of the age formula, the two-line joining technique can produce duplicate detections. Skipping any detection within three lines of the previous one eliminates these.

**Folio map.** Building a mapping from line numbers to current folio markers allows computation of folio start, folio end, and folio range for each deposition without re-scanning.

### 3.2 Boundary stripping

The text gathered around the age formula typically includes case-level metadata (case description, examination clause, sequence marker) that must be stripped before extracting the deponent's name. The stripping logic applies a sequence of patterns:

1. **Sequence markers** (Rp., jus, dt:, numerals) — these are the most reliable boundary between case metadata and front matter.
2. **Closing parentheses** — mark the end of case descriptions.
3. **"Examined upon..." clause** — may precede the name when no sequence marker is present.
4. **Transcription annotations** — [CHECK], [XXX. dt.], [CENTRE HEADING], ---- separators.
5. **"The deposition and answers of"** — an alternative front matter opener.

The stripping must find the **last** boundary marker before "aged," since earlier markers may appear within case descriptions that name other parties.

### 3.3 What the parser cannot detect

**Depositions without an age formula.** Richard Stevens appears in HCA 13/71 only as a signature — his preamble and front matter are not present in the transcription. The parser cannot detect depositions that lack the front matter entirely.

**Depositions with severely non-standard preambles.** The parser handles the variants documented above, but genuinely novel structures will produce extraction failures that require manual review.

### 3.4 Detection rate

Against the SOLM ground truth for HCA 13/71 f.1r–f.50v:

- SOLM records: 75 entries (tracking signatures/marks, not depositions)
- SOLM unique deponents: 57
- Parser detections: 56
- Match rate: 55 of 57 unique deponents confirmed (96%)
- Undetected: Richard Stevens (no front matter in transcription), and Burridge/Bowridge confirmed as a spelling variant (same person, detected under "Bowridge")
- Clean name extraction: 53 of 56 records (95%) after boundary stripping improvements

---

## 4. Normalisation Principles

The parser extracts both raw (as-transcribed) and normalised forms for names, occupations, and places. The raw form preserves the scribe's exact spelling. The normalised form enables aggregation and knowledge graph construction.

### 4.1 Names

Raw: "ffrancis Rois", "hilliard", "James Wilson nowe"
Normalised: "Francis Rois", "Hilliard", "James Wilson"

The "ff" convention (lowercase ff for capital F) is a consistent C17th scribal practice, not a transcription error. "Nowe" and "late" are adverbs modifying place of residence ("now of London", "late of Dover") and should be stripped from the normalised name.

### 4.2 Occupations

Raw: "Marriner", "merćhant", "Boatswayne", "sailer"
Normalised against: `occupations.json` (14 categories, 143 terms)

The normalisation uses a spelling variant dictionary and fuzzy matching. Accent marks in the transcription (e.g., "merćhant") require Unicode NFD stripping before matching.

Occupational descriptions in HCA depositions are often compound: "Mariner late cheife masters mate and Steevador." The parser extracts the primary occupation term. Extended role descriptions (ship roles, former positions) are preserved in the raw text but not normalised.

### 4.3 Places

Raw: "Wapping in the County of Middlesex", "the parish of Saint Mary Magdalen Bermondsey"
Normalised against: `parishes.json` (118 City of London parishes)

The parish vocabulary covers City of London parishes only. Places outside the City (Wapping, Deptford, Limehouse, Shadwell, foreign ports like Flushing and Danzig) are correctly flagged as unmatched. This is a feature, not a bug — it distinguishes City-dwellers from others.

Place normalisation handles St/Saint variation and partial matching ("Saint Dunstans" → "Saint Dunstans in the East").

### 4.4 Structured place components (v1.2)

In addition to the flat `place` string and parish vocabulary matching, the segmenter parses place strings into four structured components:

```json
{
  "locality": "Wapping",
  "parish": null,
  "county": "Middlesex",
  "country": null
}
```

Each component is derived from explicit textual cues in the front matter, not inferred from external knowledge:

- **`county`** — from "in the County of [X]" or equivalent explicit phrases. All county attributions in HCA 13/71 ff.1r–50v were found to be explicit and historically correct (confirmed April 2026, including the St Mary Matfelon / Middlesex case).
- **`parish`** — from "of the parish of [X]" or "in the parish of [X]" phrases. Parish is never inferred from locality alone. The pilot graph for HCA 13/71 demonstrated that parish attribution is historically ambiguous: Wapping straddled the parishes of Stepney and St Mary Matfelon (Whitechapel), and deponents did not typically state their parish.
- **`locality`** — the most specific named place, excluding parish and county qualifiers. This is typically what appears immediately after "of" in the front matter: "Wapping", "Deptford", "Ratcliffe", "London".
- **`country`** — extracted only from explicit textual cues (e.g., "in Zeeland", "in the kingdom of Spaine"). Not defaulted to "England" — a significant minority of deponents (10–15%, higher in wartime volumes) resided outside England. Set to `null` when the text does not state a country.

Components that cannot be determined from the text are set to `null`. The flat `place` string is always preserved alongside the structured components.

**Examples from HCA 13/71:**

| Raw place string | locality | parish | county | country |
|-----------------|----------|--------|--------|---------|
| "Wapping in the County of Middlesex" | Wapping | *null* | Middlesex | *null* |
| "the parish of Saint Mary Magdalen Bermondsey in the County of Surrey" | Bermondsey | Saint Mary Magdalen Bermondsey | Surrey | *null* |
| "London" | London | *null* | *null* | *null* |
| "Deale in the County of Kent" | Deal | *null* | Kent | *null* |
| "Middelburg in Zeeland" | Middelburg | *null* | *null* | Zeeland |
| "Flushing in Zeeland" | Flushing | *null* | *null* | Zeeland |

**Design rational