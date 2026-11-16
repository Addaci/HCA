# HTR evaluation: HCA 13/65 pilot

`htr_eval.py` compares machine-read text with held-out ground truth (GT). It reports:

- error rates
- a table of which letters are misread as which
- every wrong word
- for each person, ship, place, date and quantity, whether exact or fuzzy search would still find it.

It needs Python 3 and nothing else.

## Pilot before Graz: 20 to 30 pages

1. **Check the model record.** In Transkribus, open the model's details and look at its training set and validation set. No 13/65 page may be in either. Note the model's name and ID; the analysis should cite them.
2. **Choose the pages.** Take 20–30 GT pages from 13/65, spread across several clerks' hands. Include some Barbados or Guinea depositions if you can.
3. **Export the GT first.** Export those pages as PAGE XML into a folder called `gt`.
4. **Run the model on a copy.** Duplicate the document and run the model on the duplicate only. That keeps your GT untouched. Choose the option that keeps the existing layout (no new layout analysis), so the line IDs stay the same and lines can be compared one to one.
5. **Export the machine text.** Export the duplicate as PAGE XML into a folder called `htr`. The file names will match the GT export because the images are the same.
6. **Run the script:**

```
python htr_eval.py --gt gt --htr htr --out results --label pylaia-440k
```

Optional extras:

- `--lexicon entities.csv` (columns `term,class`) lists known ships, people and places. You could take it from SOLM for the depositions involved. It stays on your machine. Without it, the script finds names from cues such as "ship called", "Mr", "Captain" or "from X", and marks those classes with `?`.
- `--fold-uv-ij` makes u/v and i/j count as the same letter for search.
- For a stochastic comparison, put Claude or Gemini text for the same pages in another folder, one `.txt` file per page with the same names. Run the script again with `--label gemini` and the same `--out` folder.

## What to look at first

- `*_summary.md`: headline error rates, the search-survival table by class, the commonest letter confusions and figures per page.
- `*_entity_survival.csv`, rows where the tier is `lost`: mentions that neither exact nor fuzzy search would find.
- `*_word_errors.csv`, rows marked `plausible`: the machine wrote a real word, just the wrong one.
- `*_errors_in_phrases.txt`: the same layout as the 2024 Hugging Face file, so the two sets can be compared or merged.

## Caveats

- For dates, numbers and quantities, a fuzzy hit means a wrong value: 1656 read as 1636 is "found", but it is the wrong year.
- If the GT was corrected from earlier machine text, some machine errors may have survived in it. The error rates would then come out too low.
- Different transcription conventions (abbreviations, long s, ff, line-end hyphens) inflate the strict figures. The search-normalised figures remove some of that.
- With 20–30 pages, read the percentages for ships and dates as indications only.
