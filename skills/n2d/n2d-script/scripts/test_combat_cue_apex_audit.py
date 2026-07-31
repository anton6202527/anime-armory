"""combat_cue_apex_audit 单测——把"剪辑峰值必须对齐命中/apex"散文规则兑现成对账。

cd skills/n2d/n2d-script/scripts && python3 -m pytest test_combat_cue_apex_audit.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("combat_cue_apex_audit.py")
spec = importlib.util.spec_from_file_location("combat_cue_apex_audit", SCRIPT)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


def _fight(impact="命中 1.8s 狰狞峰", anchors=None, duration=10.0):
    clip = {
        "id": "Clip_01", "template": "fight_exchange", "duration": duration,
        "template_contract": {"impact_frame": impact, "beats": ["起势", "劈砍", "命中"]},
    }
    if anchors is not None:
        clip["continuity"] = {"anchors": anchors}
    return clip


# ── 纯函数 ─────────────────────────────────────────────────────────────────────

def test_parse_when_seconds() -> None:
    assert m.parse_when_seconds("命中 1.8s 狰狞峰") == 1.8
    assert m.parse_when_seconds("impact 2s") == 2.0
    assert m.parse_when_seconds("impact") is None
    assert m.parse_when_seconds("命中（无秒）") is None
    assert m.parse_when_seconds(None) is None


def test_keyframe_anchor_secs() -> None:
    clip = {"continuity": {"anchors": [
        {"use": "keyframe", "at_sec": 1.8}, {"use": "split", "at_sec": 5.0},
        {"use": "keyframe", "at_sec": 7.0},
    ]}}
    assert m.keyframe_anchor_secs(clip) == [1.8, 7.0]
    assert m.keyframe_anchor_secs({}) == []


# ── audit_clip：C1/C2/C3 ──────────────────────────────────────────────────────

def test_non_impact_spectacle_skipped() -> None:
    assert m.audit_clip({"template": "dialogue", "duration": 6.0}, "Clip_X") == []
    # chase 有 cue 但无离散命中帧 → 不在本闸
    assert m.audit_clip({"template": "chase", "duration": 8.0,
                         "template_contract": {"beats": ["a", "b"]}}, "Clip_X") == []


def test_c1_untimestamped_impact_frame() -> None:
    codes = [f["code"] for f in m.audit_clip(_fight(impact="命中（无秒数）"), "Clip_01")]
    assert codes == ["combat_apex_untimestamped"]


def test_c2_cue_pinned_but_no_keyframe_anchor() -> None:
    # impact 带秒，但 storyboard 无 keyframe 锚（anchor_planner 未注回）
    codes = [f["code"] for f in m.audit_clip(_fight(anchors=None), "Clip_01")]
    assert codes == ["combat_cue_apex_no_keyframe"]
    # 有锚但 use=split（非 keyframe）也算无 keyframe 落点
    codes2 = [f["code"] for f in m.audit_clip(
        _fight(anchors=[{"use": "split", "at_sec": 1.8}]), "Clip_01")]
    assert "combat_cue_apex_no_keyframe" in codes2


def test_aligned_no_findings() -> None:
    clip = _fight(anchors=[{"use": "keyframe", "at_sec": 1.8}, {"use": "split", "at_sec": 5.0}])
    assert m.audit_clip(clip, "Clip_01") == []


def test_c3_apex_keyframe_without_edit_cue() -> None:
    clip = _fight(anchors=[{"use": "keyframe", "at_sec": 1.8}, {"use": "keyframe", "at_sec": 7.0}])
    findings = m.audit_clip(clip, "Clip_01")
    codes = [f["code"] for f in findings]
    assert codes == ["combat_apex_no_edit_cue"]
    assert findings[0]["at_sec"] == 7.0 and findings[0]["level"] == "info"


def test_magic_burst_collision_frame() -> None:
    clip = {
        "id": "Clip_02", "template": "magic_burst", "duration": 8.0,
        "template_contract": {"collision_or_apex_frame": "峰值 3.2s 白闪", "beats": ["蓄", "放", "峰"]},
        "continuity": {"anchors": [{"use": "keyframe", "at_sec": 3.2}]},
    }
    assert m.audit_clip(clip, "Clip_02") == []  # 对齐


# ── 端到端 build_audit ────────────────────────────────────────────────────────

def test_build_audit_end_to_end(tmp_path: Path) -> None:
    sb = {"clips": [
        _fight(impact="命中（无秒）"),                                  # C1
        _fight(anchors=[{"use": "keyframe", "at_sec": 1.8}]),           # 对齐
        {"id": "Clip_03", "template": "dialogue", "duration": 5.0},     # 非奇观
    ]}
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")
    audit = m.build_audit(tmp_path, "第1集")
    assert audit["kind"] == m.AUDIT_KIND
    assert audit["summary"]["combat_clips"] == 2
    assert audit["summary"]["by_code"].get("combat_apex_untimestamped") == 1
    # render 不崩
    assert "对齐审计" in m.render_md(audit)


def test_build_audit_missing_storyboard(tmp_path: Path) -> None:
    audit = m.build_audit(tmp_path, "第9集")
    assert audit["findings"] == [] and "error" in audit["summary"]
    assert "缺少或损坏" in m.render_md(audit)
