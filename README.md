# voice-gate

A mechanical linter that catches the AI tells in a draft, so a human only has to
judge the things a machine genuinely cannot.

Any writing prompt can *describe* a voice. It cannot reach into the draft afterward
and prove the draft obeyed it. This does. Point it at a draft and it exits non-zero
if the draft carries a construct you have banned.

```bash
python3 voice_check.py DRAFT.md          # lint a file
python3 voice_check.py -                 # lint stdin
python3 voice_check.py DRAFT.md --full   # lint the whole file, not just the post body
python3 voice_check.py --selfcheck       # run the built-in GOOD/BAD fixtures
```

Python 3, standard library only. Nothing to install.

## What it catches

**HARD** (exit 1, the gate fails):

- Em-dashes and every substitute for them (`—` `–` `―` `−` `‒` `⸺` `﹘` `－` and `--` used as a dash)
- `it's not X, it's Y` pivots, in every punctuation form (comma, period, semicolon) and with any subject
- `isn't just X` pivots
- Wrap-up packaging: `The lesson?`, `The lesson here is`, `My takeaway?`, rule-of-three listicles
- ✅/❌ used as checklist line leaders
- Corporate filler: polished, curated, elevated, sophisticated, premium, refined, bespoke, world-class, masterclass

**SOFT** (surfaced, never blocks): hook-bait, the 👇 pointer, staccato runs, possible
aphorisms and mirrored "quotable" lines, and the open-subject pivot that may be
ordinary narration rather than a reframe. These are judgment, so the tool reports
them and gets out of the way.

## The two ideas worth stealing

**Mention is not use.** If you write *about* AI writing, you have to be able to quote
the tells in order to mock them. A phrase tell inside a short double-quoted span is
demoted to SOFT and labelled `(quoted)`. Typographic tells are never demoted, because
there is no way to mention an em-dash without the reader seeing one.

**Precision beats coverage.** Every rule is tuned so it fires on the banned move and
stays silent on the legitimate one that looks identical:

| Passes | Fails |
|---|---|
| "the lessons learned", "the lesson my dad gave me" | "The lesson?", "The lesson here is", "The biggest takeaway:" |
| "it's not fun but it's worth it", "it's not ready. it's close though" | "It's not X, it's Y" in any punctuation form |
| "the barrier is just english" | "the barrier isn't just english, it's confidence" |
| "i'll drop a link", "a comment below from a recruiter" | (drop/share CTAs are SOFT, not blocked) |
| "3-6%", "5%-10%", `--full` | `--` used as a dash |

Loosening a rule to kill a false positive quietly opens a false negative. That
happened here once: narrowing the pivot rule to require a comma let *"It's not a
tool. It's a system."* straight through. Both directions are now pinned by fixtures,
which is why `--selfcheck` exists and why you should run it after every rule edit.

## Making it yours

The rules shipped here are one writer's bans. Yours will differ, and the useful part
is the shape rather than the list.

1. Edit the constants at the top of `voice_check.py` (banned words, the phrase lists).
2. Add a GOOD fixture for a real sentence of yours that a new rule must not break, and
   a BAD fixture for the exact move you are banning.
3. Run `python3 voice_check.py --selfcheck`.
4. Sweep your own archive. Every piece you actually published should pass:

```bash
for f in posts/*.md; do python3 voice_check.py "$f" >/dev/null 2>&1 || echo "NOT-CLEAN $f"; done
```

If a rule change makes something you really wrote fail, the rule is wrong. That sweep
is the regression suite, and it catches exit code 2 ("nothing to lint") which a
`grep FAIL` would silently skip.

## What it deliberately cannot do

It cannot see over-craftedness. A draft can pass every rule here and still read as
machine-written because every paragraph resolves too cleanly and the ending ties a
bow. Real writing tends to end where the thought ended, on a loose thread. That call
stays yours, and no linter is going to take it from you.

## License

MIT
