#!/usr/bin/env python3
"""
voice_check.py - a mechanical gate for your own writing voice.

This is the DRIVER for the build-post skill. A SKILL.md can describe the voice,
but it cannot reach into a draft and prove the draft actually obeys it. This does.
It encodes the mechanical, non-negotiable rules of a voice spec (the taste rules
stay human: seed, register, "does it leave a loose thread").

Usage:
    python3 voice_check.py DRAFT.md          # lint a file
    python3 voice_check.py -                 # lint stdin
    cat draft.md | python3 voice_check.py    # lint stdin
    python3 voice_check.py --selfcheck       # run built-in GOOD/BAD fixtures (smoke test)
    python3 voice_check.py DRAFT.md --full   # lint the whole file, not just the post body

To lint text containing double quotes (which the mention-vs-use tier needs), pipe a
heredoc rather than `echo`:

    python3 voice_check.py - <<'EOF'
    that fake "here's the truth" opener always gets me
    EOF

When a file has a "## The post" heading (the _TEMPLATE.md shape), only that section
is linted by default, grounding/posting notes are ignored. Use --full to lint everything.

Exit codes: 0 PASS, 1 HARD violations (or a failed selfcheck), 2 nothing to lint /
unreadable input. Only HARD violations fail the gate; SOFT is human judgment.
"""
import re
import sys

# ── Rules ────────────────────────────────────────────────────────────────────
# Each rule: (severity, label, compiled_regex, fix_hint). severity in {HARD, SOFT}.
# Regexes run case-insensitive against the prose (markdown scaffolding stripped).

BANNED_WORDS = ["polished", "curated", "elevated", "sophisticated",
                "premium", "refined", "bespoke", "world-class", "masterclass"]

