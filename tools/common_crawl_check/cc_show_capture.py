"""Print the visible text of one archived capture, to see what a crawl really holds.

Usage:
  python cc_show_capture.py captures.jsonl "HCA_13/71_f.111v_Annotate" [--crawl CC-MAIN-2025-05] [--chars 3000]

The second argument is any part of the captured URL. The first matching
capture (HTTP 200) is fetched from data.commoncrawl.org by byte range, and
its text is printed with scripts, styles and tags removed. A page whose
content is loaded later by JavaScript shows only its frame.
Needs Python 3 and nothing else.
"""
import argparse, gzip, html, json, re, time, urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("captures")
    ap.add_argument("url_part")
    ap.add_argument("--crawl")
    ap.add_argument("--chars", type=int, default=3000)
    a = ap.parse_args()
    for line in open(a.captures):
        r = json.loads(line)
        if a.url_part in r.get("url", "") and r.get("status") == "200" and (not a.crawl or r["crawl"] == a.crawl):
            break
    else:
        raise SystemExit("no matching capture")
    off, ln = int(r["offset"]), int(r["length"])
    for i in range(8):
        try:
            req = urllib.request.Request("https://data.commoncrawl.org/" + r["filename"],
                                         headers={"Range": f"bytes={off}-{off + ln - 1}",
                                                  "User-Agent": "cc-index-lookup/1.0 (research)"})
            raw = urllib.request.urlopen(req, timeout=60).read()
            break
        except Exception:
            time.sleep(5 * (i + 1))
    else:
        raise SystemExit("fetch failed")
    body = gzip.decompress(raw).decode("utf-8", "replace").split("\r\n\r\n", 2)[-1]
    text = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", body)
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)))
    print(r["crawl"], r["ts"], r["url"], f"({len(body)} bytes of HTML, {len(text)} characters of text)")
    print(text[: a.chars])


if __name__ == "__main__":
    main()
