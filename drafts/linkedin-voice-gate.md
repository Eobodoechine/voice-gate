# LinkedIn draft: voice-gate

Grounding (not linted, kept out of the post body by the `## The post` convention):

- Repo: https://github.com/Eobodoechine/voice-gate
- Claims used and where they come from:
  - "exits non-zero on a banned construct" / "Python 3, stdlib only, no deps, no API key" -> README quick start + intro
  - The comma-narrowing regression that let "It's not a tool. It's a system." through -> README, "Precision beats coverage"
  - Quoted-mention demotion, and typographic tells never demoted -> README, "Mention is not use."
  - Rules live in voice-rules.json, OFF is a legitimate choice -> README, "Making it yours"
- Voice reference: the author's own Qwen Code post (July 2026). First person, long
  comma-joined sentences, concrete specifics, closes on a stance rather than a takeaway.
- This draft passes `python3 voice_check.py drafts/linkedin-voice-gate.md`.

## The post

I kept writing prompts that described my voice, and the drafts kept coming back carrying the same tells anyway, em-dashes everywhere, that "it's not X, it's Y" pivot, a tidy little takeaway bolted onto the end. A prompt can describe a voice. It has no way to reach into the finished draft afterward and prove the draft actually obeyed it.

So I stopped asking nicely and wrote a linter for it. Point it at a draft and it exits non-zero if the draft carries a construct I have banned. Python 3, standard library, no dependencies, no API key, nothing to install.

The tuning turned out to be the actual work, because every rule has to fire on the banned move and stay quiet on the ordinary sentence that looks identical to it. "The lesson my dad gave me" is fine and "The lesson?" is not. "It's not fun but it's worth it" is fine and the pivot is not. I got this wrong once, I narrowed the pivot rule to require a comma so it would stop flagging something innocent, and that quietly let "It's not a tool. It's a system." walk straight through. Killing a false positive had opened a false negative, and I only caught it because I had fixtures pinning both directions.

The other thing I had to solve is that writing about AI writing means quoting the tells, and I did not want my own post failing on the words I was making fun of. So a phrase inside a short quoted span gets demoted to a warning instead of a block. Typographic tells never get that pass, because there is no way to mention an em-dash without the reader simply seeing one.

The rules that ship are mine and yours will be different, which is why they live in a JSON file you edit rather than Python you fork, and switching one off is a legitimate choice. If you like em-dashes, turn that rule off and keep the rest. A gate you have argued with is worth more than one you inherited.

I ran this post through it before posting.

github.com/Eobodoechine/voice-gate