RULES = [
    # Dashes: zero em/en dashes and their substitutes. Hyphens in ranges ("3-6%")
    # and words ("world-changing") are fine. "--" is an em-dash substitute, but
    # "--full" is a CLI flag he writes about, so require a non-word char after.
    ("HARD", "em-dash", re.compile(r"[—–―−‒⸺﹘－]|--(?!\w)"),
     "stitch clauses with a comma, or end the sentence and start a new one"),

    # "It's not X, it's Y" in all punctuation forms (comma, period, semicolon).
    # Requiring PUNCTUATION before the Y lets the natural concession "it's not fun
    # but it's worth it" through, it joins with 'but'. HARD only for PRONOUN
    # subjects (it/this/that/there), where the move is unambiguously the banned
    # reframe. Open subjects go SOFT below: "the eviction wasn't fun, it was a long
    # process" is his narration, structurally identical, and only a human can tell
    # correcting from elaborating.
    # Concession guard is 'though/anyway/for now' ONLY. 'still/yet/honestly' were
    # removed: they're common mid-clause adverbs, so one incidental "still"
    # anywhere in the sentence used to switch the whole rule off.
    ("HARD", "not-X-it's-Y pivot", re.compile(
        r"\b(?:(?:it'?s|it is|its|this is|that is|it was|there is)\s+not|"
        r"(?:it|this|that)\s+(?:isn'?t|wasn'?t))\b"
        r"[^,.;!?\n]{0,60}[,.;]\s*(?:it'?s|it is|its|that'?s|this is|it was)\b"
        r"(?![^.\n]*\b(?:though|anyway|for now)\b)", re.I),
     "drop the setup, just state the thing (say Y, skip 'it's not X')"),
    # Negated-'just' pivot ("isn't just risky", "wasn't just a check"). Bare
    # affirmative "is just" is fine and natural ("the barrier is just english").
    ("HARD", "negated-'just' pivot", re.compile(
        r"\b(isn'?t|is not|wasn'?t|was not|it'?s not|it is not|aren'?t)\s+just\b", re.I),
     "drop the 'not just X' setup, just say the thing plainly"),

    # Hook-bait / engagement bait. Open on the moment, end when the thought ends.
    # The drop/share/comment CTAs are banned in the IMPERATIVE. The test is not
    # position (an imperative can follow "and", "so", "please", "One ask:") but
    # SUBJECT: scan from the clause boundary to the verb and reject the match if a
    # first-person subject got there first. So every soft offer of his passes
    # ("i'll drop a link", "i'd drop a demo", "everything i share below") while
    # "Try it out and drop your story below" is still caught. v2 line 30 keeps the
    # soft parenthetical sell; the Bans line kills "Drop your story below".
    # Deliberately SOFT, not HARD. Kept as SOFT so a draft still shows
    # where it reads as engagement bait, but it never blocks him. Do NOT restore
    # these to HARD without him saying so.
    ("SOFT", "hook-bait", re.compile(
        r"(let'?s talk|let'?s normalize|"
        r"(?:^|[.!?,;:]|\n)(?:(?!\b(?:i|we|my|lemme|imma)\b)[^.!?;:\n]){0,80}?"
        r"(?<!a )(?<!an )(?<!the )(?<!that )(?<!this )(?<!his )(?<!her )"
        r"(?<!their )(?<!any )(?<!every )(?<!will )"
        r"\b(?:drop|share|comment)\b[^.\n]{0,40}?"
        r"\b(?:below|in the (?:comments?|replies))|"
        r"(?:^|[.!?,;:]|\n)(?:(?!\b(?:i|we|my|lemme|imma)\b)[^.!?;:\n]){0,80}?"
        r"\bdrop (?:a|an) \w+ (?:emoji|if you)|"
        r"let me know (?:below|in the comments?)|tell me in the comments?|"
        r"here'?s the truth|here is the truth|let that sink in|"
        r"what do you think\??\s*(👇|$)|thoughts\?\s*(👇|$))", re.I | re.M),
     "reads as engagement bait (a CTA, or an opener like \"here's the truth\" / "
     "\"let that sink in\"). All allowed now, so keep whatever HE wrote. Only cut "
     "it if YOU added it, and for the opener forms also check it against NO BOWS"),
    # Deliberately SOFT, same reason as hook-bait above.
    ("SOFT", "pointer-CTA emoji (👇)", re.compile(r"\U0001F447"),
     "a 'read below' pointer. Allowed now, keep it if he wants it there"),

    # Packaging / listicle framing. The tell is the wrap-up FRAME, not the noun, so
    # lesson/takeaway only fires when followed by '?'/':' or an is/was predicate.
    # That keeps his real "the lessons learned" and "the takeaways from that build"
    # while catching "The lesson?", "The lesson here is", "my biggest lesson was".
    ("HARD", "packaging framing", re.compile(
        r"(here'?s the thing|\bthe moral\b|"
        # A) the labelled wrap-up frame. Determiner optional so bare "Lesson:" and
        #    "Takeaway:" are caught, but then it must be clause-initial, else
        #    "his course has 12 lessons: i watched four" would fire.
        r"(?:(?:^|[.!?]\s+|\n)\s*|"
        r"\b(?:the|my|our|one|a|big|biggest|real|main|first|another)\s+)"
        r"(?:biggest\s+|real\s+|main\s+|first\s+)?"
        r"(?:lesson|takeaway)s?(?:\s+learned)?\s*[?:]|"
        # B) subject + copula ("The lesson here is", "my biggest lesson was").
        #    Window is tight (14) and partitive "one of the lessons is" is
        #    excluded, both are ordinary narration of his, not packaging.
        r"(?<!of\s)\b(?:the|my|our)\s+(?:biggest\s+|real\s+|main\s+|first\s+)?"
        r"(?:lesson|takeaway)s?\b(?!\s+(?:plan|bag|box|note)s?\b)"
        r"[^.\n]{0,14}?\b(?:is|was)\b|"
        # C) the wrap-up posed as a question ("So what's the lesson from all this?")
        r"\b(?:the|my|our)\s+(?:biggest\s+|real\s+|main\s+|first\s+)?"
        r"(?:lesson|takeaway)s?\b[^.\n]{0,25}?\?|"
        r"here'?s what i learned|\bwhat i learned\s*[:?]|"
        r"\b(three|3|two|2) (things|lessons|takeaways|reasons)\b|"
        r"taught me (three|3|two|2)|here are the (three|3|two|2)\b)", re.I),
     "tell it in the order it happened, no 'the lesson?' wrap-up"),

    # ✅/❌ comparison list as a line-leader (a lone ✅ punchline at line-END is his, keep it).
    ("HARD", "✅/❌ list-leader", re.compile(r"(?m)^\s*[✅❌]"),
     "plain paragraphs, no ✅/❌ checklist lines (a single ✅ as a punchline at the end of a line is fine)"),

    # Soft signals — flagged for judgment, do not fail the gate.
    # Open-subject pivot shape. SOFT because "AI isn't the future, it's the present"
    # (banned reframe) and "the eviction wasn't fun, it was a long process" (his
    # narration) are the same shape, so the hint asks instead of prescribing.
    ("SOFT", "possible open-subject pivot", re.compile(
        r"\b(?!it\b|this\b|that\b|there\b)\w+\s+(?:isn'?t|wasn'?t|aren'?t|weren'?t)\b"
        r"[^,.;!?\n]{0,60}[,.;]\s*(?:it'?s|it is|its|that'?s|this is|it was)\b"
        r"(?![^.\n]*\b(?:though|still|yet|honestly|anyway|for now)\b)", re.I),
     "if the second clause CORRECTS the first, that's the banned 'not X, it's Y' "
     "reframe, cut the setup. If it just ELABORATES, keep both and join with "
     "and/so/but (do not delete his first clause)"),
    ("SOFT", "dash-substitute ' - '", re.compile(r"\S \- \S"),
     "a spaced hyphen reads like an em-dash, stitch with a comma instead"),
    ("SOFT", "emoji sub-header", re.compile(r"(?m)^\s*[\U0001F300-\U0001FAFF☀-➿]\s*\w"),
     "no emoji sub-headers, use a plain paragraph"),
    ("SOFT", "possible bow (aphorism)", re.compile(
        r"isn'?t everything.{0,20}\bnot nothing\b|"
        r"\b(\w+) is (the )?(new|real)\b.{0,40}\b\1\b", re.I),
     "kill the quotable-on-purpose line, let it end on a plain concrete detail"),
]


