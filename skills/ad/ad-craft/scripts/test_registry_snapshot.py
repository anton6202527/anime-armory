"""定妆库母本↔出图快照陈旧对账（gate.registry_snapshot_findings）。

母本 设定库/asset_registry.json 改了、出图/共享/ 快照没刷新时，prompt 与 product_qc
会照过期 registry 跑——这套系统本身是用来防漂移的，却会成为漂移源。
"""
import json
import os
import time
from pathlib import Path

import gate


def _write(root: Path, rel: str, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _stamp(path: Path, seconds_ago: float):
    when = time.time() - seconds_ago
    os.utime(path, (when, when))


def _registry(name="ACME"):
    return {"brand": {"id": "BRAND_01", "name": name, "primary_hex": "#112233"}}


def _codes(findings):
    return {f["code"] for f in findings}


def test_stale_snapshot_blocks(tmp_path):
    master = _write(tmp_path, "设定库/asset_registry.json", _registry("ACME 改过"))
    snapshot = _write(tmp_path, "出图/共享/asset_registry.json", _registry())
    _stamp(snapshot, 600)  # 快照早于母本
    _stamp(master, 60)

    findings = gate.registry_snapshot_findings(str(tmp_path))

    assert _codes(findings) == {"asset_registry_snapshot_stale"}
    assert findings[0]["severity"] == "block"


def test_fresh_snapshot_passes(tmp_path):
    master = _write(tmp_path, "设定库/asset_registry.json", _registry())
    snapshot = _write(tmp_path, "出图/共享/asset_registry.json", _registry())
    _stamp(master, 600)
    _stamp(snapshot, 60)  # 快照晚于母本 = 已刷新

    assert gate.registry_snapshot_findings(str(tmp_path)) == []


def test_missing_either_side_is_silent(tmp_path):
    """快照未生成（还没跑 plan_prompts）不是陈旧；缺料由既有 registry 检查管，此处不重复报。"""
    assert gate.registry_snapshot_findings(str(tmp_path)) == []

    _write(tmp_path, "设定库/asset_registry.json", _registry())
    assert gate.registry_snapshot_findings(str(tmp_path)) == []


def test_wired_into_every_gate_stage(tmp_path):
    """母本/快照对账对 image/video/compose 都成立——出图前就该拦，别等花完钱。"""
    master = _write(tmp_path, "设定库/asset_registry.json", _registry("ACME 改过"))
    snapshot = _write(tmp_path, "出图/共享/asset_registry.json", _registry())
    _stamp(snapshot, 600)
    _stamp(master, 60)

    for stage in gate.STAGES:
        payload = gate.run_gate(str(tmp_path), stage)
        assert "asset_registry_snapshot_stale" in _codes(payload["findings"]), stage
