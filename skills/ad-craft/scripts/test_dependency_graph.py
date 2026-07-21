import json
from pathlib import Path

import dependency_graph as dg


def _write(root: Path, rel: str, value=b"x"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value), encoding="utf-8")
    elif isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_bytes(value)
    return path


def _project(tmp_path: Path):
    root = tmp_path / "ad"
    _write(root, "需求/brief.json", {"brand": "A"})
    storyboard = {"shots": [
        {"shot_id": "S1", "duration": 1, "assets": {"PROD_A": True}},
        {"shot_id": "S2", "duration": 1, "assets": {"PROD_B": True}},
    ]}
    _write(root, "脚本/storyboard.json", storyboard)
    _write(root, "出图/共享/asset_registry.json", {
        "products": [{"id": "PROD_A", "spec": "red"}, {"id": "PROD_B", "spec": "blue"}]})
    for pos in (1, 2):
        _write(root, f"出图/分镜/prompt/镜头{pos:02d}.md", f"prompt {pos}")
        _write(root, f"出图/分镜/图片/镜头{pos:02d}.png", f"image {pos}".encode())
        _write(root, f"出视频/分镜/prompt/镜头{pos:02d}.md", f"video prompt {pos}")
        _write(root, f"出视频/分镜/视频/镜头{pos:02d}.mp4", f"video {pos}".encode())
    _write(root, "合规/locale_matrix.json", {"default_locale": "zh-CN"})
    plan = {"deliverables": [
        {"deliverable_id": "cut_s1", "kind": "cutdown", "duration": "1s",
         "expected_path": "合成/cut_s1.mp4"},
        {"deliverable_id": "cut_s2", "kind": "cutdown", "duration": "2s",
         "expected_path": "合成/cut_s2.mp4"},
    ]}
    _write(root, "合成/delivery_plan.json", plan)
    _write(root, "合成/cutdown/plan_1s.json", {"kept_shots": ["S1"]})
    _write(root, "合成/cutdown/plan_2s.json", {"kept_shots": ["S2"]})
    _write(root, "合成/cut_s1.mp4", b"cut one")
    _write(root, "合成/cut_s2.mp4", b"cut two")
    return root


def _status(report, node_id):
    return next(row["status"] for row in report["nodes"] if row["node_id"] == node_id)


def test_dependency_graph_invalidates_only_changed_shot(tmp_path):
    root = _project(tmp_path)
    dg.accept_stage(root, "image")
    _write(root, "出图/分镜/prompt/镜头01.md", "changed S1 prompt")
    report = dg.analyze(root)
    assert _status(report, "image:S1") == "stale_input"
    assert _status(report, "image:S2") == "current"


def test_dependency_graph_invalidates_only_deliverable_using_changed_clip(tmp_path):
    root = _project(tmp_path)
    dg.accept_stage(root, "compose")
    _write(root, "出视频/分镜/视频/镜头01.mp4", b"changed video one")
    report = dg.analyze(root)
    assert _status(report, "compose:cut_s1") == "stale_input"
    assert _status(report, "compose:cut_s2") == "current"


def _voice_outputs(root: Path):
    _write(root, "脚本/voiceover.txt", "旁白：整理灵感。")
    _write(root, "配音/时长清单.json", {"lines": [{"idx": 1, "seconds": 1.0}]})
    _write(root, "配音/vo.wav", b"vo")
    _write(root, "配音/voice_qc.json", {"summary": {"block": 0, "warn": 0}})


def test_voicemap_change_invalidates_voice(tmp_path):
    """音色注册表在 voice 血缘内：改 voicemap.json 必须让 voice 节点 stale。"""
    root = _project(tmp_path)
    _voice_outputs(root)
    _write(root, "设定库/voicemap.json", {"旁白": {"voice_key": "VO_A"}})
    dg.accept_stage(root, "voice")
    assert _status(dg.analyze(root), "voice") == "current"
    _write(root, "设定库/voicemap.json", {"旁白": {"voice_key": "VO_B"}})
    assert _status(dg.analyze(root), "voice") == "stale_input"


def test_voicemap_created_after_acceptance_invalidates_voice(tmp_path):
    """voicemap 从缺到有也是输入变化：缺失时以 sentinel 参与哈希，补建后触发 stale。"""
    root = _project(tmp_path)
    _voice_outputs(root)
    dg.accept_stage(root, "voice")
    assert _status(dg.analyze(root), "voice") == "current"
    _write(root, "设定库/voicemap.json", {"旁白": {"voice_key": "VO_A"}})
    assert _status(dg.analyze(root), "voice") == "stale_input"


def test_vo_wav_change_invalidates_compose_default_branch(tmp_path):
    """无 locale matrix 分支：整轨 VO 是 compose 输入，重配音后 compose 必须 stale。"""
    root = _project(tmp_path)
    _write(root, "配音/vo.wav", b"vo v1")
    dg.accept_stage(root, "compose")
    assert _status(dg.analyze(root), "compose:cut_s1") == "current"
    _write(root, "配音/vo.wav", b"vo v2 re-recorded")
    report = dg.analyze(root)
    assert _status(report, "compose:cut_s1") == "stale_input"
    assert _status(report, "compose:cut_s2") == "stale_input"


def test_subtitle_created_after_acceptance_invalidates_compose(tmp_path):
    """发现时不存在的字幕也要无条件登记：后补文件必须触发 compose stale。"""
    root = _project(tmp_path)
    dg.accept_stage(root, "compose")
    assert _status(dg.analyze(root), "compose:cut_s1") == "current"
    _write(root, "脚本/字幕_zh.srt", "1\n00:00:00,000 --> 00:00:01,000\n后补字幕\n")
    assert _status(dg.analyze(root), "compose:cut_s1") == "stale_input"


def test_endcard_removed_after_acceptance_invalidates_compose(tmp_path):
    """从有到缺同样触发 stale：endcard 被删后 compose 不能仍算 current。"""
    root = _project(tmp_path)
    endcard = _write(root, "合成/_work/endcard.png", b"endcard")
    dg.accept_stage(root, "compose")
    assert _status(dg.analyze(root), "compose:cut_s1") == "current"
    endcard.unlink()
    assert _status(dg.analyze(root), "compose:cut_s1") == "stale_input"


def test_locale_change_invalidates_only_mapped_delivery_variant(tmp_path):
    root = _project(tmp_path)
    _write(root, "脚本/voiceover_zh.txt", "中文")
    _write(root, "脚本/字幕_zh.srt", "中文字幕")
    _write(root, "脚本/voiceover_en.txt", "English")
    _write(root, "脚本/字幕_en.srt", "English captions")
    _write(root, "合规/locale_matrix.json", {
        "default_locale": "zh-CN",
        "locales": {
            "zh-CN": {"voiceover_path": "脚本/voiceover_zh.txt", "subtitle_path": "脚本/字幕_zh.srt"},
            "en-US": {"voiceover_path": "脚本/voiceover_en.txt", "subtitle_path": "脚本/字幕_en.srt"},
        },
        "deliverable_locales": {"cut_s1": ["zh-CN"], "cut_s2": ["en-US"]},
    })
    dg.accept_stage(root, "compose")
    _write(root, "脚本/字幕_en.srt", "Changed English captions")
    report = dg.analyze(root)
    assert _status(report, "compose:cut_s1") == "current"
    assert _status(report, "compose:cut_s2") == "stale_input"