# ── Core ─────────────────────────────────────────────────────────────────────
def extract_post_section(text):
    """If the file uses the _TEMPLATE.md shape, lint only the post body.

    Grounding notes, posting notes, and variations live outside the post and a
    reader never sees them, so em-dashes there are not violations of the POST.
    Returns (body, scoped, base_line) where base_line is the 1-indexed line of the
    body's first line in the ORIGINAL file, so reported line numbers point at the
    real file. Falls back to the whole text when there's no '## The post' heading.
    """
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s*#{1,6}\s+the post\b", ln, re.I):
            start = i + 1
            break
    if start is None:
        return text, False, 1
    body = []
    for ln in lines[start:]:
        if re.match(r"^---\s*$", ln) or re.match(r"^\s*#{1,6}\s+\S", ln):
            break
        body.append(ln)
    return "\n".join(body), True, start + 1


def strip_markdown(text):
    """Keep the prose, drop scaffolding that isn't part of the post itself.

    Removes fenced code blocks, headings, blockquote/list/bold markers, and
    horizontal rules, so linting a post file focuses on the words a reader would
    actually see. It removes MARKERS, never prose.

    Returns (prose, linemap) where linemap[i] is the 0-indexed source line that
    stripped line i came from, so findings can be reported against the real file.

    Fails CLOSED: an unclosed ``` fence keeps its content instead of swallowing
    the rest of the document, and a `**Key:**` prefix is stripped rather than
    dropping the whole line (a bolded lead-in used to delete real prose with it).
    """
    lines = text.splitlines()
    # Only treat fences as fences when they actually pair up; a stray ``` must not
    # silently hide everything after it.
    fence_idx = [i for i, ln in enumerate(lines) if ln.strip().startswith("```")]
    fenced = set()
    for a, b in zip(fence_idx[0::2], fence_idx[1::2]):
        fenced.update(range(a, b + 1))

    out, linemap = [], []
    for i, raw in enumerate(lines):
        if i in fenced:
            continue
        line = raw
        s = line.strip()
        if s.startswith("#"):                       # heading
            continue
        if s in ("---", "***", "___"):              # hr
            continue
        line = re.sub(r"^\s*>+\s?", "", line)       # blockquote marker
        line = re.sub(r"^\s*[-*+]\s+", "", line)    # bullet marker
        # Drop the bold MARKERS but never the text. A "**Key:**" lead-in used to
        # delete its whole line, which hid real prose; stripping just the prefix
        # still hid a tell living inside the prefix ("**Here's the truth:**").
        line = line.replace("**", "").replace("__", "")
        out.append(line)
        linemap.append(i)
    return "\n".join(out), linemap


