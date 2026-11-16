#!/usr/bin/env python3
"""
htr_eval.py - measure machine-read text (HTR) against held-out ground truth (GT),
and say in advance which names, dates and quantities exact and fuzzy search will miss.

Written for the HCA 13/65 pilot (CRASH, Graz, 30 Nov - 1 Dec 2026), but works on any
pair of Transkribus exports: one folder of GT pages, one folder of HTR pages.

Standard library only. If the optional package `rapidfuzz` is installed it is used
for speed; results are identical either way.

USAGE
  python htr_eval.py --gt GT_DIR --htr HTR_DIR --out OUT_DIR [options]

  GT_DIR / HTR_DIR   folders of PAGE XML (.xml) or plain text (.txt) files, one per page.
                     Pages are paired by file name (stem). In Transkribus, export the
                     GT version and the HTR version of the same document into two folders.
  --label NAME       name of this reading, e.g. "pylaia-440k" or "gemini" (default: htr)
  --lexicon CSV      optional list of known entities: columns  term,class
                     e.g.  Mary Rose,ship   /  Barbados,place  /  John Smith,person
                     (Build it from SOLM locally; it never leaves your machine.)
  --fold-uv-ij       also treat u/v and i/j as the same letter when normalising for search
  --abbrev-chars S   characters that mark an abbreviation in the GT (default set below);
                     words containing them are reported as class "abbreviation"

OUTPUTS (in OUT_DIR, prefixed with the label)
  summary.md               headline figures and tables, readable as it stands
  page_metrics.csv         CER and WER per page, strict and search-normalised
  char_confusions.csv      letter-level substitutions, omissions, insertions with counts
  word_errors.csv          every word the HTR got wrong, with its GT reading and class
  entity_survival.csv      every entity mention: what the HTR made of it, and whether
                           exact / fuzzy search would still find it
  survival_by_class.csv    the same, summed by class (person, ship, place, date, ...)
  errors_in_phrases.txt    wrong readings in the format of the 2024 Hugging Face file
                           (MarineLives/HCA-1358-HTR-Errors-In-Phrases)

DEFINITIONS
  CER  characters wrong per hundred GT characters (edit distance / GT length).
  WER  words wrong per hundred GT words.
  strict  text as transcribed, whitespace collapsed.
  search  lower case, long s -> s, punctuation removed, (optionally u/v, i/j folded):
          roughly what a search engine sees.
  Survival tiers for an entity, comparing its GT form with the HTR reading at the same
  place on the page (from the word alignment):
     exact     identical after search normalisation
     fuzzy-1   one letter out           (found by edit distance 1)
     fuzzy-2   two letters out          (found by edit distance 2)
     fuzzy-30  within 30% of its length (found only by a generous fuzzy search)
     lost      further off than that: needs context, vectors or a graph
  "decoys" counts other places on the same page that a fuzzy-2 search for the GT form
  would also hit: the cost of loosening the search.
  "plausible" marks a wrong word whose HTR form is itself a word found elsewhere in the
  GT: a real-word error, the kind a reader is least likely to notice.
"""

import argparse
import csv
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

try:  # optional speed-up
    from rapidfuzz.distance import Levenshtein as _RFL

    def lev(a, b):
        return _RFL.distance(a, b)
except Exception:  # pragma: no cover
    _RFL = None

    def lev(a, b):
        if a == b:
            return 0
        if len(a) < len(b):
            a, b = b, a
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]


# --------------------------------------------------------------------------- reading

def _local(tag):
    return tag.rsplit('}', 1)[-1]


def read_page_xml(path):
    """Return list of (line_id, text) in document order from a PAGE XML file.
    Uses the TextEquiv that is a direct child of each TextLine (not word-level ones)."""
    tree = ET.parse(path)
    lines = []
    for el in tree.iter():
        if _local(el.tag) != 'TextLine':
            continue
        text = ''
        equivs = [c for c in el if _local(c.tag) == 'TextEquiv']
        if equivs:
            # prefer index="0" or the first one
            equivs.sort(key=lambda e: int(e.get('index', '0') or 0))
            for c in equivs[0]:
                if _local(c.tag) == 'Unicode':
                    text = c.text or ''
                    break
        lines.append((el.get('id', ''), text))
    return lines


