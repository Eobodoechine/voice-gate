# LinkedIn draft: voice-gate

Grounding (not linted, kept out of the post body by the `## The post` convention):

- Repo: https://github.com/Eobodoechine/voice-gate
- Claims used and where they come from:
  - "exits non-zero on a banned construct" / stdlib only, no install, no API key -> README quick start
  - The loosened-rule regression that let "It's not a tool. It's a system." through -> README, "Precision beats coverage"
  - "The lesson my dad gave me" passes / "The lesson?" fails -> README precision table
- Voice reference: the author's own Qwen Code post (July 2026). Opens on a concrete
  personal moment, long comma-joined sentences, admits something, closes on a stance.
- Length target: ~220 words, matching the Qwen post, not a README restatement.
- This draft passes `python3 voice_check.py drafts/linkedin-voice-gate.md`.

## The post

I kept telling the model how I write, and it kept handing me back drafts with em-dashes all over them, that little "it's not X, it's Y" flip, a neat takeaway glued onto the end like a bow. So I'd go fix it by hand every time, and some nights I'd miss one and post it anyway.

What I finally had to admit is that a prompt can only describe my voice. It has no way to look at the finished draft and tell me whether the draft actually listened.

So I wrote something that does. It reads a draft and fails if it finds a construct I have banned. Python 3, standard library, nothing to install, no API key.

The hard part was never catching the tells, it was not catching everything else. "The lesson my dad gave me" has to pass. "The lesson?" has to fail. I broke this once, I loosened a rule to shut up a false alarm, and that quietly let "It's not a tool. It's a system." sail straight through. The annoying fix had opened a hole I could not see.

I still write my own posts. I just stopped trusting myself to catch my own tells at 1am, and now I do not have to.

This one went through it before it went up.

github.com/Eobodoechine/voice-gate