# Typographic tells CANNOT be demoted by quoting: there is no way to mention an
# em-dash without using one, and the reader still sees the character on the page.
# Only PHRASE tells have a real mention-vs-use distinction.
# (The 👇 pointer used to live here; it's SOFT now, and only HARD rules demote.)
NON_DEMOTABLE = {"em-dash", "✅/❌ list-leader"}

# A mention is short (the longest banned phrase is ~30 chars). A quoted sentence
# is content, not a mention, so it stays HARD, otherwise "wrap the line in quotes"
# is a one-keystroke evasion.
MAX_QUOTE_MENTION = 60


def quoted_spans(prose):
    """Ranges of BALANCED double-quoted regions, paired within each line.

    You write posts ABOUT AI writing, so he quotes the banned phrases to mock
    them ('that fake "here'"'"'s the truth" opener'). Mention is not use.

    Pairs sequentially per line so an unbalanced quote leaves the last one
    UNPAIRED rather than silently re-pairing with a quote further along (which
    would hand an evader a span they never opened), and no span crosses a
    newline. Single quotes are excluded, they're ambiguous with apostrophes.
    """
    spans = []
    offset = 0
    for line in prose.split("\n"):
        # Straight quotes are non-directional, so pair them by typography: a real
        # opening quote is followed by a non-space, a real closing quote is
        # preceded by one. That rejects the stray quote in
        #   i built a "system here's the truth "and it worked out
        # which would otherwise hand out a span nobody opened.
        open_at = None
        for p in [i for i, c in enumerate(line) if c == '"']:
            opens = p + 1 < len(line) and not line[p + 1].isspace()
            closes = p > 0 and not line[p - 1].isspace()
            if open_at is None:
                open_at = p if opens else None
            elif closes:
                spans.append((offset + open_at, offset + p + 1))
                open_at = None
            elif opens:
                open_at = p       # can't close here, but it can start a new quote
            else:
                open_at = None    # stray quote, abandon the pending open rather
                                  # than letting the span run on past it
        opens = [i for i, c in enumerate(line) if c == "“"]
        closes = [i for i, c in enumerate(line) if c == "”"]
        ci = 0
        for o in opens:                                  # curly are directional
            while ci < len(closes) and closes[ci] < o:
                ci += 1
            if ci < len(closes):
                spans.append((offset + o, offset + closes[ci] + 1))
                ci += 1
        offset += len(line) + 1
    return spans


def is_mention(spans, start, end):
    """True if the match sits wholly inside a SHORT quoted span."""
    return any(s <= start and end <= e and (e - s) <= MAX_QUOTE_MENTION
               for s, e in spans)


def split_sentences(prose):
    parts = re.split(r"(?<=[.!?])\s+", prose.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]


def find_staccato(prose):
    """Runs of 3+ consecutive short sentences (<=5 words). His rhythm flows."""
    hits = []
    sents = split_sentences(prose)
    run = []
    for s in sents:
        words = len(re.findall(r"\w+", s))
        if 0 < words <= 5:
            run.append(s)
        else:
            if len(run) >= 3:
                hits.append(run[:])
            run = []
    if len(run) >= 3:
        hits.append(run)
    return hits