def read_txt(path):
    with open(path, encoding='utf-8') as f:
        return [(None, ln.rstrip('\n')) for ln in f]  # no line ids: compared page by page


def read_folder(d):
    pages = {}
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        stem, ext = os.path.splitext(name)
        if ext.lower() == '.xml':
            if name.lower() in ('mets.xml', 'doc.xml', 'metadata.xml'):
                continue
            try:
                pages[stem] = read_page_xml(p)
            except ET.ParseError as e:
                print('  skipped %s: %s' % (name, e), file=sys.stderr)
        elif ext.lower() == '.txt':
            pages[stem] = read_txt(p)
    return pages


# --------------------------------------------------------------------------- normalising

HYPHEN_END = re.compile(r'[¬=\-]\s*$')
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
DEFAULT_ABBREV = 'ꝑꝓꝗꝙꝯꝰ̃̄̅ͣͤͥͦͧͨͩͪͫͬͭͮͯ' \
                 'ʳˢᵗᵉᵃᵈᵐⁿᵒᵘᶜ'


def strict_norm(s):
    s = unicodedata.normalize('NFC', s)
    return re.sub(r'\s+', ' ', s).strip()


def make_search_norm(fold_uv_ij):
    def f(s):
        s = unicodedata.normalize('NFC', s).lower().replace('ſ', 's')
        s = PUNCT.sub('', s)
        if fold_uv_ij:
            s = s.replace('v', 'u').replace('j', 'i')
        return re.sub(r'\s+', ' ', s).strip()
    return f


def page_tokens(lines):
    """Join a page into tokens, rejoining words hyphenated across line ends.
    Returns list of (token, line_index)."""
    toks = []
    carry = None
    for li, (_, text) in enumerate(lines):
        t = strict_norm(text)
        hyph = bool(HYPHEN_END.search(t))
        if hyph:
            t = HYPHEN_END.sub('', t)
        words = t.split()
        if carry is not None and words:
            words[0] = carry[0] + words[0]
            li0 = carry[1]
            carry = None
            toks.append((words[0], li0))
            words = words[1:]
        elif carry is not None:
            toks.append(carry)
            carry = None
        for k, w in enumerate(words):
            if hyph and k == len(words) - 1:
                carry = (w, li)
            else:
                toks.append((w, li))
    if carry is not None:
        toks.append(carry)
    return toks


# --------------------------------------------------------------------------- alignment

