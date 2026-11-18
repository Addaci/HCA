"""Summarise MarineLives wiki captures found by cc_lookup.py.

A "content page" is a wiki page whose current text was captured: HTTP 200,
HTML, and an address that shows the page itself (plain or printable view),
not an edit form, history, old revision or diff. Pages in the Special, File,
MediaWiki, Template, Help, User, Talk, Form and Property namespaces are left
out.

Usage:
  python cc_summarise.py captures.jsonl --outdir results [--upto CC-MAIN-2025-51]

Writes to OUTDIR:
  marinelives_by_crawl.csv     per crawl: captures, HTTP status counts, content pages
  marinelives_pages.csv        per content page: first and last crawl, number of crawls
  marinelives_by_volume.csv    HCA 13 pages per volume, up to --upto
  github_captures.csv          every capture under a non-MarineLives prefix
  captures.csv.gz              the compact capture list (crawl, timestamp, status, mime, url)
and prints the headline figures. Needs Python 3 and nothing else.
"""
import argparse, collections, csv, gzip, json, os, re, urllib.parse

SKIP_NS = ("Special:", "File:", "Image:", "MediaWiki:", "Template:", "Help:", "User:", "User_talk:",
           "Talk:", "Category_talk:", "Form:", "Form_talk:", "Property:", "Template_talk:")


def wiki_title(url):
    """The page title if the URL shows a page's current content, else None."""
    u = urllib.parse.urlsplit(url)
    q = urllib.parse.parse_qs(u.query)
    if u.path.startswith("/wiki/"):
        title = urllib.parse.unquote(u.path[6:])
    elif u.path in ("/index.php", "/") and "title" in q:
        title = q["title"][0]
    elif u.path == "/" and not u.query:
        title = "Main_Page"
    else:
        return None
    if any(k in q for k in ("action", "oldid", "diff", "redlink")):
        return None
    return title.replace(" ", "_")


def content_title(r):
    if r.get("status") != "200" or "html" not in r.get("mime", ""):
        return None
    t = wiki_title(r["url"])
    if not t or t.startswith(SKIP_NS):
        return None
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("captures")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--upto", default="CC-MAIN-2025-51", help="last crawl for the cumulative figures")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    recs = [json.loads(l) for l in open(a.captures)]
    ml = [r for r in recs if r["prefix"].startswith("org,marinelives")]
    other = [r for r in recs if not r["prefix"].startswith("org,marinelives") and not r["prefix"].startswith("#")]

    by_crawl = collections.defaultdict(lambda: {"captures": 0, "status": collections.Counter(), "pages": set()})
    pages = {}
    for r in ml:
        c = by_crawl[r["crawl"]]
        c["captures"] += 1
        c["status"][r.get("status", "")] += 1
        t = content_title(r)
        if t:
            c["pages"].add(t)
            p = pages.setdefault(t, set())
            p.add(r["crawl"])

    with open(os.path.join(a.outdir, "marinelives_by_crawl.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["crawl", "captures", "status_200", "status_3xx", "status_403", "status_other", "content_pages"])
        for k in sorted(by_crawl):
            s = by_crawl[k]["status"]
            w.writerow([k, by_crawl[k]["captures"], s["200"],
                        sum(v for x, v in s.items() if x.startswith("3")), s["403"],
                        sum(v for x, v in s.items() if x != "200" and not x.startswith("3") and x != "403"),
                        len(by_crawl[k]["pages"])])

    with open(os.path.join(a.outdir, "marinelives_pages.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "first_crawl", "last_crawl", "crawls"])
        for t in sorted(pages):
            cs = sorted(pages[t])
            w.writerow([t, cs[0], cs[-1], len(cs)])

    upto = {t for t, cs in pages.items() if min(cs) <= a.upto}
    year = a.upto[8:12]
    in_year = {t for t, cs in pages.items() if any(c[8:12] == year for c in cs)}
    vol = collections.Counter()
    for t in upto:
        m = re.match(r"HCA_13/(\d+)", t)
        if m:
            vol[int(m.group(1))] += 1
    with open(os.path.join(a.outdir, "marinelives_by_volume.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["volume", f"pages_captured_up_to_{a.upto}"])
        for v in sorted(vol):
            w.writerow([f"HCA 13/{v}", vol[v]])

    with open(os.path.join(a.outdir, "github_captures.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["crawl", "timestamp", "status", "mime", "url"])
        for r in other:
            w.writerow([r["crawl"], r["ts"], r.get("status"), r.get("mime"), r["url"]])

    with gzip.open(os.path.join(a.outdir, "captures.csv.gz"), "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["crawl", "timestamp", "status", "mime", "url"])
        for r in sorted(recs, key=lambda r: (r["crawl"], r.get("url", ""))):
            if not r["prefix"].startswith("#"):
                w.writerow([r["crawl"], r["ts"], r.get("status"), r.get("mime"), r["url"]])

    annot = [t for t in upto if re.match(r"HCA_13/\d+_f\.\d+[rv]_Annotate$", t)]
    print(f"crawls searched with any MarineLives capture: {len(by_crawl)}")
    print(f"content pages in any crawl: {len(pages)}")
    print(f"content pages in any crawl up to {a.upto}: {len(upto)} (of which HCA 13 folio Annotate pages: {len(annot)})")
    print(f"content pages in the {year} crawls: {len(in_year)}")
    print(f"captures under other prefixes (GitHub): {len(other)}")


if __name__ == "__main__":
    main()