def line_of(prose, idx, linemap=None, base_line=1):
    """1-indexed line in the ORIGINAL file, via the strip_markdown line map."""
    stripped_line = prose.count("\n", 0, idx)
    if linemap and stripped_line < len(linemap):
        return base_line + linemap[stripped_line]
    return stripped_line + 1


def check(text, base_line=1):
    """Return (hard, soft, stats). hard/soft are lists of (label, line, snippet, hint)."""
    prose, linemap = strip_markdown(text)
    hard, soft = [], []
    qspans = quoted_spans(prose)

    def add(sev, label, m, hint):
        start = max(0, m.start() - 25)
        end = min(len(prose), m.end() + 25)
        snippet = prose[start:end].replace("\n", " ").strip()
        ln = line_of(prose, m.start(), linemap, base_line)
        if (sev == "HARD" and label not in NON_DEMOTABLE
                and is_mention(qspans, m.start(), m.end())):
            soft.append((f"{label} (quoted)", ln, snippet,
                         "inside quotes, so you're probably naming the tell, not using "
                         "it. Fine if you're mocking it, fix it if it's really your line"))
        else:
            (hard if sev == "HARD" else soft).append((label, ln, snippet, hint))

    for sev, label, rx, hint in RULES:
        for m in rx.finditer(prose):
            add(sev, label, m, hint)

    # Banned words (word-boundary, case-insensitive).
    for w in BANNED_WORDS:
        for m in re.finditer(r"\b" + re.escape(w) + r"\b", prose, re.I):
            add("HARD", f"banned word '{w}'", m,
                "use real / honest / dope / solid, or just describe the thing")

    for run in find_staccato(prose):
        soft.append(("staccato run", 0, " ".join(run)[:70],
                     "flow these into one comma-stitched sentence"))

    sents = split_sentences(prose)
    wordcounts = [len(re.findall(r"\w+", s)) for s in sents] or [0]
    stats = {
        "sentences": len(sents),
        "avg_words": round(sum(wordcounts) / len(wordcounts), 1),
        "longest": max(wordcounts),
        "exclamations": prose.count("!"),
    }
    # Positive-rhythm nudge: his fingerprint is at least one long comma-stitched
    # run. Only meaningful on a real draft, his short comment register is his
    # cleanest voice, so don't nag a one-liner about not having a run-on.
    if sum(wordcounts) >= 40 and max(wordcounts) < 20:
        soft.append(("no long run-on", 0, f"longest sentence is {max(wordcounts)} words",
                     "his fingerprint is a 25-40 word comma-stitched sentence, add one"))

    hard.sort(key=lambda r: r[1])
    soft.sort(key=lambda r: r[1])
    return hard, soft, stats


def report(text, name, full=False):
    scoped, base_line = False, 1
    if not full:
        text, scoped, base_line = extract_post_section(text)
    hard, soft, stats = check(text, base_line)
    print(f"VOICE CHECK — {name}")
    print(f"scope: {'post body only (## The post section)' if scoped else 'whole text'}")
    print("─" * 52)
    # Fail closed: a gate that prints PASS on content it never read is worse than
    # one that errors. Empty input means the draft never reached the rules.
    if not stats["sentences"]:
        print("Result: NO CONTENT (nothing to lint, check the path or the "
              "'## The post' section)")
        return 2
    print(f"HARD violations (must fix): {len(hard)}")
    for label, ln, snip, hint in hard:
        loc = f"line {ln}" if ln else "text"
        print(f"  [{label}] {loc}: “{snip}”")
        print(f"      → {hint}")
    print(f"SOFT warnings (judge): {len(soft)}")
    for label, ln, snip, hint in soft:
        loc = f"line {ln}" if ln else "text"
        print(f"  [{label}] {loc}: “{snip}”")
        print(f"      → {hint}")
    print(f"Rhythm: {stats['sentences']} sentences, avg {stats['avg_words']} words, "
          f"longest {stats['longest']} words, {stats['exclamations']} exclamations")
    result = "FAIL (hard violations)" if hard else "PASS"
    print(f"Result: {result}")
    return 0 if not hard else 1


