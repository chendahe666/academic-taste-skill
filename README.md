# academic-taste

A [Claude Code](https://claude.com/claude-code) skill that distills the **academic taste** of a specific research field from its top-venue papers, then uses that taste to help you frame a research idea you have already chosen.

It is meant to run *after* topic selection, and pairs with [research-ideation](https://github.com/chendahe666/research-ideation-skill).

## Core idea

**Taste is discrimination, and discrimination is learned by contrast.** Reading ten thousand average papers teaches you the average. What teaches taste is seeing, within one field, why one paper became an oral or a best paper, another an ordinary poster, and a third a reject.

So instead of reading broadly, the skill:

- samples papers by **tier**: award, oral, spotlight, highly cited, "poster that was later highly cited", ordinary poster, rejected;
- reads each introduction **blind**, with shuffled order and hidden tiers, so strong papers are not rationalized after the fact;
- turns every observation into a **contrastive, counted rule**, such as "high tier 11/16 vs. low tier 3/16", graded by strength.

Taste is distilled on three layers:

| Layer | Question |
|---|---|
| Idea taste | What problems and insights does this field reward? Where do ideas come from? |
| Story taste | How is the introduction told: opening hook, how the gap is built, where the insight appears, Figure 1, contributions, how strongly claims are worded |
| Evidence taste | What evidence does the introduction promise, and what do reviewers accept? |

One caveat is built in: **an introduction is a post-hoc story, not necessarily how the idea was actually born.** The skill cross-checks stated origins against author talks, blog posts, Test-of-Time talks and cited precursors, and labels its confidence.

## Workflow

1. **Scope.** Narrow the field to one sub-area and one community, pick the target venues, and default to the last 3 years.
2. **Build the corpus.** Take a tier-stratified sample from OpenReview. Add award and highly cited papers, collect author interviews about where ideas came from, and optionally pull public reviews.
3. **Blind dissection.** Write one card per paper: idea origin (12-type taxonomy), gap type, paragraph-by-paragraph narrative moves, key-insight sentence, Figure 1 role, contribution style and claim strength. Each card ends with a blind guess of the paper's tier. Large corpora are split across parallel sub-agents.
4. **Contrastive synthesis.** Count first, then conclude. The output is a taste profile with 10 graded rules, canonical story templates with exemplar papers, anti-patterns, an exemplar library ("one trick worth stealing" per paper), time drift, and known biases.
5. **Apply to your idea.** A taste check of your idea, a sharpened one-sentence insight, and three distinct storylines. Each storyline comes with an introduction skeleton, a Figure 1 sketch, the "evidence debt" it creates, and simulated reviewer reactions. The framing is never allowed to promise more than the experiments can support.
6. **Calibration (optional).** Blind-test the profile on held-out papers to check whether it actually improves tier prediction. The same set doubles as a taste-training exercise for you.

Human checkpoints use a "mentor mode": a default recommendation, at most three things for you to verify yourself, and a one-line reply format. Only two decisions are required from you: the scope, and which storyline to adopt.

## Installation

Clone into your user-level skills directory:

```bash
git clone https://github.com/chendahe666/academic-taste-skill.git ~/.claude/skills/academic-taste
```

Then, in Claude Code, say something like "distill the taste of <field>" or "help me frame my idea the way ICLR reviewers like". The skill's instructions are written in Chinese. Claude follows them fine in any language and replies in the language you use.

## Scripts (Python standard library only)

| Script | What it does |
|---|---|
| `scripts/build_corpus.py` | Tier-stratified sampling. OpenReview keyword search per venue with tiers read from the decision label; citation counts and arXiv ids from Semantic Scholar, OpenAlex or the arXiv API; top-cited papers per year for the `highcite` tier; hand-picked papers via `--add tier:<arXiv id or title>`. |
| `scripts/fetch_intros.py` | Extracts title, abstract, Figure 1 caption, section outline and the full introduction, with numbered paragraphs, from arXiv HTML (falling back to ar5iv). Blind by default: shuffled `P01.md`… files, with tiers kept in `key.json`. |

```bash
python scripts/build_corpus.py -t "gaussian splatting" -v ICLR.cc/2025/Conference --citations \
    --hc-query "gaussian splatting" --add award:2308.04079 --out taste/3dgs/raw/corpus
python scripts/fetch_intros.py --corpus taste/3dgs/raw/corpus.json --out taste/3dgs/raw/intros
```

On Windows, use `py` if `python` is not available.

### Rate limits

Anonymous quotas for Semantic Scholar, OpenAlex and the arXiv API are shared per IP address and are easy to exhaust. Each service in `build_corpus.py` has its own circuit breaker, so the run degrades instead of hanging. Papers whose arXiv id could not be checked are kept and listed as **needs id**, so you can fill them in by hand and re-run `fetch_intros.py --skip-existing`.

For reliable runs, set free API keys:

- `SEMANTIC_SCHOLAR_API_KEY`: get one at <https://www.semanticscholar.org/product/api>. It also gives the most accurate citation counts for CS.
- `OPENALEX_API_KEY`: get one at <https://openalex.org>.

Downloading OpenReview reviews needs your own OpenReview account. See `openreview_reviews.py` in [research-ideation](https://github.com/chendahe666/research-ideation-skill).

## Which venues work best

| Venue type | Tiers available |
|---|---|
| OpenReview venues. ICLR is best because rejected submissions are public; NeurIPS, ICML, COLM, CoRL and TMLR also work. | oral / spotlight / poster / rejected / withdrawn |
| Other venues (CVPR/ICCV/ECCV, ACL*, systems, security, HCI, theory) | award and oral lists found by web search, highly cited papers, and ordinary accepted papers picked from the proceedings |

Without a rejected tier, the contrast becomes "good vs. better" rather than "in vs. out". The profile states this explicitly.

## Repository layout

```
academic-taste/
├── SKILL.md                        # workflow and rules (read by Claude)
├── references/
│   ├── dissection_card.md          # per-paper card template and taxonomies
│   ├── taste_profile_template.md   # profile template and rule-strength criteria
│   ├── apply_to_idea.md            # narrative operators and storyline template for your idea
│   └── priors.md                   # published writing/taste principles, used as hypotheses to test
└── scripts/
    ├── build_corpus.py
    └── fetch_intros.py
```

## Principles

- **No fabricated papers, no dissection from memory.** Every card is based on fetched text. Anything the model merely remembers about a famous paper is kept separate from evidence.
- **Only contrastive rules count.** Generic advice like "write clearly" is not field taste.
- **Small samples call for modesty.** With about 8 papers per tier, a difference of fewer than 3 papers is treated as noise.
- **Quote briefly.** Full texts stay local; outputs quote at most about 25 words at a time.
- **Stay honest.** The storyline serves the facts, never the other way round.
