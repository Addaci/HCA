# HCA

English High Court of Admiralty records from The National Archives, Kew, transcribed by the MarineLives project: the examination books HCA 13/20 to HCA 13/79 (depositions, 1570 to 1685), and from 31 October 2026 a first machine transcription of the personal-answer book HCA 13/125 (1652 to 1654).

MarineLives is a volunteer collaboration launched in 2012. Its transcriptions are made available to the public on an open basis. The wiki holds about 12,000 pages: [www.marinelives.org/wiki/MarineLives](http://www.marinelives.org/wiki/MarineLives). We are on BlueSky at [marinelivesorg.bsky.social](https://bsky.app/profile/marinelivesorg.bsky.social).

## What is here

**Edited deposition volumes, HCA 13/31 to HCA 13/79.** Twenty-seven files named `HCA_13_nn_Full_Volume_Processed_Text_EDITED_Ver.x.y_DDMMYYYY.txt`, one per volume, produced in 2024 from machine transcription with human editing. Each page is headed `HCA 13/nn f.nnr Annotate` or `f.nnv`, matching the wiki page names, so a hit here can be read against the page image on the wiki. Volumes 31, 35, 39, 40, 42, 44, 48 to 53, 55 to 59, 61, 63, 64, 68, 70 to 73, 76 and 79 are present; the rest of the series is to follow.

**Raw machine transcription, HCA 13/125.** `HCA_13_125_Full_Volume_Machine_Transcription_RAW_Ver.1.3_31102026.txt` is different in kind: an unedited reading of all 416 photographed pages by Claude Opus 5.5 on 31 October 2026, with no human check of any page. It is published to be searched, not quoted. Its front matter gives the provenance of the photographs, the method, the system prompt and the script, and a short note on what a personal answer is and how it differs from a deposition. The volume is unfoliated, so pages are headed by image number, `HCA 13/125 IMG_115_05_nnnn`. The photographs are not on the wiki and are available on request.

**Other files.** `ML_FINDING_AID_Materials_Handling_16092021_Ver71.7.pdf`, a finding aid to the HCA material; `Index_Ver.2.0_04112024.html` and `index.html`, an index to the volumes; `TNA_AI_Week_New_Skills_for_Historians_FINAL_WITH_EMAIL_19072024.pdf`, a talk given at The National Archives in July 2024; and three `Working_with_Aurelius-HTR_...txt` files, chapters on working with the Aurelius HTR model, in English and in Portuguese.

**Tools.** `tools/htr_eval/` holds `htr_eval.py` and its README, added on 16 November 2026. The script measures machine transcription against ground truth that the model was not trained on. It reports characters and words wrong per hundred, which letters are misread as which, and every wrong word. For each person, ship, place, date and quantity it says whether exact or fuzzy search would still find it. It needs Python 3 and nothing else. It was written for a pilot on HCA 13/65 ahead of the CRASH hackathon in Graz (30 November to 1 December 2026). Its output follows the format of the Hugging Face dataset [MarineLives/HCA-1358-HTR-Errors-In-Phrases](https://huggingface.co/datasets/MarineLives/HCA-1358-HTR-Errors-In-Phrases) (2024), so the two can be compared.

## Reading the text

Spelling, capitalisation and abbreviation are the scribes' own, not errors to be corrected: in HCA 13/71, for example, about seven words in ten are in a spelling that is not the modern one. In the edited volumes some common abbreviations have been expanded ("videlicet", "the"); in the raw HCA 13/125 file they stand as written ("vizt", "ye"), with `[?]` after a doubtful word and `[illegible]` for an unread stretch.

## Licence

Except where a file says otherwise, the transcriptions, index, documentation and tools in this repository are released under the [Creative Commons Attribution 4.0 International licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). The full text is in `LICENSE`. You may copy, adapt and reuse them for any purpose, provided you credit MarineLives and cite as below.

The licence covers the work of MarineLives and its volunteers: the transcriptions, their editing and the files here. The original records are held by The National Archives, Kew, under the reference HCA.

## Citing

**A page.** Cite the volume, the folio and side (or, for HCA 13/125, the image number), MarineLives as transcriber, the file name with its version, and this repository, with the date you used it. For example:

> HCA 13/71 f.45r, transcribed by MarineLives, `HCA_13_71_Full_Volume_Processed_Text_EDITED_Ver.1.3_16062024.txt`, MarineLives HCA repository, https://github.com/Addaci/HCA (accessed 20 November 2026). CC BY 4.0.

For HCA 13/125, add that the reading is a machine transcription of 31 October 2026, unverified:

> HCA 13/125 IMG_115_05_8500, MarineLives raw machine transcription of 31 October 2026, unverified, `HCA_13_125_Full_Volume_Machine_Transcription_RAW_Ver.1.3_31102026.txt`, MarineLives HCA repository, https://github.com/Addaci/HCA (accessed 20 November 2026). CC BY 4.0.

**MarineLives as a whole.** Cite the project and its wiki:

> MarineLives (2012 to date), a volunteer collaboration transcribing the records of the English High Court of Admiralty, https://www.marinelives.org/wiki/MarineLives (accessed 20 November 2026).

**This repository.** GitHub's "Cite this repository" button, at the top right of the repository page, gives the same reference in APA and BibTeX form, from the file `CITATION.cff`.

Replace the access date with your own. Credit to MarineLives satisfies the attribution condition of the CC BY 4.0 licence.

## Contact

Questions, corrections and requests for page images: on application to Colin Greenstreet through his LinkedIn account, https://www.linkedin.com/in/colin-greenstreet-7434b9/.

*README version 2.0, 31 October 2026. Drafted by Claude Fable 5.1 (medium), in Claude Code, for Colin Greenstreet; the previous README (2024) said that a machine transcription of all volumes 1570 to 1685 would be complete by the end of 2025, and gave a word count; Colin to update those two statements.*

*README version 2.1, 16 November 2026: adds the Tools paragraph. Drafted by Claude in Claude Code for Colin Greenstreet.*

*README version 2.2, 20 November 2026: adds the Licence section and the `LICENSE` file (CC BY 4.0), how to cite MarineLives, and `CITATION.cff`, at Colin Greenstreet's instruction. Drafted by Claude in Claude Code.*
