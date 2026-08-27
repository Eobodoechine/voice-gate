# voice-gate

A mechanical linter that catches the AI tells in a draft, so a human only has to
judge the things a machine genuinely cannot.

Any writing prompt can *describe* a voice. It cannot reach into the draft afterward
and prove the draft obeyed it. This does. Point it at a draft and it exits non-zero
if the draft carries a construct you have banned.

Python 3, standard library only. Nothing to install, no dependencies, no API key.

## Quick start

```bash
git clone https://github.com/Eobodoechine/voice-gate.git
cd voice-gate

echo "This isn't just a tool — it's a system. The lesson? ship." | python3 voice_check.py -
```

That fails on three separate rules at once (the em-dash, the "isn't just X" pivot, and
the "The lesson?" wrap-up), which is the fastest way to see what the thing does. Then
make it yours:

```bash
python3 voice_check.py --init          # writes voice-rules.json for your own bans
python3 voice_check.py --list-rules    # shows exactly which rules are active
```

## Everyday use

```bash
python3 voice_check.py DRAFT.md          # lint a file
python3 voice_check.py -                 # lint stdin
python3 voice_check.py DRAFT.md --full   # lint the whole file, not just the post body
python3 voice_check.py --rules mine.json DRAFT.md   # use a specific rules file
python3 voice_check.py --selfcheck       # the engine's built-in GOOD/BAD fixtures
```

Exit codes: **0** pass, **1** hard violations, **2** nothing to lint or a broken input.
Exit 2 is deliberately distinct from 1, so a missing file never looks like a voice
violation to a script that only reads the exit code.

If a file has a `## The post` heading, only that section is linted by default, so your
own notes and grounding do not count against the draft. `--full` lints everything.

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

The rules that ship here are one writer's bans. Yours will differ, and the useful part
is the shape rather than the list. You do not edit Python to change them.

```bash
python3 voice_check.py --init          # writes voice-rules.json, commented
python3 voice_check.py --list-rules    # shows exactly what is active
```

`voice-rules.json` is picked up automatically from the current directory. Override with
`--rules path/to/file.json` or the `VOICE_GATE_RULES` environment variable. No file
anywhere means the built-in rules run unchanged.

Every key is optional. Anything you leave out falls back to the built-in behavior.

```jsonc
{
  // Words you personally never say, added to the built-in list.
  "extend_banned_words": ["leverage", "synergy", "unlock"],

  // Or replace the list outright. [] switches the banned-word rule off entirely.
  "banned_words": null,

  // Retune any built-in rule by its label: HARD blocks, SOFT warns, OFF removes it.
  // Labels are exactly what --list-rules prints.
  "severity_overrides": { "hook-bait": "SOFT", "em-dash": "OFF" },

  // Your own rules. Matched case-insensitively against the prose, markdown stripped.
  "custom_rules": [
    { "severity": "HARD",
      "label": "in today's world opener",
      "pattern": "\\bin today'?s (?:world|landscape|economy)\\b",
      "hint": "cut it and open on the actual moment" }
  ],

  // Longest double-quoted span still treated as MENTIONING a tell rather than using it.
  "max_quote_mention": 60
}
```

**Turning a rule OFF is a legitimate choice.** Every rule here came from one person's
taste. If you like em-dashes, turn the em-dash rule off and keep the rest. A gate you
have argued with is worth more than one you inherited.

### The regexes are deliberately not editable

You can add your own patterns, but the built-in ones are not exposed as editable strings.
That is on purpose. Loosening a tuned regex to kill a false positive quietly opens a
false negative, which happened here once: narrowing the pivot rule to require a comma let
*"It's not a tool. It's a system."* straight through. Both directions are pinned by
fixtures now. If a built-in rule genuinely does not fit you, turn it `OFF` and write your
own rather than filing down the one that is tested.

### Then sweep your own archive

This is the step people skip, and it is the one that tells you whether your rules are
right. Every piece you actually published should pass:

```bash
for f in posts/*.md; do python3 voice_check.py "$f" >/dev/null 2>&1 || echo "NOT-CLEAN $f"; done
```

If a rule makes something you really wrote fail, the rule is wrong. That sweep is your
regression suite, and it catches exit code 2 ("nothing to lint") which a `grep FAIL`
would silently skip.

## Running the tests

```bash
python3 voice_check.py --selfcheck    # the engine's own GOOD/BAD fixtures
pip install pytest && pytest tests/ -q # 13 tests for the user-rules layer
```

`--selfcheck` deliberately ignores your rules file. It is the regression suite for the
engine, not for your customisations; sweeping your own archive is how you test those.

## What it deliberately cannot do

It cannot see over-craftedness. A draft can pass every rule here and still read as
machine-written because every paragraph resolves too cleanly and the ending ties a
bow. Real writing tends to end where the thought ended, on a loose thread. That call
stays yours, and no linter is going to take it from you.

## License

MIT
