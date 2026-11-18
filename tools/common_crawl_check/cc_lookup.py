"""Find the captures of chosen web sites in Common Crawl's URL indexes.

Works without the Common Crawl index server (index.commoncrawl.org), which
may refuse connections. Instead it reads the index files on
data.commoncrawl.org with HTTP range requests: a binary search of each
crawl's cluster.idx, then only the compressed index blocks that can hold the
site. A crawl costs a few dozen small requests, not a download of the index.

Sites are given as SURT prefixes: the host reversed, with commas, then ")".
  marinelives.org and www.marinelives.org   org,marinelives)
  other marinelives.org subdomains          org,marinelives,
  github.com/Addaci/HCA (lower case)        com,github)/addaci/hca
A prefix starting with "#" is counted, not listed: the result gives the
number of index blocks (about 3,000 captures each) that hold it.

Usage:
  python cc_lookup.py --out captures.jsonl --all-crawls
  python cc_lookup.py --out captures.jsonl --prefix "org,marinelives)" CC-MAIN-2025-47

Output: one JSON line per capture, with Common Crawl's index fields (url,
status, mime, digest, length, offset, filename, ...) plus crawl, prefix,
surt and ts. The run can be stopped and restarted: crawls already done are
listed in OUT.done and skipped. Needs Python 3 and nothing else.
"""
import argparse, concurrent.futures as cf, gzip, json, os, re, sys, time
import urllib.error, urllib.request

HOST = "https://data.commoncrawl.org/"
BASE = HOST + "cc-index/collections/{c}/indexes/"
DEFAULT_PREFIXES = [
    "org,marinelives)",
    "org,marinelives,",
    "com,github)/addaci/hca",
    "com,githubusercontent,raw)/addaci/hca/",
    "io,github,addaci)",
]
UA = {"User-Agent": "cc-index-lookup/1.0 (research; low request rate)"}


def get(url, start=None, end=None, tries=10):
    """GET, or a byte range of it. Retries with backoff (the host answers 503 when busy)."""
    for i in range(tries):
        req = urllib.request.Request(url, headers=dict(UA))
        if start is not None:
            req.add_header("Range", f"bytes={start}-{end}")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (403, 416):
                raise
        except Exception:
            pass
        time.sleep(min(60, 3 * 2 ** i))
    raise RuntimeError(f"failed {url} {start}-{end}")


def size_of(url):
    for i in range(6):
        req = urllib.request.Request(url, method="HEAD", headers=dict(UA))
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return int(r.headers["Content-Length"])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(min(60, 3 * 2 ** i))
    raise RuntimeError("HEAD failed " + url)


def all_crawls():
    page = get(HOST + "crawl-data/index.html").decode("utf-8", "replace")
    return sorted(set(re.findall(r"CC-MAIN-\d{4}-\d{2}", page)))


def line_at(url, pos, size):
    """The first whole line starting at or after byte pos: (start, text)."""
    data = get(url, pos, min(pos + 8192, size) - 1)
    s = 0
    if pos:
        nl = data.find(b"\n")
        if nl < 0:
            return None, None
        s = nl + 1
    e = data.find(b"\n", s)
    if e < 0:
        return None, None
    return pos + s, data[s:e].decode("utf-8", "replace")


def lookup(crawl, prefix, idx_url, size):
    count_only = prefix.startswith("#")
    prefix = prefix.lstrip("#")
    # 1. Binary search: the last cluster.idx line whose key sorts before the prefix.
    lo, hi, best = 0, size, 0
    while hi - lo > 16384:
        mid = (lo + hi) // 2
        ls, line = line_at(idx_url, mid, size)
        if line is None:
            hi = mid
            continue
        if line.split("\t", 1)[0] < prefix:
            best, lo = ls, ls + 1
        else:
            hi = mid
    # 2. Read forward: the blocks that can hold keys starting with the prefix.
    blocks, pos, prev, done = [], best, None, False
    while not done:
        data = get(idx_url, pos, min(pos + 262144, size) - 1)
        lines = data.split(b"\n")
        at_end = pos + len(data) >= size
        if not at_end:
            lines = lines[:-1]
        consumed = 0
        for raw in lines:
            consumed += len(raw) + 1
            t = raw.decode("utf-8", "replace").split("\t")
            if len(t) < 4:
                continue
            if t[0] < prefix:
                prev = t
                continue
            if prev is not None:
                blocks.append(prev)
                prev = None
            if t[0].startswith(prefix):
                blocks.append(t)
            else:
                done = True
                break
        else:
            if at_end:
                if prev is not None:
                    blocks.append(prev)
                done = True
        pos += consumed
    if count_only:
        return [{"crawl": crawl, "prefix": "#" + prefix, "url": "",
                 "blocks": len({(t[1], t[2]) for t in blocks})}]
    # 3. Fetch those blocks and keep the matching captures.
    out, seen = [], set()
    for t in blocks:
        fn, off, ln = t[1], int(t[2]), int(t[3])
        if (fn, off) in seen:
            continue
        seen.add((fn, off))
        raw = get(BASE.format(c=crawl) + fn, off, off + ln - 1)
        for line in gzip.decompress(raw).decode("utf-8", "replace").splitlines():
            if line.startswith(prefix):
                surt, ts, js = line.split(" ", 2)
                rec = json.loads(js)
                rec.update(crawl=crawl, prefix=prefix, surt=surt, ts=ts)
                out.append(rec)
    return out


def do_crawl(crawl, prefixes):
    try:
        idx_url = BASE.format(c=crawl) + "cluster.idx"
        size = size_of(idx_url)
        if size is None:
            return crawl, None
        res = []
        for p in prefixes:
            res.extend(lookup(crawl, p, idx_url, size))
        return crawl, res
    except Exception as e:  # reported, and the crawl is retried on the next run
        return crawl, e


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("crawls", nargs="*", help="crawl IDs such as CC-MAIN-2025-47")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", action="append", help="SURT prefix; repeat for several (default: MarineLives and Addaci/HCA)")
    ap.add_argument("--all-crawls", action="store_true", help="every crawl listed on data.commoncrawl.org")
    ap.add_argument("--workers", type=int, default=3, help="crawls looked up at once (keep it low)")
    a = ap.parse_args()
    prefixes = a.prefix or DEFAULT_PREFIXES
    crawls = all_crawls() if a.all_crawls else a.crawls
    done_path = a.out + ".done"
    done = set(open(done_path).read().split()) if os.path.exists(done_path) else set()
    todo = [c for c in crawls if c not in done]
    print(f"{len(todo)} crawls to do, {len(crawls) - len(todo)} already done", file=sys.stderr)
    errors = 0
    with open(a.out, "a") as f, open(done_path, "a") as d, cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(do_crawl, c, prefixes) for c in todo]
        for fu in cf.as_completed(futs):
            crawl, res = fu.result()
            if isinstance(res, Exception):
                errors += 1
                print(crawl, "ERROR", res, file=sys.stderr, flush=True)
                continue
            for r in res or []:
                f.write(json.dumps(r) + "\n")
            f.flush()
            d.write(crawl + "\n")
            d.flush()
            counts = {p: (sum(1 for r in res if r["prefix"] == p) if not p.startswith("#")
                          else sum(r["blocks"] for r in res if r["prefix"] == p)) for p in prefixes} if res else "no index"
            print(crawl, counts, file=sys.stderr, flush=True)
    if errors:
        print(f"{errors} crawls failed; run the same command again to retry them", file=sys.stderr)


if __name__ == "__main__":
    main()
