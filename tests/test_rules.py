"""Tests for the user-rules layer.

The engine's own regression suite is `--selfcheck`, which deliberately runs against
the built-in rules. These tests cover the other half: that a user who substitutes
their own preferences actually gets them, and that a broken rules file fails loud
instead of quietly reporting PASS.
"""
import importlib
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
SCRIPT = REPO / "voice_check.py"


def run(text, *args, cwd=None):
    """Run the linter as a subprocess so each case gets clean module state."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "-", *args],
        input=text, capture_output=True, text=True, cwd=str(cwd or REPO),
    )


def write(tmp_path, payload):
    p = tmp_path / "rules.json"
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    return str(p)


def test_builtin_rules_pass_a_word_they_do_not_ban(tmp_path):
    assert run("we should leverage this properly").returncode == 0


def test_extend_banned_words_adds_to_the_builtin_list(tmp_path):
    r = run("we should leverage this properly", "--rules", write(tmp_path, {"extend_banned_words": ["leverage"]}))
    assert r.returncode == 1
    assert "banned word 'leverage'" in r.stdout
    # the built-ins must survive an extend
    assert run("this is polished", "--rules", write(tmp_path, {"extend_banned_words": ["leverage"]})).returncode == 1


def test_banned_words_replaces_the_list(tmp_path):
    text = "this is a polished world-class masterclass"
    assert run(text).returncode == 1
    assert run(text, "--rules", write(tmp_path, {"banned_words": []})).returncode == 0


def test_severity_override_off_removes_a_rule(tmp_path):
    text = "this is a thing — and here it is"
    assert run(text).returncode == 1
    assert run(text, "--rules", write(tmp_path, {"severity_overrides": {"em-dash": "OFF"}})).returncode == 0


def test_severity_override_hard_to_soft_stops_blocking(tmp_path):
    text = "i built it in a week. The lesson? ship early"
    assert run(text).returncode == 1
    r = run(text, "--rules", write(tmp_path, {"severity_overrides": {"packaging framing": "SOFT"}}))
    assert r.returncode == 0
    assert "packaging framing" in r.stdout   # still surfaced, just not blocking


def test_custom_rule_fires(tmp_path):
    rules = {"custom_rules": [{"severity": "HARD", "label": "in-todays-world",
                               "pattern": r"\bin today'?s world\b", "hint": "cut it"}]}
    text = "in today's world everybody says that"
    assert run(text).returncode == 0
    r = run(text, "--rules", write(tmp_path, rules))
    assert r.returncode == 1 and "in-todays-world" in r.stdout


def test_malformed_rules_file_exits_2_not_pass(tmp_path):
    """A broken rules file must never be indistinguishable from a clean draft."""
    r = run("anything at all", "--rules", write(tmp_path, "{ not json"))
    assert r.returncode == 2
    assert "could not read rules file" in r.stderr


def test_bad_custom_regex_exits_2(tmp_path):
    r = run("anything", "--rules", write(tmp_path, {"custom_rules": [{"pattern": "([unclosed"}]}))
    assert r.returncode == 2


def test_missing_rules_file_is_not_an_error(tmp_path):
    """Absent config is the normal case, not a failure."""
    assert run("a perfectly fine sentence about nothing", "--rules", str(tmp_path / "nope.json")).returncode == 0


def test_init_writes_a_usable_starter_file(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT), "--init"], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0
    written = tmp_path / "voice-rules.json"
    assert written.exists()
    cfg = json.loads(written.read_text())
    assert "extend_banned_words" in cfg
    # and it must not clobber an existing file
    assert subprocess.run([sys.executable, str(SCRIPT), "--init"],
                          capture_output=True, text=True, cwd=tmp_path).returncode == 2


def test_selfcheck_ignores_user_rules(tmp_path):
    """--selfcheck is the engine's regression suite; a user file must not skew it."""
    r = subprocess.run([sys.executable, str(SCRIPT), "--selfcheck", "--rules",
                        write(tmp_path, {"banned_words": []})], capture_output=True, text=True)
    assert r.returncode == 0 and "PASS" in r.stdout


def test_list_rules_reports_what_is_active(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT), "--list-rules", "--rules",
                        write(tmp_path, {"severity_overrides": {"em-dash": "OFF"}})],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "em-dash" not in r.stdout


def test_file_argument_still_works_alongside_rules(tmp_path):
    """--rules VALUE must not be mistaken for the input filename."""
    draft = tmp_path / "d.md"
    draft.write_text("a plain honest sentence that breaks nothing at all here")
    r = subprocess.run([sys.executable, str(SCRIPT), str(draft), "--rules",
                        write(tmp_path, {"extend_banned_words": ["zzz"]})],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert str(draft) in r.stdout
