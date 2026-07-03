#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for probe_cli.py. Run from skills/n2d-video/scripts/."""
import probe_cli as pc


MULTIFRAME_HELP = """Usage:
  dreamina multiframe2video [flags]

Upload multiple local images...

Flags:
      --images strings                    local reference image paths
      --prompt string                     shorthand prompt for exactly 2 images
      --duration float                    shorthand transition duration
      --transition-prompt stringArray     repeat once per transition segment
      --transition-duration stringArray   repeat once per transition segment
      --session int                       session id (default 0)
      --poll int                          submit then poll
  -h, --help                              help for multiframe2video

Global Flags:
      --version   print build version information
"""


def test_parse_flags_extracts_long_flags():
    flags = pc.parse_flags(MULTIFRAME_HELP)
    assert "images" in flags
    assert "transition-prompt" in flags
    assert "transition-duration" in flags
    assert "version" in flags  # from Global Flags
    # -h/--help short+long: long name captured
    assert "help" in flags


def test_parse_flags_ignores_prose():
    # words in the description must not be mistaken for flags
    assert "Upload" not in pc.parse_flags(MULTIFRAME_HELP)


def test_verify_detects_missing_flag(monkeypatch):
    monkeypatch.setattr(pc, "run_help", lambda b, c: (0, MULTIFRAME_HELP))
    ok, msg = pc.verify("dreamina", "/fake/dreamina", "multiframe2video",
                        ["images", "transition-prompt"])
    assert ok
    ok2, msg2 = pc.verify("dreamina", "/fake/dreamina", "multiframe2video",
                          ["images", "nonexistent-flag"])
    assert not ok2 and "nonexistent-flag" in msg2


def test_verify_fails_without_binary():
    ok, msg = pc.verify("dreamina", None, "multiframe2video", ["images"])
    assert not ok and "not found" in msg


def test_probe_skips_when_binary_missing(tmp_path, monkeypatch):
    report = pc.probe("dreamina", None)
    assert report["available"] is False and "not found" in report["reason"]


def test_live_cli_contract_if_installed():
    """If dreamina is actually installed, its multiframe2video must still expose the
    flags video_runner builds args from — this is the 'run it every time' guard."""
    import shutil
    binary = shutil.which("dreamina")
    if not binary:
        return  # not installed in this env; skip
    ok, msg = pc.verify("dreamina", binary, "multiframe2video",
                        ["images", "prompt", "duration", "transition-prompt", "transition-duration"])
    assert ok, msg
