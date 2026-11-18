# Common Crawl check: MarineLives, this repository and the Amsterdam notarial archive

Which pages of the MarineLives wiki, of this repository and of the Stadsarchief Amsterdam's sites are in Common Crawl, the open web archive that most large language models are trained on. The scripts and results were made on 18 November 2026, ahead of the CRASH hackathon in Graz (30 November to 1 December 2026), to judge which test material a model may already have read.

## Findings, 18 November 2026

All 126 Common Crawl crawls were searched, from CC-MAIN-2013-20 to CC-MAIN-2026-43.

**MarineLives wiki: about two-thirds of its pages, transcriptions included.**

| Measure | Content pages |
| --- | --- |
| Captured in any crawl up to the end of 2025 | 8,625 |
| of which HCA 13 folio transcription pages (`…_Annotate`) | 5,495 |
| Captured in the 2025 crawls | 4,023 |
| Captured in a single 2025 crawl | 510 to 911 |
| Captured in the largest single crawl (January 2019) | 4,284 |
| On the wiki today, for comparison | 12,757 |

- A content page is a page whose current text was captured: HTTP 200, HTML, and not an edit form, history, old revision or diff. Special, User, Talk and similar pages are left out.
- The captures hold the text. The January 2025 capture of `HCA_13/71_f.111v_Annotate` carries the whole transcription (try `cc_show_capture.py`).
- Coverage begins in March 2017. Before then the crawls held only the home page.
- HCA 13 volumes with most pages captured up to the end of 2025: 13/71 (842), 13/70 (817), 13/72 (753), 13/68 (658), 13/73 (644), 13/63 (554), 13/69 (503), 13/53 (462), 13/124 (344), 13/65 (194), 13/67 (169), 13/127 (101). The full table is `results/marinelives_by_volume.csv`.
- The Cloudflare block of autumn 2026 has worked. CC-MAIN-2026-39 holds no wiki pages, and in CC-MAIN-2026-43 114 requests were refused (HTTP 403). Captures made before then stay in Common Crawl.

**This repository: none.** No capture of `github.com/Addaci/HCA`, of `raw.githubusercontent.com/Addaci/HCA`, or of `addaci.github.io` in any crawl. The repository dates from August 2024. This is weak evidence that no model has seen it: Common Crawl samples GitHub thinly (a widely used SDK repository appeared once in two recent crawls checked), and model builders also collect GitHub by other routes.

**Stadsarchief Amsterdam: present, but almost empty of content** (CC-MAIN-2025-47 only).

- About 120 index-record pages (`archief.amsterdam/indexen/deeds/…`) were captured. The three opened hold only the site's frame: the record is loaded later by JavaScript.
- 8 inventory pages for archive 5075 were captured.
- 4 pages of the Transkribus viewer (`amsterdam-city-archives.transkribus.eu`) were captured, with no transcription in them.
- `files.transkribus.eu`, which serves PAGE XML, had no robots.txt in November 2025. No file from it was captured.
- No Stadsarchief records were found on Open Archieven under the prefix `saa:`.

The list is `results/amsterdam_CC-MAIN-2025-47.csv`.

## What this means for testing language models

A model trained on Common Crawl may have read the English side of a match (the deposition, from the wiki) but very probably not the Amsterdam side (the archive's index and machine text). This bites only where a language model reads, glosses, proposes or judges. Exact, fuzzy and graph search cannot remember anything.

HCA 13/65, the volume for the HTR pilot, has 194 pages in the crawls. That does not touch the PyLaia model, but a language model used as a reader may have seen those pages' text.

## The scripts

All need Python 3 and nothing else.

- `cc_lookup.py` finds every capture of chosen sites, crawl by crawl. It does not use the index server (index.commoncrawl.org), which refused connections from the machine used. Instead it binary-searches each crawl's `cluster.idx` on data.commoncrawl.org by HTTP range requests, then fetches only the index blocks that can hold the site. A run over all crawls takes about 20 minutes at three crawls at a time. It can be stopped and restarted.
- `cc_summarise.py` turns the captures into the tables in `results/`.
- `cc_show_capture.py` prints the visible text of one archived capture, to check what a crawl really holds.

To repeat the check:

```
python cc_lookup.py --out captures.jsonl --all-crawls
python cc_summarise.py captures.jsonl --outdir results --upto CC-MAIN-2025-51
python cc_show_capture.py captures.jsonl "HCA_13/71_f.111v_Annotate" --crawl CC-MAIN-2025-05
```

To check other sites, give SURT prefixes (the host reversed): for example `--prefix "amsterdam,archief)" --prefix "eu,transkribus,amsterdam-city-archives)"`. A prefix that starts with `#` is counted in index blocks of about 3,000 captures each, not listed. Use it for very large sites.

## Results files

- `marinelives_by_crawl.csv`: per crawl, captures, HTTP status counts and content pages.
- `marinelives_pages.csv`: every content page captured, with first and last crawl and the number of crawls.
- `marinelives_by_volume.csv`: HCA 13 pages captured up to the end of 2025, by volume.
- `github_captures.csv`: captures of this repository (none).
- `amsterdam_CC-MAIN-2025-47.csv`: Stadsarchief and Transkribus captures in that crawl.
- `captures.csv.gz`: all 143,027 captures found (crawl, timestamp, status, type, address).

## Limits

- Common Crawl is one source among several. Model builders also crawl for themselves, buy data and use other archives. Absence from Common Crawl is not proof that a model never saw a page.
- Presence in a crawl is not proof that a page was used either: builders filter and deduplicate.
- Which crawls a given model used depends on its training cutoff, which most builders state only roughly.

*Version 1.0, 18 November 2026. Written by Claude in Claude Code for Colin Greenstreet.*
