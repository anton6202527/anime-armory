"""combat_rhythm_audit 单测——打斗剪辑节奏曲线（过慢/平淡·advisory-only·不阻断）。

cd skills/n2d-script/scripts && python3 -m pytest test_combat_rhythm_audit.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("combat_rhythm_audit.py")
spec = importlib.util.spec_from_file_location("combat_rhythm_audit", SCRIPT)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


def _clip(template="fight_exchange", duration=12.0, shots=None):
    c = {"id": "Clip_01", "template": template, "duration": duration}
    if shots is not None:
        c["shots"] = [{"t": t} for t in shots]
    return c


# ── 纯函数 ─────────────────────────────────────────────────────────────────────

def test_cut_intervals() -> None:
    assert m.cut_intervals(_clip(shots=["0-3s", "3-6s", "6-9s", "9-12s"]), 12.0) == [3.0, 3.0, 3.0, 3.0]
    assert m.cut_intervals(_clip(), 12.0) == [12.0]            # 单长镜
    assert m.cut_intervals(_clip(), 0) == []                   # 无时长


def test_cov_and_tighten() -> None:
    assert m._cov([3, 3, 3, 3]) == 0.0
    assert m._cov([5, 4, 2, 1]) > 0.15
    assert m._cov([4.0]) == 0.0                                # 单元素证据不足
    assert m.tightens_toward_apex([5, 4, 2, 1]) is True        # 向后收紧
    assert m.tightens_toward_apex([1, 2, 4, 5]) is False       # 越来越慢
    assert m.tightens_toward_apex([3, 3]) is True              # <3 切证据不足→True


# ── audit_clip：R1/R2 ─────────────────────────────────────────────────────────

def test_r1_too_slow_single_long_take() -> None:
    codes = [f["code"] for f in m.audit_clip(_clip(duration=12.0), "Clip_01")]
    assert codes == ["combat_pacing_too_slow"]


def test_r1_respects_region_slow_sec() -> None:
    # 7s 单切：国内默认 5s 阈值 → 过慢；放宽到 8s → 不报。
    assert any(f["code"] == "combat_pacing_too_slow"
               for f in m.audit_clip(_clip(duration=7.0), "Clip_01", slow_sec=5.0))
    assert not m.audit_clip(_clip(duration=7.0), "Clip_01", slow_sec=8.0)


def test_r2_flat_uniform_cuts() -> None:
    codes = [f["code"] for f in m.audit_clip(_clip(shots=["0-3s", "3-6s", "6-9s", "9-12s"]), "Clip_01")]
    assert codes == ["combat_rhythm_flat"]


def test_r2_flat_notes_no_apex_acceleration() -> None:
    # 等长切 + 有 apex 命中拍但未向后收紧 → flat 附注「未向命中拍收紧」。
    clip = _clip(shots=["0-3s", "3-6s", "6-9s", "9-12s"])
    clip["template_contract"] = {"impact_frame": "命中 10s"}
    f = [x for x in m.audit_clip(clip, "Clip_01") if x["code"] == "combat_rhythm_flat"][0]
    assert "未向命中拍收紧" in f["msg"]


def test_good_rhythm_no_findings() -> None:
    # 切点变化大 + 向命中拍收紧 → 既不过慢也不平淡。
    assert m.audit_clip(_clip(shots=["0-5s", "5-9s", "9-11s", "11-12s"]), "Clip_01") == []


def test_non_combat_skipped() -> None:
    assert m.audit_clip(_clip(template="dialogue", duration=12.0), "Clip_01") == []
    assert m.audit_clip(_clip(template="chase", duration=12.0), "Clip_01") == []  # chase 不在 combat 集


def test_all_findings_are_advisory_info() -> None:
    for shots in (None, ["0-3s", "3-6s", "6-9s", "9-12s"]):
        for f in m.audit_clip(_clip(shots=shots, duration=12.0), "Clip_01"):
            assert f["level"] == "info"  # 永不 warn/block


# ── 端到端 ────────────────────────────────────────────────────────────────────

def test_build_audit_end_to_end(tmp_path: Path) -> None:
    sb = {"clips": [
        _clip(duration=12.0),                                       # too_slow
        _clip(shots=["0-3s", "3-6s", "6-9s", "9-12s"]),             # flat
        {"id": "Clip_03", "template": "dialogue", "duration": 6.0}, # 非奇观
    ]}
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    audit = m.build_audit(tmp_path, "第1集")
    assert audit["kind"] == m.AUDIT_KIND
    assert audit["summary"]["combat_clips"] == 2
    assert audit["summary"]["advisory_only"] is True
    assert audit["summary"]["by_code"].get("combat_pacing_too_slow") == 1
    assert "节奏曲线" in m.render_md(audit)


def test_build_audit_missing_storyboard(tmp_path: Path) -> None:
    audit = m.build_audit(tmp_path, "第9集")
    assert audit["findings"] == [] and "error" in audit["summary"]