# ── Self-check (smoke test): the doc's own GOOD/BAD pairs ─────────────────────
GOOD_FIXTURES = {
    "good_arv": "Not knowing your real hosting costs can bite you, even if you're not running anything big. You launch a side project you love, six months later traffic picks up, the free tier is gone, you still pay 3-6% in payment processing and 2-4% in currency conversion and if you only budgeted 5%-10% for infrastructure then you are underwater and will need to raise prices or just eat it because you are stuck.",
    "good_coldcall": "I had that feeling when I first started. It got easier when I was around a bunch of people shipping every day like it's nothing. Sometimes the thought creeps up still but I don't let it stop me from shipping, the good part is on the other side of it",
    # The tail "so the lessons learned" and "wasn't fun but I learned" must NOT
    # trip the packaging / pivot rules.
    "good_rental": "I remember getting my first paying user and my mind was blown. It felt like I got money for doing nothing. There's also the first time to do a refund process which wasn't fun but I learned a lot. I look forward to the more first wins and more new lessons in the future but I'm following you so the lessons learned can be more from your previous experiences and not mine",
    "good_announce": "Currently moving my whole workflow onto a server. Having to have my laptop open for build to continue has been inefficient. So now I am getting a vm, running my notes as the knowledge base, a scheduler as the control plane, and I can kick off jobs from my phone while I'm out. Slightly more cost but time wise it is exponentially worth it.",
    # DJ + builder register: "drop a mix" / "drop a tool" are his, not CTA hook-bait.
    "good_dj": "i'm about to drop a new mix this weekend for the culture, might drop a small tool next week too if it works out, still figuring out the setlist honestly",
    # Concession joined with 'but' must pass, it is not the "it's not X, it's Y" pivot.
    "good_concession": "the migration honestly it's not fun but it's worth it in the end, you learn a lot going through it once and you never forget it",
    # You write about the tools he ships, CLI flags in prose are not em-dashes.
    "good_cliflag": "i pass --full when i want the whole file linted, otherwise it just checks the post body and skips my notes",
    # Punctuation-form concessions are his honest-cost register, not the AI pivot.
    "good_concession_period": "it's not ready. it's close though, i'll ship next week. it was not cheap. it was worth every dollar though",
    # First-person soft offers are his, only imperative CTA bait is banned.
    "good_softoffer": "i'll drop a link if you want the build log, i might drop a demo too if you're curious about the setup",
    # Open-subject comma-splice NARRATION (elaborates, doesn't correct). Must not
    # HARD-fail: a real corpus sample is "which wasn't fun but I learned a lot", one
    # comma from this shape. It may raise a SOFT flag, that's the human's call.
    "good_narration": "the migration wasn't fun, it was a long process, the first rollback wasn't great and it was a learning experience for me",
    # You write ABOUT AI writing, so he QUOTES the tells to mock them. Mention is
    # not use. Found by running a real A/B draft through the gate.
    "good_quoting_tells": 'everything came out sounding like a press release, that fake "here\'s the truth" opener and a "let\'s talk" at the end, i would never say "polished" out loud',
    # Partitive / relative-clause narration is not a packaging frame.
    "good_lesson_narration": "one of the lessons is that nobody reads the spec you wrote, and the lessons i keep relearning is why i log everything now",
    # Every first-person soft-offer shape must survive the imperative-CTA rule.
    "good_soft_offer_forms": "i'll drop a link if you want the build log, i'd drop a demo too, i can drop it below once the repo is public, and everything i share below is from the real logs",
    # drop/share/comment as NOUNS. The CTA rule must test for the verb, not the word.
    "good_comment_noun": "somebody left a comment below my last post asking how i built it, and the comment below from a recruiter is what pushed me to build this",
    # Casual first-person contraction must count as a first-person subject.
    "good_lemme": "lemme drop a tool if you want to try it, lemme share below what actually broke",
    # 'lessons:' mid-sentence as a plain count is not a wrap-up frame.
    "good_lessons_count": "his course has 12 lessons: i watched four of them so far and they were fine",
}
BAD_FIXTURES = {
    "bad_arv": "Not knowing your costs isn't just risky — it's expensive. You launch. Traffic spikes. You panic. Suddenly you're over budget, watching your runway evaporate. The lesson? Know your numbers before you launch.",
    "bad_coldcall": "Shipping fear is real. But here's the truth: discomfort isn't just growth, it's the price of it — ship it anyway. The lesson? do it scared.",
    "bad_rental": "My first paying user taught me three things. Revenue is real. Refunds are brutal. Growth lives outside your comfort zone. It wasn't just a sale — it was a masterclass.",
    # NOTE: named for the BANNED WORDS it pins, not the bow rule. The mirrored
    # sentences here are NOT caught mechanically, bows are human judgment per the
    # NO BOWS section of the v2 doc. Don't read this fixture as bow coverage.
    "bad_banned_words": "His felt like the same old grind. Mine felt the exact same way. This tool is the new normal. Polished, curated, world-class.",

    # Regression guards: the pivot in its NON-comma forms, and the wrap-up forms
    # that survive without '?' or ':'. A verifier caught all of these slipping.
    "bad_pivot_period": "It's not a tool. It's a system. This is not about speed, that's the easy part.",
    "bad_pivot_semicolon": "It's not risky; it's expensive when you actually run the numbers on it",
    "bad_lesson_prose": "The lesson here is know your numbers before you launch, the takeaway for me was simple",
    # Pronoun-subject pivot in its non-comma forms.
    "bad_pivot_generic": "That wasn't the plan, it was better. This isn't a win, it's a redirection.",
    # Rule-of-three and packaging without the literal words already covered.
    "bad_ruleofthree": "Three lessons from my first launch. Here are the two things it taught me.",
    "bad_takeaway_det": "My takeaway? Start before you feel ready. The biggest takeaway: just ship.",
    # ── Quote-demotion boundary guards. Each pins one evasion a verifier proved
    # ── survives an unguarded implementation. Do not delete when tuning quotes.
    # Typographic tells are never demotable, quoting can't unsee the character.
    "bad_quoted_emdash": '"i shipped a tool this week — it works — and they used it"',
    # Whole-line quoting is content, not a mention, so it must not clear the gate.
    "bad_wholeline_quote": '"here\'s the truth, nobody is coming to save you, the lesson? just start, let\'s talk about it"',
    # Apostrophes are not quotes: this must keep its banned word.
    "bad_apostrophe_not_quote": "i won't call it polished, that's not me, i'd rather it stay honest",
    # A tell that STRADDLES a quote boundary is used, not mentioned.
    "bad_straddle_quote": 'it\'s not a "tool", it\'s a system that runs itself',
    # An unbalanced quote must not hand out a span it never opened. Two shapes:
    # the stray close, and the stray close that then RE-PAIRS with a later quote
    # (one extra quote character used to bypass the first fixture).
    "bad_unbalanced_quote": 'i built a "system polished "and it worked out fine',
    "bad_unbalanced_repair": 'i built a "system polished "and it worked" out',
    "bad_unbalanced_short": 'a "b " polished" c',
    # A bolded lead-in must not delete the line it introduces (it used to, so a
    # whole slop line could hide behind "**Here's the truth:**").
    "bad_bold_leadin": "**Here's the truth:** nobody is coming to save you, the lesson? just start.",
    # A stray/unclosed ``` fence must not swallow the rest of the document.
    "bad_unclosed_fence": "```\nIt's not a tool, it's a system. The lesson? just ship it.",
    # CTA forms that must survive the clause-initial narrowing.
    # Packaging frames that must survive the lesson/takeaway precision fix.
    "bad_packaging_frames": "my biggest lesson was simple, know your numbers. The biggest takeaway for me was to log everything. So what's the lesson from all of this?",
    # 'still' is an ordinary adverb and must not switch off the pivot rule.
    "bad_pivot_still": "It's not a tool, it's a system i still run my whole week on.",
    # The uncontracted hook is the same banned hook.
    # Bare and determiner-less packaging frames.
    "bad_packaging_bare": "Lesson: always read the lease twice. Takeaway: get it in writing.",
    "bad_packaging_one": "One lesson: always read the lease twice",
    "bad_packaging_learned": "Lesson learned: never skip the walkthrough. Here's what I learned.",
}

