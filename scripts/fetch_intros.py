#!/usr/bin/env python3
"""Fetch the parts of a paper that carry its story: title, abstract, Figure 1 caption,
section outline and the full Introduction, with numbered paragraphs.

Reads the arXiv HTML rendering (arxiv.org/html, falling back to ar5iv for older papers).
Writes one markdown file per paper so dissection can be split across agents.

Blind mode (default): files are named P01.md, P02.md ... in shuffled order and do not
show the tier; the tier key goes to key.json. The reader then judges each introduction
before knowing whether it was an oral or a reject. Use --reveal to put tiers in the files.

Standard library only. Examples:
  python fetch_intros.py --corpus taste/3dgs/raw/corpus.json --out taste/3dgs/raw/intros
  python fetch_intros.py 2308.04079 2311.16493 --out intros --reveal
"""
import argparse
import html
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser

UA = "academic-taste-skill/1.0 (fetch_intros.py)"
ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?", re.I)
INTRO_RE = re.compile(r"introduction|^\s*\d*\.?\s*(overview|motivation|background and motivation)\s*$", re.I)


class Blocks(HTMLParser):
    """Flattens LaTeXML HTML into heading / paragraph / list-item blocks plus figure captions."""

    SKIP = {"script", "style", "table", "nav", "footer", "header"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []          # ("h", level, text) | ("p", text) | ("li", text)
        self.captions = []        # (block_index_when_seen, caption_text)
        self.buf = []
        self.heading = None
        self.li_depth = 0
        self.skip_depth = 0
        self.math_depth = 0
        self.fig_depth = 0
        self.cap_depth = 0
        self.cap_buf = []
        self.title = ""
        self.in_title = False

    def flush(self):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if not text:
            return
        if self.heading is not None:
            self.blocks.append(("h", self.heading, text))
        elif self.li_depth:
            self.blocks.append(("li", text))
        else:
            self.blocks.append(("p", text))

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if self.skip_depth:
            if tag in self.SKIP:
                self.skip_depth += 1
            return
        if tag in self.SKIP:
            self.skip_depth = 1
            return
        if tag == "math":
            if self.math_depth == 0:
                alt = dict(attrs).get("alttext")
                if alt:
                    (self.cap_buf if self.cap_depth else self.buf).append(f" ${alt}$ ")
            self.math_depth += 1
            return
        if tag == "figure":
            if self.fig_depth == 0:
                self.flush()
            self.fig_depth += 1
            return
        if tag == "figcaption":
            self.cap_depth += 1
            return
        if self.fig_depth:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = int(tag[1])
        elif tag == "li":
            self.flush()
            self.li_depth += 1
        elif tag in ("p", "div", "section", "br"):
            self.flush()

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if self.skip_depth:
            if tag in self.SKIP:
                self.skip_depth -= 1
            return
        if tag == "math":
            self.math_depth = max(0, self.math_depth - 1)
            return
        if tag == "figcaption":
            self.cap_depth = max(0, self.cap_depth - 1)
            if self.cap_depth == 0:
                cap = re.sub(r"\s+", " ", "".join(self.cap_buf)).strip()
                self.cap_buf = []
                if cap and self.fig_depth <= 1:   # outer caption only, not sub-figure labels
                    self.captions.append((len(self.blocks), cap))
            return
        if tag == "figure":
            self.fig_depth = max(0, self.fig_depth - 1)
            self.cap_buf = []
            return
        if self.fig_depth:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = None
        elif tag == "li":
            self.flush()
            self.li_depth = max(0, self.li_depth - 1)
        elif tag in ("p", "div", "section"):
            self.flush()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.skip_depth or self.math_depth:
            return
        if self.cap_depth:
            self.cap_buf.append(data)
        elif not self.fig_depth:
            self.buf.append(data)


def fetch(url, retries=3):
    delay = 3.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def get_html(aid):
    for url in (f"https://arxiv.org/html/{aid}", f"https://ar5iv.labs.arxiv.org/html/{aid}"):
        page = fetch(url)
        if page and "ltx_section" in page:   # failed conversions return a stub without sections
            return url, page
    return None, None


def extract(page, max_chars):
    parser = Blocks()
    parser.feed(page)
    parser.flush()
    b = parser.blocks
    title = re.sub(r"\s+", " ", html.unescape(parser.title)).strip()

    abstract, abs_i = "", None
    for i, x in enumerate(b):
        if x[0] == "h" and x[2].lower().startswith("abstract"):
            abs_i = i
            abstract = " ".join(y[1] for y in b[i + 1:i + 4] if y[0] == "p")
            break

    heads = [(i, x[1], x[2]) for i, x in enumerate(b) if x[0] == "h"]
    top = min((lvl for _, lvl, t in heads if not t.lower().startswith("abstract")), default=2)
    outline = [t for _, lvl, t in heads if lvl <= top + 1 and not t.lower().startswith("abstract")]

    start = next((i for i, lvl, t in heads if lvl <= top + 1 and INTRO_RE.search(t)), None)
    if start is None:   # no explicit Introduction heading: take the first section after the abstract
        start = next((i for i, lvl, t in heads if lvl == top and (abs_i is None or i > abs_i)), None)
    intro, level = [], None
    if start is not None:
        level = b[start][1]
        for x in b[start + 1:]:
            if x[0] == "h" and x[1] <= level:
                break
            intro.append(x)
    end = start + 1 + len(intro) if start is not None else 0

    fig1 = ""
    for pos, cap in parser.captions:
        if re.match(r"\s*(figure|fig\.?)\s*1\b", cap, re.I):
            fig1 = cap
            break
    if not fig1 and parser.captions and parser.captions[0][0] <= end:
        fig1 = parser.captions[0][1]   # first figure appears before the intro ends: treat as teaser

    lines, n_par, words, used = [], 0, 0, 0
    for x in intro:
        if used > max_chars:
            lines.append("... [introduction truncated]")
            break
        if x[0] == "h":
            lines.append(f"**[sub-heading] {x[2]}**")
            continue
        text = x[1]
        words += len(text.split())
        used += len(text)
        if x[0] == "li":
            lines.append(f"- {text}")
        else:
            n_par += 1
            lines.append(f"[¶{n_par}] {text}")
    return {"title": title, "abstract": abstract, "outline": outline, "fig1": fig1,
            "intro_heading": b[start][2] if start is not None else "", "intro": lines,
            "paragraphs": n_par, "words": words}


def slug(s, n=50):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n] or "paper"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="arXiv ids or URLs (used when --corpus is not given)")
    ap.add_argument("--corpus", help="corpus.json written by build_corpus.py")
    ap.add_argument("--out", default="intros", help="output directory")
    ap.add_argument("--reveal", action="store_true", help="show tier/venue/citations inside each file")
    ap.add_argument("--max-chars", type=int, default=16000, help="cap on introduction length")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-existing", action="store_true",
                    help="keep files already extracted in a previous run (same corpus + seed gives the same Pxx ids); "
                         "use after filling missing arXiv ids in corpus.json")
    args = ap.parse_args()

    if args.corpus:
        with open(args.corpus, encoding="utf-8") as f:
            papers = json.load(f)["papers"]
    else:
        papers = []
        for t in args.ids:
            m = ARXIV_ID_RE.search(t)
            if m:
                papers.append({"tier": "unlabeled", "title": "", "arxiv": m.group(1), "venue": "", "year": None,
                               "cites": None, "forum": None})
    if not papers:
        sys.exit("no papers given")
    if not args.reveal:
        random.Random(args.seed).shuffle(papers)

    os.makedirs(args.out, exist_ok=True)
    key, index = {}, ["# Introductions", "",
                      "Blind set: tiers are in key.json — do not open it until every card is written."
                      if not args.reveal else "Tiers shown in each file.", "",
                      "| id | words | ¶ | fig1 | title |", "|---|---|---|---|---|"]
    ok = 0
    for n, p in enumerate(papers, 1):
        pid = f"P{n:02d}"
        aid = p.get("arxiv")
        print(f"[{n}/{len(papers)}] {pid} {aid or '(no arXiv)'} {p.get('title', '')[:60]}", file=sys.stderr)
        key[pid] = {k: p.get(k) for k in ("tier", "title", "venue", "year", "cites", "arxiv", "forum")}
        name = f"{pid}.md" if not args.reveal else f"{pid}_{slug(p.get('tier') or 'unlabeled', 20)}_{slug(p.get('title') or aid or pid, 40)}.md"
        path = os.path.join(args.out, name)
        if args.skip_existing and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                prev = f.read()
            if "## Introduction" in prev:
                key[pid]["file"] = name
                m = re.search(r"\((\d+) words, (\d+) paragraphs\)", prev)
                fig = "yes" if "_(no figure" not in prev else "no"
                index.append(f"| {pid} | {m.group(1) if m else '?'} | {m.group(2) if m else '?'} | {fig} | "
                             f"{(p.get('title') or aid or pid)[:80]} |")
                ok += 1
                print("  kept from previous run", file=sys.stderr)
                continue
        info = None
        if aid:
            try:
                url, page = get_html(aid)
                if page:
                    info = extract(page, args.max_chars)
                    info["url"] = url
            except Exception as e:
                print(f"  fetch failed: {e}", file=sys.stderr)
        title = (info or {}).get("title") or p.get("title") or aid or pid
        key[pid]["file"] = name
        md = [f"# {pid} — {title}", ""]
        if aid:
            md.append(f"arXiv: [{aid}](https://arxiv.org/abs/{aid})")
        if args.reveal:
            md.append(f"Tier: **{p.get('tier')}** · Venue: {p.get('venue') or '?'} · Year: {p.get('year') or '?'}"
                      f" · Citations: {p.get('cites') if p.get('cites') is not None else '?'}")
        md.append("")
        if not info or not info["intro"]:
            md += ["_Introduction not extracted (no arXiv HTML, or no section found)._",
                   f"_Read it from the PDF instead: https://arxiv.org/pdf/{aid}_" if aid else
                   "_No arXiv id in corpus.json. Find it (WebSearch the title + arxiv), put it in the "
                   "`arxiv` field, and re-run with --skip-existing._", ""]
            if p.get("abstract"):
                md += ["## Abstract", "", p["abstract"], ""]
            index.append(f"| {pid} | — | — | — | {title[:80]} (NOT EXTRACTED) |")
        else:
            ok += 1
            md += ["## Abstract", "", info["abstract"] or p.get("abstract") or "_(not found)_", "",
                   "## Figure 1 caption", "", info["fig1"] or "_(no figure before/within the introduction)_", "",
                   "## Section outline", "", " / ".join(info["outline"]), "",
                   f"## Introduction — “{info['intro_heading']}” ({info['words']} words, {info['paragraphs']} paragraphs)",
                   ""] + [line + "\n" for line in info["intro"]]
            index.append(f"| {pid} | {info['words']} | {info['paragraphs']} | {'yes' if info['fig1'] else 'no'} | {title[:80]} |")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
        time.sleep(1.0)

    with open(os.path.join(args.out, "key.json"), "w", encoding="utf-8") as f:
        json.dump(key, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index) + "\n")
    print(f"wrote {len(papers)} files to {args.out} ({ok} with an extracted introduction); tiers in key.json")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