def align(a, b, cost=lambda x, y: 0 if x == y else 1):
    """Levenshtein alignment of two sequences. Returns list of (op, i, j):
    op in 'eq','sub','del' (in a, missing from b),'ins' (in b, not in a)."""
    n, m = len(a), len(b)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        D[i][0] = i
    for j in range(1, m + 1):
        D[0][j] = j
    for i in range(1, n + 1):
        ai = a[i - 1]
        Di, Dp = D[i], D[i - 1]
        for j in range(1, m + 1):
            Di[j] = min(Dp[j] + 1, Di[j - 1] + 1, Dp[j - 1] + cost(ai, b[j - 1]))
    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and D[i][j] == D[i - 1][j - 1] + cost(a[i - 1], b[j - 1]):
            ops.append(('eq' if a[i - 1] == b[j - 1] else 'sub', i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and D[i][j] == D[i - 1][j] + 1:
            ops.append(('del', i - 1, None))
            i -= 1
        else:
            ops.append(('ins', None, j - 1))
            j -= 1
    ops.reverse()
    return ops


def word_cost(x, y):
    """Substitution cost between words: cheaper when similar, so that similar words
    pair up rather than being counted as one deletion plus one insertion."""
    if x == y:
        return 0
    d = lev(x.lower(), y.lower())
    return 0.5 + 0.5 * min(1.0, d / max(len(x), len(y), 1))


def char_edits(gt, htr):
    """Character-level edits turning the HTR reading into the GT reading.
    Yields (kind, htr_chars, gt_chars) with kind in sub/omit/insert."""
    ops = align(list(htr), list(gt))
    out = []
    # merge runs of adjacent non-eq ops into one edit, e.g. 'ff' -> 'Ro'
    run_h, run_g = '', ''
    for op, i, j in ops + [('eq', None, None)]:
        if op == 'eq':
            if run_h or run_g:
                kind = 'sub' if run_h and run_g else ('omit' if run_g else 'insert')
                out.append((kind, run_h, run_g))
                run_h, run_g = '', ''
            continue
        if i is not None:
            run_h += htr[i]
        if j is not None:
            run_g += gt[j]
    return out


# --------------------------------------------------------------------------- entities

MONTHS = ('january|february|ffebruary|march|april|may|june|july|august|september|october|'
          'november|december|jan|feb|ffeb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec|'
          '7ber|8ber|9ber|10ber|xber|januarii|februarii|martii|aprilis|maii|iunii|junii|julii|'
          'augusti|septembris|octobris|novembris|decembris|januarij|februarij|martij|junij|julij')
NUMBER_WORDS = ('one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|'
                'fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|'
                'fortie|fifty|fiftie|sixty|sixtie|seventy|eighty|ninety|hundred|hundreth|'
                'thousand|score|halfe|half|first|second|third|fourth|fifth|sixth|seventh|'
                'eighth|ninth|tenth')
UNITS = ('tons|tonns|tunns|tun|tunn|pounds|pound|li|lb|lbs|barrells|barrels|barrell|hogsheads|'
         'hogshead|hhds|chests|chest|pieces|peeces|peeces|pipes|butts|bales|baggs|bags|'
         'quintals|kintalls|ells|yards|guilders|gilders|gulden|rixdollars|ryxdollars|dollars|'
         'pieces of eight|reals|ryalls|shillings|shilling|pence|negroes|slaves|servants|men|'
         'guns|peeces of ordnance|lasts|chaldron|quarters|bushells|gallons|jarres|jars|rolls|'
         'kegs|cask|caskes|casks|sugar|chests of sugar')
TITLES = r'(mr|mris|mrs|capt|captaine|captain|sr|sir|master|mr\.|monsr|seignior|signor|don|heer)'
SHIP_CUE = re.compile(r'\b(?:ship|shipp|shippe|vessell|vessel|pinke|pink|ketch|catch|frigot|frigat\w*|'
                      r'flyboat|fliboat|hoy|barke|bark|barque|boat|galliott|galliot|fluyt|fluit)\s+'
                      r'(?:called|named|caled|cald)\s+(?:the\s+)?', re.I)


AMBIGUOUS_MONTHS = {'may', 'march', 'mar', 'jan', 'feb', 'ffeb', 'apr', 'jun', 'jul', 'aug', 'sep',
                    'sept', 'oct', 'nov', 'dec'}


def classify_numbers(norm_tokens):
    """Mark date and quantity spans in a list of search-normalised tokens.
    Returns list of (start, end, class)."""
    spans = []
    n = len(norm_tokens)
    is_num = [bool(re.fullmatch(r'\d+(?:st|nd|rd|th|o)?|' + NUMBER_WORDS, t)) for t in norm_tokens]
    used = [False] * n
    # pass 1: dates built round a month name
    for i, t in enumerate(norm_tokens):
        if not re.fullmatch(MONTHS, t):
            continue
        s = i
        k = i - 1
        while k >= 0 and i - k <= 4 and (is_num[k] or norm_tokens[k] in ('of', 'day', 'the')):
            if is_num[k]:
                s = k
            k -= 1
        e = i + 1
        if e < n and (re.fullmatch(r'1[5-7]\d\d|\d{1,4}', norm_tokens[e]) or is_num[e]):
            e += 1
            if e < n and re.fullmatch(r'1[5-7]\d\d', norm_tokens[e]):  # "March 3 1656"
                e += 1
        has_number = s < i or e > i + 1
        if t in AMBIGUOUS_MONTHS and not has_number:
            continue  # "may" the verb, "march" the verb
        if any(used[s:e]):
            continue
        for k in range(s, e):
            used[k] = True
        spans.append((s, e, 'date'))
    # pass 2: years after anno / in / of, quantities, other numbers
    i = 0
    while i < n:
        if used[i]:
            i += 1
            continue
        if re.fullmatch(r'1[5-7]\d\d', norm_tokens[i]) and i > 0 and norm_tokens[i - 1] in (
                'anno', 'year', 'yeare', 'in', 'of', 'domini'):
            spans.append((i, i + 1, 'date'))
            i += 1
            continue
        if is_num[i]:
            e = i + 1
            while e < n and not used[e] and (is_num[e] or norm_tokens[e] in ('and', 'or')) and e - i < 6:
                e += 1
            while e > i + 1 and norm_tokens[e - 1] in ('and', 'or'):
                e -= 1
            if e < n and re.fullmatch(UNITS, norm_tokens[e]):
                spans.append((i, e + 1, 'quantity'))
                i = e + 1
                continue
            if e + 1 < n and norm_tokens[e] == 'of' and re.fullmatch(UNITS, norm_tokens[e + 1]):
                spans.append((i, e + 2, 'quantity'))
                i = e + 2
                continue
            if re.search(r'\d', ''.join(norm_tokens[i:e])):
                spans.append((i, e, 'number'))
            i = e
            continue
        i += 1
    return spans


def load_lexicon(path, snorm):
    lex = defaultdict(list)  # first token -> list of (token tuple, class, term)
    if not path:
        return lex
    with open(path, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            term = (row.get('term') or '').strip()
            cls = (row.get('class') or '').strip() or 'lexicon'
            toks = tuple(snorm(term).split())
            if toks:
                lex[toks[0]].append((toks, cls, term))
    for k in lex:
        lex[k].sort(key=lambda x: -len(x[0]))
    return lex


def find_entities(gt_tokens_strict, gt_tokens_norm, lex, abbrev_chars):
    """Return list of (start, end, class, source). Lexicon beats cue rules;
    numbers/dates added where no lexicon entity overlaps; unverified cue classes end in '?'."""
    n = len(gt_tokens_norm)
    taken = [False] * n
    ents = []

    def add(s, e, cls, src):
        if s >= e or any(taken[s:e]):
            return False
        for k in range(s, e):
            taken[k] = True
        ents.append((s, e, cls, src))
        return True

    # 1. lexicon (longest match first)
    i = 0
    while i < n:
        hit = False
        for toks, cls, _ in lex.get(gt_tokens_norm[i], []):
            if tuple(gt_tokens_norm[i:i + len(toks)]) == toks:
                add(i, i + len(toks), cls, 'lexicon')
                i += len(toks)
                hit = True
                break
        if not hit:
            i += 1
    # 2. dates and quantities
    for s, e, cls in classify_numbers(gt_tokens_norm):
        add(s, e, cls, 'rule')
    # 3. cue rules on the strict text
    text = ' '.join(gt_tokens_strict)
    starts = []
    pos = 0
    for t in gt_tokens_strict:
        starts.append(pos)
        pos += len(t) + 1

    def tok_at(charpos):
        for k in range(len(starts) - 1, -1, -1):
            if starts[k] <= charpos:
                return k
        return 0

    def cap_run(k, maxlen=4):
        e = k
        while e < n and e - k < maxlen and gt_tokens_strict[e][:1].isupper() or \
                (e < n and e > k and e - k < maxlen and gt_tokens_norm[e] in ('de', 'van', 'la', 'del', 'da', 'le')
                 and e + 1 < n and gt_tokens_strict[e + 1][:1].isupper()):
            e += 1
        return e

    for m in SHIP_CUE.finditer(text):
        k = tok_at(m.end())
        e = cap_run(k, 4)
        if e == k and k < n:  # ship names are not always capitalised
            e = min(k + 2, n)
        add(k, e, 'ship?', 'cue')
    for k in range(n - 1):
        if re.fullmatch(TITLES, gt_tokens_norm[k]) and gt_tokens_strict[k + 1][:1].isupper():
            add(k + 1, cap_run(k + 1, 3), 'person?', 'cue')
    for k in range(n - 1):
        if gt_tokens_norm[k] in ('at', 'from', 'in', 'to', 'for', 'of') and gt_tokens_strict[k + 1][:1].isupper() \
                and not taken[k + 1]:
            add(k + 1, cap_run(k + 1, 3), 'place?', 'cue')
    # 4. remaining capitalised words not at the start of the page
    for k in range(1, n):
        if not taken[k] and gt_tokens_strict[k][:1].isupper() and len(gt_tokens_norm[k]) > 2:
            add(k, cap_run(k, 3), 'capitalised', 'rule')
    # 5. abbreviations
    for k in range(n):
        if not taken[k] and any(c in abbrev_chars for c in gt_tokens_strict[k]):
            add(k, k + 1, 'abbreviation', 'rule')
    ents.sort()
    return ents


# --------------------------------------------------------------------------- main

def survival_tier(d, length):
    if d == 0:
        return 'exact'
    if d == 1:
        return 'fuzzy-1'
    if d == 2:
        return 'fuzzy-2'
    if d <= max(2, round(0.3 * length)):
        return 'fuzzy-30'
    return 'lost'


TIERS = ['exact', 'fuzzy-1', 'fuzzy-2', 'fuzzy-30', 'lost']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--gt', required=True)
    ap.add_argument('--htr', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--label', default='htr')
    ap.add_argument('--lexicon')
    ap.add_argument('--fold-uv-ij', action='store_true')
    ap.add_argument('--abbrev-chars', default=DEFAULT_ABBREV)
    a = ap.parse_args()

    snorm = make_search_norm(a.fold_uv_ij)
    gt_pages, htr_pages = read_folder(a.gt), read_folder(a.htr)
    common = sorted(set(gt_pages) & set(htr_pages))
    if not common:
        sys.exit('No pages with the same file name in both folders.')
    missing = sorted(set(gt_pages) ^ set(htr_pages))
    lex = load_lexicon(a.lexicon, snorm)
    os.makedirs(a.out, exist_ok=True)
    P = lambda name: os.path.join(a.out, '%s_%s' % (a.label, name))

    # GT vocabulary across the whole set, for the 'plausible' (real-word error) test
    gt_vocab = Counter()
    for pg in common:
        for t, _ in page_tokens(gt_pages[pg]):
            gt_vocab[snorm(t)] += 1

    page_rows, word_rows, ent_rows = [], [], []
    char_conf = Counter()
    tot = Counter()
    for pg in common:
        g_lines, h_lines = gt_pages[pg], htr_pages[pg]
        # line pairing by id (Transkribus keeps line ids when HTR is run on the GT layout)
        g_ids = [i for i, _ in g_lines]
        h_map = {i: t for i, t in h_lines}
        id_overlap = sum(1 for i in g_ids if i and i in h_map) / max(1, len(g_ids))
        # character error rate
        cer = {}
        for mode, fn in (('strict', strict_norm), ('search', snorm)):
            if id_overlap >= 0.8:
                errs = sum(lev(fn(t), fn(h_map.get(i, ''))) for i, t in g_lines)
                n = sum(len(fn(t)) for _, t in g_lines)
            else:
                gtxt = fn(' '.join(t for _, t in g_lines))
                htxt = fn(' '.join(t for _, t in h_lines))
                errs, n = lev(gtxt, htxt), len(gtxt)
            cer[mode] = (errs, n)
            tot['cer_err_' + mode] += errs
            tot['cer_n_' + mode] += n

        # word alignment over the whole page (handles merged / split lines)
        g_toks = page_tokens(g_lines)
        h_toks = page_tokens(h_lines)
        g_s = [t for t, _ in g_toks]
        h_s = [t for t, _ in h_toks]
        g_n = [snorm(t) for t in g_s]
        h_n = [snorm(t) for t in h_s]
        ops = align(g_n, h_n, word_cost)
        g2h = {}  # gt index -> list of htr indices
        wer_err = {'strict': 0, 'search': 0}
        last_h = -1
        for k, (op, i, j) in enumerate(ops):
            if i is not None and j is not None:
                g2h[i] = [j]
                last_h = j
            elif i is not None:
                g2h[i] = []
            if op == 'eq':
                if g_s[i] != h_s[j]:
                    wer_err['strict'] += 1
                continue
            wer_err['strict'] += 1
            wer_err['search'] += 1
            if op == 'sub':
                kind = 'substitution'
                # word-boundary error: GT w1 w2 read as one word, or one GT word read as two
                nxt = ops[k + 1] if k + 1 < len(ops) else None
                prv = ops[k - 1] if k > 0 else None
                if nxt and nxt[0] == 'del' and h_n[j] == g_n[i] + g_n[nxt[1]]:
                    kind = 'words run together'
                elif nxt and nxt[0] == 'ins' and g_n[i] == h_n[j] + h_n[nxt[2]]:
                    kind = 'word split'
                gt_w, htr_w = g_s[i], h_s[j]
                for ck, hc, gc in char_edits(snorm(gt_w), snorm(htr_w)):
                    char_conf[(ck, hc, gc)] += 1
                plausible = snorm(htr_w) in gt_vocab
            elif op == 'del':
                kind, gt_w, htr_w, plausible = 'word omitted', g_s[i], '', False
            else:
                kind, gt_w, htr_w, plausible = 'word superfluous', '', h_s[j], False
            ctx_lo = max(0, (i if i is not None else (ops[k - 1][1] or 0)) - 2)
            ctx = ' '.join(g_s[ctx_lo:ctx_lo + 5])
            line_idx = g_toks[i][1] if i is not None else h_toks[j][1]
            word_rows.append({'page': pg, 'line': line_idx + 1, 'gt': gt_w, 'htr': htr_w,
                              'distance': lev(snorm(gt_w), snorm(htr_w)), 'kind': kind,
                              'plausible': 'yes' if plausible else '', 'gt_context': ctx})
            tot['kind_' + kind] += 1
            if plausible:
                tot['plausible'] += 1
        tot['words'] += len(g_s)
        tot['wer_err_strict'] += wer_err['strict']
        tot['wer_err_search'] += wer_err['search']

        # entities and their survival
        ents = find_entities(g_s, g_n, lex, a.abbrev_chars)
        for s, e, cls, src in ents:
            gt_form = ' '.join(g_n[s:e])
            hs = sorted(j for i in range(s, e) for j in g2h.get(i, []))
            if hs:
                h_form = ' '.join(h_n[hs[0]:hs[-1] + 1])
            else:
                h_form = ''
            d = lev(gt_form, h_form)
            tier = survival_tier(d, len(gt_form))
            # decoys: other windows on the page within distance 2 of the GT form
            L = e - s
            decoys = 0
            for w in range(max(1, L - 1), L + 2):
                for j in range(0, len(h_n) - w + 1):
                    if hs and j == hs[0] and w == len(hs):
                        continue
                    cand = ' '.join(h_n[j:j + w])
                    if abs(len(cand) - len(gt_form)) <= 2 and lev(gt_form, cand) <= 2:
                        decoys += 1
            ent_rows.append({'page': pg, 'line': g_toks[s][1] + 1, 'class': cls, 'source': src,
                             'gt': ' '.join(g_s[s:e]), 'htr': ' '.join(h_s[hs[0]:hs[-1] + 1]) if hs else '',
                             'distance': d, 'tier': tier, 'decoys_within_2': decoys})

        page_rows.append({'page': pg, 'lines': len(g_lines),
                          'line_ids_matched': '%.0f%%' % (100 * id_overlap),
                          'gt_chars': cer['strict'][1], 'gt_words': len(g_s),
                          'cer_strict': '%.2f' % (100 * cer['strict'][0] / max(1, cer['strict'][1])),
                          'cer_search': '%.2f' % (100 * cer['search'][0] / max(1, cer['search'][1])),
                          'wer_strict': '%.2f' % (100 * wer_err['strict'] / max(1, len(g_s))),
                          'wer_search': '%.2f' % (100 * wer_err['search'] / max(1, len(g_s)))})

    # ------------------------------------------------------------------ write
    def write_csv(name, rows, fields=None):
        with open(P(name), 'w', encoding='utf-8', newline='') as f:
            if not rows:
                f.write('')
                return
            w = csv.DictWriter(f, fieldnames=fields or list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_csv('page_metrics.csv', page_rows)
    write_csv('word_errors.csv', word_rows,
              ['page', 'line', 'gt', 'htr', 'distance', 'kind', 'plausible', 'gt_context'])
    write_csv('entity_survival.csv', ent_rows,
              ['page', 'line', 'class', 'source', 'gt', 'htr', 'distance', 'tier', 'decoys_within_2'])
    conf_rows = [{'kind': k, 'htr_read': h, 'should_be': g, 'count': c}
                 for (k, h, g), c in char_conf.most_common()]
    write_csv('char_confusions.csv', conf_rows, ['kind', 'htr_read', 'should_be', 'count'])

    by_cls = defaultdict(Counter)
    dec = defaultdict(list)
    for r in ent_rows:
        by_cls[r['class']][r['tier']] += 1
        dec[r['class']].append(r['decoys_within_2'])
    surv_rows = []
    for cls in sorted(by_cls, key=lambda c: -sum(by_cls[c].values())):
        c = by_cls[cls]
        n = sum(c.values())
        row = {'class': cls, 'mentions': n}
        cum = 0
        for t in TIERS:
            row[t] = c[t]
        for t in TIERS[:-1]:
            cum += c[t]
            row['found_by_' + t] = '%.0f%%' % (100 * cum / n)
        row['mean_decoys_fuzzy2'] = '%.1f' % (sum(dec[cls]) / n)
        surv_rows.append(row)
    write_csv('survival_by_class.csv', surv_rows)

    with open(P('errors_in_phrases.txt'), 'w', encoding='utf-8') as f:
        f.write('# ERRORS IN RAW HTR TEXT (%s), AUTOMATICALLY EXTRACTED AGAINST HELD-OUT GROUND TRUTH\n' % a.label)
        f.write('# format as MarineLives/HCA-1358-HTR-Errors-In-Phrases: htr reading -> correct reading, #kind\n')
        for r in word_rows:
            if r['kind'] in ('substitution', 'words run together', 'word split') and r['htr']:
                f.write("r'\\b%s\\b': '%s', #%s, #distance %d%s, #%s\n" % (
                    r['htr'].replace("'", "\\'"), r['gt'].replace("'", "\\'"), r['kind'], r['distance'],
                    ', #plausible' if r['plausible'] else '', r['page']))

    # summary
    def pct(x, n):
        return '%.2f' % (100 * x / max(1, n))
    nsub = tot['kind_substitution'] + tot['kind_words run together'] + tot['kind_word split']
    md = []
    md.append('# HTR evaluation: %s\n' % a.label)
    md.append('GT folder: `%s`  \nHTR folder: `%s`  \nPages compared: %d' % (a.gt, a.htr, len(common)))
    if missing:
        md.append('  \nPages present in only one folder (ignored): %s' % ', '.join(missing[:20]) +
                  (' ...' if len(missing) > 20 else ''))
    md.append('  \nLexicon: %s  \nu/v and i/j folded for search: %s\n' % (a.lexicon or 'none (cue rules only)',
                                                                           'yes' if a.fold_uv_ij else 'no'))
    md.append('## Headline\n')
    md.append('| Measure | Strict | Search-normalised |\n|---|---|---|')
    md.append('| Characters wrong per 100 (CER) | %s | %s |' % (pct(tot['cer_err_strict'], tot['cer_n_strict']),
                                                              pct(tot['cer_err_search'], tot['cer_n_search'])))
    md.append('| Words wrong per 100 (WER) | %s | %s |' % (pct(tot['wer_err_strict'], tot['words']),
                                                         pct(tot['wer_err_search'], tot['words'])))
    md.append('\nGT words: %d. Wrong words (search-normalised): %d, of which substitutions %d, '
              'words run together %d, words split %d, omitted %d, superfluous %d.' % (
                  tot['words'], tot['wer_err_search'], tot['kind_substitution'], tot['kind_words run together'],
                  tot['kind_word split'], tot['kind_word omitted'], tot['kind_word superfluous']))
    md.append('Plausible (real-word) errors: %d of %d substituted words (%s%%): the HTR reading is itself '
              'a word found elsewhere in the GT.\n' % (tot['plausible'], nsub, pct(tot['plausible'], nsub)))
    md.append('## Would search still find it?\n')
    md.append('Share of entity mentions found by each kind of search (cumulative). '
              'Classes ending in "?" come from cue rules, not a checked list.\n')
    md.append('| Class | Mentions | Exact | Fuzzy 1 | Fuzzy 2 | Fuzzy 30% | Lost | Decoys at fuzzy 2 |')
    md.append('|---|---|---|---|---|---|---|---|')
    for r in surv_rows:
        md.append('| %s | %d | %s | %s | %s | %s | %d | %s |' % (
            r['class'], r['mentions'], r['found_by_exact'], r['found_by_fuzzy-1'], r['found_by_fuzzy-2'],
            r['found_by_fuzzy-30'], r['lost'], r['mean_decoys_fuzzy2']))
    md.append('\nFor dates, numbers and quantities a fuzzy hit is not a success: "13 of October 1656" read as '
              '"18 of October 1636" is found at fuzzy 2 but gives the wrong date. For those classes only the '
              'Exact column counts as a correct value, and the decoy count shows how many other places on the page '
              'a fuzzy search would also hit.\n')
    md.append('\n"Lost" mentions are listed in `%s_entity_survival.csv` (tier = lost): the set that '
              'context, vectors or a graph would have to earn.\n' % a.label)
    md.append('## Commonest letter confusions\n')
    md.append('| Kind | HTR read | Should be | Count |\n|---|---|---|---|')
    for r in conf_rows[:25]:
        md.append('| %s | `%s` | `%s` | %d |' % (r['kind'], r['htr_read'] or '·', r['should_be'] or '·', r['count']))
    md.append('\n## Pages\n')
    md.append('| Page | Lines | Line ids matched | CER strict | CER search | WER search |\n|---|---|---|---|---|---|')
    for r in page_rows:
        md.append('| %s | %d | %s | %s | %s | %s |' % (r['page'], r['lines'], r['line_ids_matched'],
                                                     r['cer_strict'], r['cer_search'], r['wer_search']))
    md.append('\n## Caveats\n')
    md.append('- Check that no page here was in the training or validation set of the model (Transkribus model record).')
    md.append('- If the GT was corrected from earlier machine text rather than typed fresh, some machine errors may '
              'survive in it, and the rates above will be too low.')
    md.append('- Differences in transcription rules (abbreviations, long s, ff, line-end hyphens) count as errors '
              'in the strict figures; the search-normalised figures remove some of them.')
    md.append('- Rare classes (ships, dates) need many pages before their percentages settle; '
              'read small counts as indications.')
    with open(P('summary.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    print('Compared %d pages. CER (search) %s, WER (search) %s. Results in %s' % (
        len(common), pct(tot['cer_err_search'], tot['cer_n_search']),
        pct(tot['wer_err_search'], tot['words']), os.path.abspath(a.out)))


if __name__ == '__main__':
    main()