# Fixtures that must PASS the gate (0 HARD) but must still SURFACE a given SOFT
# label. Two jobs: guard against a "just suppress quoted matches" regression, and
# keep the UNBANNED rules (hook-bait, 👇) under test now that they no longer fail
# the gate. Without these, deleting those rules outright would go unnoticed.
SOFT_FIXTURES = {
    "soft_cta_imperative": (
        "That was the whole build. Drop your story in the replies. Share below if it "
        "helped, and tell me in the comments.", "hook-bait"),
    "soft_cta_conjunction": (
        "Try it out and drop your story below, i want to hear it", "hook-bait"),
    "soft_cta_adverb": (
        "Give it a shot then comment below with your result", "hook-bait"),
    "soft_cta_colon": (
        "One ask: drop your story below when you get a minute", "hook-bait"),
    "soft_cta_polite": (
        "Please share below if this was useful to you at all", "hook-bait"),
    "soft_cta_modal": ("You should drop your story below, seriously", "hook-bait"),
    "soft_cta_pronoun": (
        "That's my whole process. Drop yours below, or let me know below what I missed",
        "hook-bait"),
    "soft_hook_opener": (
        "Here is the truth: nobody is coming to save you, so just start already.",
        "hook-bait"),
    "soft_lets_talk": (
        "I shipped the whole thing this week. Let's talk about what broke.",
        "hook-bait"),
    "soft_pointer": ("More on how I built it 👇", "pointer-CTA emoji (👇)"),
    "soft_drop_emoji": (
        "This changed everything for me. Drop a fire emoji if you agree, share below",
        "hook-bait"),
    # Quote-demotion still works on the HARD rules that remain.
    "soft_quoted_banned_word": (
        'everything came out sounding like a press release, i would never say '
        '"polished" out loud', "banned word 'polished' (quoted)"),
}


