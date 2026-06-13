import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cleanup


def make_skills(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    (root / "common" / "__pycache__").mkdir(parents=True)
    (root / "common" / "__pycache__" / "x.cpython-314.pyc").write_bytes(b"cache")
    (root / "mv-plan").mkdir()
    (root / "mv-plan" / ".DS_Store").write_text("junk", encoding="utf-8")
    (root / "song" / "scripts").mkdir(parents=True)
    (root / "song" / "scripts" / "draft.py~").write_text("junk", encoding="utf-8")
    (root / "song" / "scripts" / "keep.py").write_text("print('keep')\n", encoding="utf-8")
    (root / "empty").mkdir()
    return root


def test_scan_finds_allowlisted_junk(tmp_path):
    root = make_skills(tmp_path)
    candidates = cleanup.scan(root)
    paths = {c.path for c in candidates}
    assert "common/__pycache__" in paths
    assert "mv-plan/.DS_Store" in paths
    assert "song/scripts/draft.py~" in paths
    assert "song/scripts/keep.py" not in paths
    assert "empty" not in paths
    assert all(c.auto_clean for c in candidates)


def test_clean_removes_auto_candidates_but_keeps_source(tmp_path):
    root = make_skills(tmp_path)
    candidates = cleanup.scan(root)
    for candidate in candidates:
        if candidate.auto_clean:
            cleanup.remove_candidate(root, candidate)

    assert not (root / "common" / "__pycache__").exists()
    assert not (root / "mv-plan" / ".DS_Store").exists()
    assert not (root / "song" / "scripts" / "draft.py~").exists()
    assert (root / "song" / "scripts" / "keep.py").exists()


def test_empty_dirs_require_explicit_flag(tmp_path):
    root = make_skills(tmp_path)
    assert "empty" not in {c.path for c in cleanup.scan(root)}
    candidates = cleanup.scan(root, include_empty_dirs=True)
    empty = [c for c in candidates if c.path == "empty"]
    assert empty and empty[0].auto_clean is True


def test_clean_include_empty_dirs_removes_dirs_that_become_empty(tmp_path):
    root = tmp_path / "skills"
    (root / "only-cache" / "__pycache__").mkdir(parents=True)
    (root / "only-cache" / "__pycache__" / "x.pyc").write_bytes(b"cache")

    code = cleanup.main(["clean", str(root), "--include-empty-dirs", "--json"])

    assert code == 0
    assert not (root / "only-cache").exists()


def test_placeholder_skill_is_review_only(tmp_path):
    root = tmp_path / "skills"
    skill = root / "n2d-update"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: n2d-update\ndescription: [TODO: Complete and informative explanation]\n---\n",
        encoding="utf-8",
    )

    candidates = cleanup.scan(root)
    assert len(candidates) == 1
    assert candidates[0].path == "n2d-update"
    assert candidates[0].auto_clean is False


def test_json_mode_outputs_candidates(tmp_path, capsys):
    root = make_skills(tmp_path)
    code = cleanup.main(["scan", str(root), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "scan"
    assert payload["summary"]["auto_clean"] >= 1
    assert any(c["path"] == "common/__pycache__" for c in payload["candidates"])


def test_repo_scan_finds_root_caches_and_prunes_review_dirs(tmp_path):
    root = tmp_path / "repo"
    (root / ".pytest_cache").mkdir(parents=True)
    (root / ".pytest_cache" / "README.md").write_text("cache", encoding="utf-8")
    (root / "desktop" / "node_modules" / "pkg" / "__pycache__").mkdir(parents=True)
    (root / "desktop" / "node_modules" / "pkg" / "__pycache__" / "x.pyc").write_bytes(b"cache")

    candidates = cleanup.scan(root)
    by_path = {c.path: c for c in candidates}

    assert ".pytest_cache" in by_path
    assert by_path[".pytest_cache"].auto_clean is True
    assert "desktop/node_modules" in by_path
    assert by_path["desktop/node_modules"].auto_clean is False
    assert "desktop/node_modules/pkg/__pycache__" not in by_path


def test_repo_mode_reports_logs_but_does_not_auto_clean(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    log = root / "生产运行.log"
    log.write_text("keep for audit", encoding="utf-8")

    default_candidates = cleanup.scan(root)
    default_by_path = {c.path: c for c in default_candidates}
    assert default_by_path["生产运行.log"].auto_clean is True

    repo_candidates = cleanup.scan(root, repo_mode=True)
    repo_by_path = {c.path: c for c in repo_candidates}
    assert repo_by_path["生产运行.log"].kind == "review-log-file"
    assert repo_by_path["生产运行.log"].auto_clean is False

    for candidate in repo_candidates:
        if candidate.auto_clean:
            cleanup.remove_candidate(root, candidate)
    assert log.exists()


def test_clean_json_reports_saved_bytes(tmp_path, capsys):
    root = make_skills(tmp_path)

    code = cleanup.main(["clean", str(root), "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["cleaned"] == payload["summary"]["cleaned"]
    assert payload["saved_bytes"] == payload["summary"]["saved_bytes"]
    assert payload["saved_bytes"] > 0
    assert not (root / "common" / "__pycache__").exists()
