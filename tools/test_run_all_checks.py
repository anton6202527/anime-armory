#!/usr/bin/env python3
"""Guard tests for the repo-level regression gate scripts.

Run: cd tools && python3 -m pytest test_run_all_checks.py

The gate itself (tools/run_all_checks.sh) runs pytest/validate/independence, so we
do not invoke it recursively here. We only assert the scripts stay valid, executable,
and keep the contract other tooling/docs depend on (modes, hook wiring).
"""
import os
import stat
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
GATE = os.path.join(REPO, "tools", "run_all_checks.sh")
HOOK = os.path.join(REPO, ".githooks", "pre-commit")
CI = os.path.join(REPO, ".github", "workflows", "ci.yml")


def test_gate_script_exists_and_executable():
    assert os.path.isfile(GATE)
    assert os.stat(GATE).st_mode & stat.S_IXUSR, "run_all_checks.sh must be executable"


def test_gate_script_valid_bash():
    r = subprocess.run(["bash", "-n", GATE], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_gate_supports_documented_modes():
    text = open(GATE, encoding="utf-8").read()
    for mode in ("--fast", "--changed"):
        assert mode in text, f"gate must keep documented mode {mode}"
    # The gate must wire the two governance checks every entrypoint relies on.
    assert "validate_skills.py" in text
    assert "check_independence.py" in text
    assert "self_audit.py" in text
    assert "--fail-on-block" in text


def test_pre_commit_hook_valid_and_delegates_to_gate():
    assert os.path.isfile(HOOK)
    assert os.stat(HOOK).st_mode & stat.S_IXUSR, "pre-commit hook must be executable"
    r = subprocess.run(["bash", "-n", HOOK], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "run_all_checks.sh" in open(HOOK, encoding="utf-8").read()


def test_ci_workflow_invokes_gate():
    assert os.path.isfile(CI)
    assert "run_all_checks.sh" in open(CI, encoding="utf-8").read()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
