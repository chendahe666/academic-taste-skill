#!/usr/bin/env python3
"""Build a tier-stratified paper sample for distilling a field's academic taste.

Taste is learned by contrast, so the sample is split into tiers and each tier is
sampled separately:
  award      best / outstanding / test-of-time papers   (added by hand: --add)
  oral       OpenReview oral (or added by hand)
  spotlight  OpenReview spotlight
  highcite   top-cited papers per year for a topic      (--hc-query)
  poster_highcite  accepted posters the community later cited most (--citations)
  poster     typical accepted papers
  rejected   OpenReview "Submitted to ..." / rejected    (ICLR publishes these)
  withdrawn  withdrawn submissions                       (off unless --tiers lists it)

Sources:
  - OpenReview full-text search per venue, no login (ICLR / NeurIPS / ICML / TMLR / COLM / CoRL ...)
  - Semantic Scholar: arXiv ids, citation counts, top-cited papers. Best with a free key in
    SEMANTIC_SCHOLAR_API_KEY; without one it is tried anonymously and often rate-limited.
  - OpenAlex: fallback for the same (key in OPENALEX_API_KEY; anonymous budget is small
    and shared by everyone behind the same IP)
  - arXiv API: last-resort title -> arXiv id lookup (throttles bursts with HTTP 406)

Each service has its own circuit breaker: once it keeps refusing, the run stops calling it
and carries on with the others. A sampled paper whose arXiv id could not be checked (because
services were refusing) is kept and flagged "needs_arxiv"; fill the id in corpus.json by hand
(WebSearch "<title> arxiv") before running fetch_intros.py. A paper that all live services say
has no arXiv version is replaced by the next candidate of its tier.

Standard library only. Examples:
  python build_corpus.py -t "gaussian splatting" -v ICLR.cc/2024/Conference -v ICLR.cc/2025/Conference \
      -v NeurIPS.cc/2024/Conference --citations --hc-query "gaussian splatting" --out taste/3dgs/raw/corpus
  python build_corpus.py --hc-query "retrieval augmented generation" --from 2021 --per-tier 10 \
      --add "award:2005.11401" --add "oral:Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection"
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OR_API = "https://api2.openreview.net"
S2_API = "https://api.semanticscholar.org/graph/v1"
OA_API = "https://api.openalex.org"
ARXIV_API = "https://export.arxiv.org/api/query"
UA = "academic-taste-skill/1.0 (build_corpus.py)"
TIERS = ["award", "oral", "spotlight", "highcite", "poster_highcite", "poster", "rejected", "withdrawn"]
DEFAULT_TIERS = [t for t in TIERS if t != "withdrawn"]
ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
THIS_YEAR = time.gmtime().tm_year
SURVEY_RE = re.compile(r"\b(survey|review|tutorial|overview|primer)\b", re.I)


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- HTTP with per-service breakers

class Refused(Exception):
    """The service refused (rate limit / throttle / budget) or is switched off for this run."""


class Service:
    def __init__(self, name, min_interval, backoff, max_fail, hint, headers=None):
        self.name, self.min_interval, self.backoff, self.max_fail = name, min_interval, backoff, max_fail
        self.hint, self.headers = hint, headers or {}
        self.off, self.fails, self.last = False, 0, 0.0

    def switch_off(self, why):
        if not self.off:
            log(f"[warn] {self.name}: {why}. Not calling it again in this run. {self.hint}")
        self.off = True

    def get(self, url, as_json=True):
        if self.off:
            raise Refused(self.name)
        for attempt in range(2):
            wait = self.min_interval - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", **self.headers})
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read().decode("utf-8", errors="replace")
                self.fails = 0
                return json.loads(body) if as_json else body
            except urllib.error.HTTPError as e:
                text = e.read()[:400].decode("utf-8", errors="replace")
                if e.code == 404:
                    return None
                if e.code == 429 and "budget" in text.lower():
                    self.switch_off("daily budget used up")
                    raise Refused(self.name)
                if e.code in (403, 406, 429):
                    if attempt == 0:
                        time.sleep(self.backoff)
                        continue
                    self.fails += 1
                    if self.fails >= self.max_fail:
                        self.switch_off(f"keeps refusing (HTTP {e.code})")
                    raise Refused(self.name)
                if e.code >= 500 and attempt == 0:
                    time.sleep(self.backoff)
                    continue
                raise RuntimeError(f"{self.name} HTTP {e.code}: {text[:160]}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == 0:
                    time.sleep(self.backoff)
                    continue
                raise RuntimeError(f"{self.name} network error: {e}")


def make_services():
    s2_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or os.environ.get("S2_API_KEY")
    return {
        "openreview": Service("OpenReview", 0.5, 5, 3, ""),
        "s2": Service("Semantic Scholar", 1.1 if s2_key else 3.5, 6, 2 if s2_key else 2,
                      "A free key (semanticscholar.org/product/api) in SEMANTIC_SCHOLAR_API_KEY makes this reliable.",
                      {"x-api-key": s2_key} if s2_key else None),
        "openalex": Service("OpenAlex", 0.2, 5, 2,
                            "A free key (openalex.org) in OPENALEX_API_KEY lifts the shared anonymous budget."),
        "arxiv": Service("arXiv API", 3.5, 20, 2,
                         "arXiv throttles for ~15 minutes; re-run later, or fill ids by hand."),
    }


SV = make_services()


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def same_title(a, b):
    a, b = norm_title(a), norm_title(b)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    return long_.startswith(short) and len(short) / len(long_) > 0.85


# ---------------------------------------------------------------- OpenReview

def val(content, key):
    v = content.get(key)
    if isinstance(v, dict):
        v = v.get("value")
    if isinstance(v, list):
        v = ", ".join(str(x) for x in v)
    return "" if v is None else str(v)


def or_tier(venue_str):
    s = venue_str.lower()
    if "desk rejected" in s:
        return None
    if "withdrawn" in s:
        return "withdrawn"
    if "reject" in s or s.startswith("submitted to"):
        return "rejected"
    if "oral" in s:
        return "oral"
    if "spotlight" in s:
        return "spotlight"
    return "poster"


def or_search(term, venue, limit):
    notes, offset = [], 0
    while len(notes) < limit:
        page = SV["openreview"].get(f"{OR_API}/notes/search?" + urllib.parse.urlencode(
            {"term": term, "type": "terms", "content": "all", "source": "forum", "group": venue,
             "limit": min(100, limit - len(notes)), "offset": offset})) or {}
        batch = page.get("notes", [])
        if not batch:
            break
        notes += batch
        offset += len(batch)
    return [n for n in notes if n.get("id") == n.get("forum")]


def collect_openreview(terms, venues, require, loose, pool):
    papers, seen = [], set()
    phrases = [t.lower() for t in terms]
    for venue in venues:
        for term in terms:
            try:
                notes = or_search(term, venue, pool)
            except (Refused, RuntimeError) as e:
                log(f"[warn] OpenReview search failed ({venue}, {term}): {e}")
                continue
            for n in notes:
                if n["id"] in seen:
                    continue
                c = n.get("content", {})
                text = " ".join(val(c, k) for k in ("title", "abstract", "keywords")).lower()
                # OpenReview "terms" search matches ANY word; keep papers that contain a whole phrase
                if not loose and not any(p in text for p in phrases):
                    continue
                if any(r.lower() not in text for r in require):
                    continue
                venue_str = val(c, "venue")
                tier = or_tier(venue_str)
                if tier is None:
                    continue
                seen.add(n["id"])
                m = re.search(r"(19|20)\d{2}", venue)
                papers.append(new_paper(tier, val(c, "title"), venue_str or venue, int(m.group(0)) if m else None,
                                        forum=f"https://openreview.net/forum?id={n['id']}",
                                        abstract=val(c, "abstract"), keywords=val(c, "keywords"),
                                        source="openreview"))
        log(f"[openreview] {venue}: {len(papers)} matching submissions so far")
    return papers


def new_paper(tier, title, venue, year, **kw):
    p = {"tier": tier, "title": title, "venue": venue, "year": year, "forum": None, "abstract": "",
         "keywords": "", "source": "", "arxiv": None, "cites": None, "needs_arxiv": False}
    p.update(kw)
    return p


# ---------------------------------------------------------------- lookups (S2 -> OpenAlex -> arXiv)

def arxiv_from_openalex(work):
    blob = [work.get("doi") or "", json.dumps(work.get("ids") or {})]
    for loc in work.get("locations") or []:
        blob += [loc.get("landing_page_url") or "", loc.get("pdf_url") or ""]
    for b in blob:
        if "arxiv" in b.lower():
            m = ARXIV_ID_RE.search(b)
            if m:
                return m.group(1)
    return None


def s2_lookup(title):
    data = SV["s2"].get(f"{S2_API}/paper/search/match?" + urllib.parse.urlencode(
        {"query": title[:300], "fields": "title,year,citationCount,externalIds,abstract"}))
    for w in (data or {}).get("data", []):
        if same_title(w.get("title"), title):
            return {"cites": w.get("citationCount"), "year": w.get("year"),
                    "arxiv": (w.get("externalIds") or {}).get("ArXiv"), "abstract": w.get("abstract") or ""}
    return None


def oa_params(extra):
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        extra["api_key"] = key
    return urllib.parse.urlencode(extra)


def oa_lookup(title):
    data = SV["openalex"].get(f"{OA_API}/works?" + oa_params(
        {"search": title[:250], "per-page": 10, "select": "title,cited_by_count,publication_year,locations,ids,doi"}))
    # OpenAlex often keeps the preprint and the proceedings version as separate works,
    # each with part of the citations: take the best-cited match, and any arXiv id found
    hits = [w for w in (data or {}).get("results", []) if same_title(w.get("title"), title)]
    if not hits:
        return None
    best = max(hits, key=lambda w: w.get("cited_by_count") or 0)
    return {"cites": best.get("cited_by_count"), "year": min(w.get("publication_year") or 9999 for w in hits),
            "arxiv": next((a for a in map(arxiv_from_openalex, hits) if a), None), "abstract": ""}


def parse_atom(xml):
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", xml or "", re.S):
        idm = re.search(r"<id>\s*https?://arxiv\.org/abs/([^<\s]+)\s*</id>", entry)
        tm = re.search(r"<title>(.*?)</title>", entry, re.S)
        sm = re.search(r"<summary>(.*?)</summary>", entry, re.S)
        pm = re.search(r"<published>(\d{4})", entry)
        if idm and tm:
            aid = ARXIV_ID_RE.search(idm.group(1))
            out.append({"arxiv": aid.group(1) if aid else idm.group(1),
                        "title": re.sub(r"\s+", " ", tm.group(1)).strip(),
                        "abstract": re.sub(r"\s+", " ", sm.group(1)).strip() if sm else "",
                        "year": int(pm.group(1)) if pm else None})
    return out


def arxiv_query(params):
    # keep ':' literal in "ti:..." — arXiv answers 406 when it is percent-encoded
    q = "&".join(f"{k}={urllib.parse.quote(str(v), safe=':')}" for k, v in params.items())
    return parse_atom(SV["arxiv"].get(f"{ARXIV_API}?{q}", as_json=False))


def arxiv_lookup(title):
    clean = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]+", " ", title)).strip()
    for e in arxiv_query({"search_query": f'ti:"{clean}"', "max_results": 5}) if clean else []:
        if same_title(e["title"], title):
            return {"cites": None, "year": e["year"], "arxiv": e["arxiv"], "abstract": e["abstract"]}
    return None


_cache = {}


def lookup(title, need_cites, cites_only=False):
    """Returns (info dict, checked) — checked is False when some service we needed was refusing,
    i.e. a missing arXiv id may just mean we could not ask."""
    key = (norm_title(title), need_cites, cites_only)
    if key in _cache:
        return _cache[key]
    info, checked = {"cites": None, "year": None, "arxiv": None, "abstract": ""}, True
    chain = [("s2", s2_lookup), ("openalex", oa_lookup)]
    if not cites_only:
        chain.append(("arxiv", arxiv_lookup))   # has no citations, so only worth asking for an id
    for name, fn in chain:
        if info["arxiv"] and (info["cites"] is not None or not need_cites):
            break
        if name == "arxiv" and info["arxiv"]:
            break
        try:
            got = fn(title)
        except Refused:
            checked = False
            continue
        except RuntimeError as e:
            log(f"[warn] {name} lookup failed for '{title[:50]}': {e}")
            checked = False
            continue
        for k, v in (got or {}).items():
            if info.get(k) in (None, "") and v not in (None, ""):
                info[k] = v
    _cache[key] = (info, checked)
    return info, checked


def resolve(p, need_cites, cites_only=False):
    """Fill arxiv / cites / year / abstract. Returns 'ok', 'unchecked' or 'absent'."""
    if p["arxiv"] and (p["cites"] is not None or not need_cites):
        return "ok"
    info, checked = lookup(p["title"], need_cites, cites_only)
    p["arxiv"] = p["arxiv"] or info["arxiv"]
    p["cites"] = p["cites"] if p["cites"] is not None else info["cites"]
    p["year"] = p["year"] or info["year"]
    p["abstract"] = p["abstract"] or info["abstract"]
    if p["arxiv"]:
        return "ok"
    return "unchecked" if not checked else "absent"


def manual_paper(spec):
    tier, _, what = spec.partition(":")
    tier, what = tier.strip().lower(), what.strip()
    if tier not in TIERS or not what:
        sys.exit(f"--add expects 'tier:arxiv_id_or_title' with tier in {TIERS}; got {spec!r}")
    p = new_paper(tier, what, "(manual)", None, source="manual")
    m = ARXIV_ID_RE.fullmatch(what) or re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", what)
    if m:
        p["arxiv"] = m.group(1)
        p["title"] = m.group(1)
        try:
            e = arxiv_query({"id_list": m.group(1), "max_results": 1})
            if e:
                p.update({"title": e[0]["title"], "abstract": e[0]["abstract"], "year": e[0]["year"]})
        except (Refused, RuntimeError):
            log(f"[info] could not fetch metadata for {m.group(1)}; fetch_intros.py will still read it")
    return p


# ---------------------------------------------------------------- highcite tier

def highcite_s2(queries, year_from, year_to):
    out = []
    for q in queries:
        data = SV["s2"].get(f"{S2_API}/paper/search/bulk?" + urllib.parse.urlencode(
            {"query": f'"{q}"', "fields": "title,year,citationCount,externalIds,venue",
             "sort": "citationCount:desc", "year": f"{year_from}-{year_to or ''}"}))
        for w in (data or {}).get("data", [])[:400]:
            out.append(new_paper("highcite", w.get("title") or "", w.get("venue") or "", w.get("year"),
                                 source="semanticscholar", cites=w.get("citationCount"),
                                 arxiv=(w.get("externalIds") or {}).get("ArXiv")))
    return out


def highcite_openalex(queries, year_from, year_to):
    out = []
    for q in queries:
        filt = f"title_and_abstract.search:{q},from_publication_date:{year_from}-01-01"
        if year_to:
            filt += f",to_publication_date:{year_to}-12-31"
        for page in (1, 2):
            data = SV["openalex"].get(f"{OA_API}/works?" + oa_params(
                {"filter": filt, "sort": "cited_by_count:desc", "per-page": 100, "page": page,
                 "select": "title,cited_by_count,publication_year,locations,ids,doi,primary_location"}))
            for w in (data or {}).get("results", []):
                src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
                out.append(new_paper("highcite", w.get("title") or "", src, w.get("publication_year"),
                                     source="openalex", cites=w.get("cited_by_count"),
                                     arxiv=arxiv_from_openalex(w)))
    return out


def collect_highcite(queries, year_from, year_to, keep_surveys):
    works = []
    for fn in (highcite_s2, highcite_openalex):
        try:
            works = fn(queries, year_from, year_to)
        except (Refused, RuntimeError) as e:
            log(f"[info] highcite via {fn.__name__[9:]} unavailable ({e}); trying next source")
            continue
        if works:
            break
    by_year, seen = {}, set()
    for p in works:
        k = norm_title(p["title"])
        if not k or k in seen or (not keep_surveys and SURVEY_RE.search(p["title"])):
            continue   # surveys tell a different kind of story; keep them out of the contrast
        seen.add(k)
        by_year.setdefault(p["year"], []).append(p)
    for v in by_year.values():
        v.sort(key=lambda p: -(p["cites"] or 0))
    ranked, depth = [], 0   # round-robin across years so old papers do not crowd out recent ones
    while any(depth < len(v) for v in by_year.values()):
        for y in sorted(by_year, key=lambda y: -(y or 0)):
            if depth < len(by_year[y]):
                ranked.append(by_year[y][depth])
        depth += 1
    return ranked


# ---------------------------------------------------------------- sampling

def cite_rate(p):
    if p["cites"] is None:
        return -1
    return p["cites"] / max(1, THIS_YEAR - (p["year"] or THIS_YEAR) + 1)


def interleave(cands, rng):
    groups = {}
    for p in cands:
        groups.setdefault(str(p["year"]) + p["venue"].replace("Submitted to ", "").split(" ")[0], []).append(p)
    for g in groups.values():
        rng.shuffle(g)
    out, keys = [], sorted(groups)
    while any(groups[k] for k in keys):
        for k in keys:
            if groups[k]:
                out.append(groups[k].pop())
    return out


def take(cands, n, need_cites, need_arxiv, label):
    picked = []
    for p in cands[: n * 4]:
        if len(picked) >= n:
            break
        status = resolve(p, need_cites)
        keep = status == "ok" or status == "unchecked" or not need_arxiv
        p["needs_arxiv"] = status == "unchecked"
        mark = {"ok": "ok ", "unchecked": "?? ", "absent": "-- "}[status]
        log(f"  [{label}] {mark} {p['arxiv'] or '':<11} {p['title'][:72]}")
        if keep:
            picked.append(p)
    if len(picked) < n:
        log(f"[info] tier {label}: {len(picked)}/{n} papers")
    return picked


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-t", "--term", action="append", default=[],
                    help="topic phrase for OpenReview search (repeatable); a paper must contain one whole phrase")
    ap.add_argument("-v", "--venue", action="append", default=[],
                    help="OpenReview venue id, e.g. ICLR.cc/2025/Conference (repeatable)")
    ap.add_argument("--require", action="append", default=[],
                    help="extra substring every OpenReview paper must contain (repeatable)")
    ap.add_argument("--loose", action="store_true", help="do not require the whole term phrase")
    ap.add_argument("--pool", type=int, default=300, help="max OpenReview hits per venue x term (default 300)")
    ap.add_argument("--hc-query", "--oa-query", dest="hc_query", action="append", default=[],
                    help="topic phrase for the 'highcite' tier (Semantic Scholar, else OpenAlex; repeatable)")
    ap.add_argument("--keep-surveys", action="store_true", help="allow surveys/reviews in the highcite tier")
    ap.add_argument("--from", dest="year_from", type=int, default=THIS_YEAR - 5)
    ap.add_argument("--to", dest="year_to", type=int, default=None)
    ap.add_argument("--add", action="append", default=[],
                    help="hand-picked paper 'tier:arxiv_id_or_url_or_title' (repeatable), e.g. award:2308.04079")
    ap.add_argument("--citations", action="store_true",
                    help="look up citations for posters and split out a poster_highcite tier")
    ap.add_argument("--cite-cap", type=int, default=60, help="max posters to look up citations for")
    ap.add_argument("--per-tier", type=int, default=8)
    ap.add_argument("--tiers", default=",".join(DEFAULT_TIERS),
                    help=f"comma list of tiers to sample (default: {','.join(DEFAULT_TIERS)})")
    ap.add_argument("--allow-no-arxiv", action="store_true", help="keep sampled papers that have no arXiv version")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="corpus")
    args = ap.parse_args()
    if not (args.term and args.venue) and not args.hc_query and not args.add:
        sys.exit("give -t/-v (OpenReview), --hc-query and/or --add")
    if bool(args.term) != bool(args.venue):
        sys.exit("-t and -v go together")

    rng = random.Random(args.seed)
    tiers = [t.strip() for t in args.tiers.split(",") if t.strip()]
    need_arxiv = not args.allow_no_arxiv
    n = args.per_tier

    pool = collect_openreview(args.term, args.venue, args.require, args.loose, args.pool) if args.term else []
    pool_counts = {}
    for p in pool:
        m = re.match(r"([A-Za-z]+)\s*((?:19|20)\d{2})", p["venue"].replace("Submitted to ", ""))
        key = f"{m.group(1)} {m.group(2)}" if m else p["venue"]
        c = pool_counts.setdefault(key, {})
        c[p["tier"]] = c.get(p["tier"], 0) + 1

    sample = []
    for spec in args.add:  # hand-picked papers are always kept, whatever --tiers says
        p = manual_paper(spec)
        status = resolve(p, need_cites=False)
        p["needs_arxiv"] = status != "ok"
        log(f"  [{p['tier']}] {'ok ' if status == 'ok' else '?? '} {p['arxiv'] or '':<11} {p['title'][:72]}")
        sample.append(p)
    taken = {norm_title(p["title"]) for p in sample}

    def fresh(cands):
        return [p for p in cands if norm_title(p["title"]) not in taken]

    for tier in ("oral", "spotlight", "rejected", "withdrawn"):
        if tier in tiers:
            sample += take(interleave(fresh([p for p in pool if p["tier"] == tier]), rng), n,
                           args.citations, need_arxiv, tier)

    posters = fresh([p for p in pool if p["tier"] == "poster"])
    if args.citations and "poster_highcite" in tiers and posters:
        rng.shuffle(posters)
        looked = posters[: args.cite_cap]
        log(f"[citations] looking up {len(looked)} posters")
        for p in looked:
            if SV["s2"].off and SV["openalex"].off:
                break
            resolve(p, need_cites=True, cites_only=True)
        with_cites = sorted([p for p in looked if p["cites"] is not None], key=cite_rate, reverse=True)
        if not with_cites:
            log("[info] no citation data available: poster_highcite tier skipped")
        chosen = take([dict(p, tier="poster_highcite") for p in with_cites], n, True, need_arxiv, "poster_highcite")
        sample += chosen
        chosen_t = {norm_title(p["title"]) for p in chosen}
        posters = [p for p in posters if norm_title(p["title"]) not in chosen_t]
    if "poster" in tiers and posters:
        sample += take(interleave(posters, rng), n, args.citations, need_arxiv, "poster")

    if args.hc_query and "highcite" in tiers:
        taken = {norm_title(p["title"]) for p in sample}
        cands = [p for p in collect_highcite(args.hc_query, args.year_from, args.year_to, args.keep_surveys)
                 if norm_title(p["title"]) not in taken]
        if not cands:
            log("[info] highcite tier empty (no source answered)")
        sample += take(cands, n, False, need_arxiv, "highcite")

    # de-duplicate across tiers (a paper keeps its first, i.e. strongest, tier)
    final, seen = [], set()
    for p in sorted(sample, key=lambda p: TIERS.index(p["tier"])):
        k = p["arxiv"] or norm_title(p["title"])
        if k not in seen:
            seen.add(k)
            final.append(p)

    services = {k: ("off" if s.off else "ok") for k, s in SV.items()}
    meta = {"terms": args.term, "venues": args.venue, "require": args.require, "hc_queries": args.hc_query,
            "year_from": args.year_from, "per_tier": n, "seed": args.seed,
            "created": time.strftime("%Y-%m-%d"), "pool_counts": pool_counts, "services": services}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out + ".json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "papers": final}, f, ensure_ascii=False, indent=1)

    md = ["# Taste corpus", "", f"Created {meta['created']}. Terms: {args.term or '-'}; "
          f"highcite queries: {args.hc_query or '-'}; venues: {', '.join(args.venue) or '-'}",
          f"Services at the end of the run: {services}", ""]
    if pool_counts:
        md += ["## OpenReview pool (base rates for this topic)", "",
               "| venue | " + " | ".join(TIERS[1:]) + " | total |", "|---|" + "---|" * len(TIERS)]
        for v, c in sorted(pool_counts.items()):
            md.append(f"| {v} | " + " | ".join(str(c.get(t, 0)) for t in TIERS[1:]) + f" | {sum(c.values())} |")
        md += ["", "Shares here describe papers that mention the topic, not the whole venue.", ""]
    md += ["## Sample", "", "| # | tier | year | venue | cites | arXiv | title |", "|---|---|---|---|---|---|---|"]
    for i, p in enumerate(final, 1):
        link = f"[{p['arxiv']}](https://arxiv.org/abs/{p['arxiv']})" if p["arxiv"] else "**needs id**"
        title = p["title"].replace("|", "/")
        if p["forum"]:
            title = f"[{title}]({p['forum']})"
        cites = "" if p["cites"] is None else p["cites"]
        md.append(f"| {i} | {p['tier']} | {p['year'] or ''} | {p['venue']} | {cites} | {link} | {title} |")
    counts = {}
    for p in final:
        counts[p["tier"]] = counts.get(p["tier"], 0) + 1
    md += ["", "Per tier: " + ", ".join(f"{t} {counts[t]}" for t in TIERS if t in counts)]
    missing = [p for p in final if not p["arxiv"]]
    if missing:
        md += ["", "## Papers that still need an arXiv id", "",
               "Services were refusing, so these could not be checked. Find each id (WebSearch "
               "`\"<title>\" arxiv`) and put it in the `arxiv` field of corpus.json, or re-run later.", ""]
        md += [f"- [{p['tier']}] {p['title']}" for p in missing]
    with open(args.out + ".md", "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"wrote {args.out}.json / {args.out}.md — {len(final)} papers "
          f"({', '.join(f'{t} {counts[t]}' for t in TIERS if t in counts)}); "
          f"{len(missing)} still need an arXiv id; services: {services}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
