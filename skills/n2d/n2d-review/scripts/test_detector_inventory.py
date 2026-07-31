#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""detector_inventory 单测。 cd skills/n2d/n2d-review/scripts && python3 -m pytest test_detector_inventory.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import detector_inventory as di  # noqa: E402


def _mk(d, name, body="x = 1\n"):
    with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
        fh.write(body)


def _fixture(tmp_path):
    d = str(tmp_path)
    # consumers
    _mk(d, "consistency_audit.py", "import face_consistency\nimport sub_detector\n")
    _mk(d, "gate.py", "from style_consistency import run\n")
    _mk(d, "consistency_ledger.py", "import style_consistency\n")
    # detectors
    _mk(d, "face_consistency.py")            # wired only
    _mk(d, "style_consistency.py")           # gate + ledger
    _mk(d, "object_state_continuity.py", "import state_pixel_sub\n")  # peer-consumes a sub
    _mk(d, "state_pixel_sub.py")             # 名字不带后缀 → 不在 EXTRA → 不计入；改用真后缀
    _mk(d, "lonely_consistency.py")          # orphan：无任何消费者
    _mk(d, "sub_detector.py")                # 进编排（被 audit import），但名字无后缀→不计入
    return d


def test_discover_excludes_infra_and_tests(tmp_path):
    d = str(tmp_path)
    _mk(d, "consistency_audit.py")           # infra
    _mk(d, "test_face_consistency.py")       # test
    _mk(d, "face_consistency.py")
    _mk(d, "quality_check.py")               # EXTRA
    stems = di.discover_detectors(d)
    assert "face_consistency" in stems
    assert "quality_check" in stems
    assert "consistency_audit" not in stems
    assert "test_face_consistency" not in stems


def test_classification_wired_gate_ledger_orphan(tmp_path):
    d = str(tmp_path)
    _mk(d, "consistency_audit.py", "import face_consistency\n")
    _mk(d, "gate.py", "import style_consistency\n")
    _mk(d, "consistency_ledger.py", "import style_consistency\n")
    _mk(d, "face_consistency.py")
    _mk(d, "style_consistency.py")
    _mk(d, "lonely_consistency.py")
    inv = di.build_inventory(d)
    rows = {r["detector"]: r for r in inv["rows"]}
    assert rows["face_consistency"]["wired"] and not rows["face_consistency"]["orphan"]
    assert rows["style_consistency"]["gate"] and rows["style_consistency"]["ledger"]
    assert rows["lonely_consistency"]["orphan"]
    assert inv["orphans"] == ["lonely_consistency"]


def test_peer_consumption_is_not_orphan(tmp_path):
    # 子检测器被另一个 detector 调用 → 不算孤儿（治传递消费假阳性，state_pixel_contract 真实案例）
    d = str(tmp_path)
    _mk(d, "consistency_audit.py", "import state_continuity\n")
    _mk(d, "gate.py", "")
    _mk(d, "consistency_ledger.py", "")
    _mk(d, "state_continuity.py", "import state_pixel_contract\n")
    _mk(d, "state_pixel_contract.py")  # 在 EXTRA 集里
    inv = di.build_inventory(d)
    rows = {r["detector"]: r for r in inv["rows"]}
    assert rows["state_pixel_contract"]["peer"] is True
    assert rows["state_pixel_contract"]["orphan"] is False
    assert inv["orphans"] == []


def test_advisory_and_disabled_are_governed_not_orphan(tmp_path):
    d = str(tmp_path)
    _mk(d, "consistency_audit.py", "")
    _mk(d, "gate.py", "")
    _mk(d, "consistency_ledger.py", "")
    _mk(d, "soft_consistency.py", "# advisory only; never block\n")
    _mk(d, "old_consistency.py", "N2D_DETECTOR_DISABLED = True\n")

    inv = di.build_inventory(d)
    rows = {r["detector"]: r for r in inv["rows"]}

    assert rows["soft_consistency"]["advisory"] is True
    assert rows["soft_consistency"]["governance_path"] == "advisory"
    assert rows["soft_consistency"]["orphan"] is False
    assert rows["old_consistency"]["disabled"] is True
    assert rows["old_consistency"]["governance_path"] == "disabled"
    assert rows["old_consistency"]["orphan"] is False
    assert inv["orphans"] == []


def test_word_boundary_no_substring_false_positive(tmp_path):
    # "face_consistency" 不应被 "subface_consistency_extra" 这类子串误判命中
    d = str(tmp_path)
    _mk(d, "consistency_audit.py", "import subface_consistency\n")
    _mk(d, "gate.py", "")
    _mk(d, "consistency_ledger.py", "")
    _mk(d, "face_consistency.py")
    _mk(d, "subface_consistency.py")
    inv = di.build_inventory(d)
    rows = {r["detector"]: r for r in inv["rows"]}
    assert rows["face_consistency"]["orphan"] is True   # 只 subface 被 import，face 仍是孤儿
    assert rows["subface_consistency"]["wired"] is True


def test_strict_exit_code(tmp_path):
    d = str(tmp_path)
    _mk(d, "consistency_audit.py", "")
    _mk(d, "gate.py", "")
    _mk(d, "consistency_ledger.py", "")
    _mk(d, "lonely_consistency.py")
    assert di.main(["--scripts-dir", d, "--strict"]) == 1
    assert di.main(["--scripts-dir", d]) == 0


def test_real_repo_has_no_orphans():
    # 锁住治理结论：真实仓库的 detector 套件应保持 0 孤儿（每个维度都被消费）。
    inv = di.build_inventory(di.HERE)
    assert inv["counts"]["orphan"] == 0, f"出现孤儿 detector: {inv['orphans']}"
    assert "dashboard" in inv["counts"]
    assert "advisory" in inv["counts"]
    assert "disabled" in inv["counts"]
    assert inv["total"] > 20  # sanity：确实扫到了完整套件


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