def selfcheck():
    ok = True
    print("SELF-CHECK — GOOD fixtures must PASS, BAD fixtures must FAIL\n")
    for name, txt in GOOD_FIXTURES.items():
        hard, _, _ = check(txt)
        passed = len(hard) == 0
        ok &= passed
        print(f"  {'ok ' if passed else 'XX '} GOOD {name}: "
              f"{'passed' if passed else 'FALSE-FAILED on ' + ', '.join(h[0] for h in hard)}")
    print()
    for name, txt in BAD_FIXTURES.items():
        hard, _, _ = check(txt)
        failed = len(hard) > 0
        ok &= failed
        labels = ", ".join(sorted({h[0] for h in hard}))
        print(f"  {'ok ' if failed else 'XX '} BAD  {name}: "
              f"{'caught (' + labels + ')' if failed else 'MISSED — no hard violation found'}")
    print()
    for name, (txt, want) in SOFT_FIXTURES.items():
        hard, soft, _ = check(txt)
        seen = any(lbl == want for lbl, _, _, _ in soft)
        good = seen and not hard
        ok &= good
        if hard:
            why = "HARD-failed on " + ", ".join(sorted({h[0] for h in hard}))
        elif not seen:
            why = f"MISSING {want} (rule deleted or suppressed?)"
        else:
            why = f"surfaced {want}, gate not blocked"
        print(f"  {'ok ' if good else 'XX '} SOFT {name}: {why}")
    print()
    print("SELF-CHECK RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck()
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    full = "--full" in argv
    args = [a for a in argv[1:] if not a.startswith("-") or a == "-"]
    try:
        if not args or args[0] == "-":
            return report(sys.stdin.read(), "stdin", full=full)
        with open(args[0], "r", encoding="utf-8") as f:
            return report(f.read(), args[0], full=full)
    except OSError as e:
        # Exit 2, never 1: a missing/unreadable file must not look like a voice
        # violation to a caller that only checks the exit code.
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as e:
        print(f"ERROR: not UTF-8 text: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
