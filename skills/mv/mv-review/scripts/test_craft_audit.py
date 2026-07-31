from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("craft_audit.py")
    spec = importlib.util.spec_from_file_location("mv_craft_audit", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write_plan(root: Path, clips: list[dict]) -> None:
    p = root / "分镜" / "clip_plan.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"kind": "mv_clip_plan", "clips": clips}, ensure_ascii=False), encoding="utf-8")


def _clip(cid, **kw):
    sd = {k: kw.pop(k) for k in ("shot_size", "angle", "camera_movement", "location_id") if k in kw}
    clip = {"clip_id": cid, "shot_design": sd}
    clip.update(kw)
    return clip


def _codes(report: dict) -> set[str]:
    return {f["code"] for f in report["findings"]}


def _f(report: dict, code: str) -> dict:
    return next(f for f in report["findings"] if f["code"] == code)


def test_chorus_no_escalation_flagged_and_escalated_quiet(tmp_path: Path) -> None:
    mod = load_module()
    # 两次副歌完全相同 → 第 2 次无升级 warn
    same = dict(section="chorus", shot_size="中景", camera_movement="推", location_id="舞台")
    clips = [
        _clip("Clip_01", section="verse", location_id="街道", camera_movement="跟拍"),
        _clip("Clip_02", **same), _clip("Clip_03", **same),
        _clip("Clip_04", section="verse", location_id="街道", camera_movement="跟拍"),
        _clip("Clip_05", **same), _clip("Clip_06", **same),
    ]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    assert "chorus_no_escalation" in _codes(report)
    # 第 2 次副歌换了场景+提了能量 → 安静
    clips[4] = _clip("Clip_05", section="chorus", shot_size="特写", camera_movement="环绕甩镜", location_id="天台")
    clips[5] = _clip("Clip_06", section="chorus", shot_size="全景", camera_movement="环绕", location_id="天台")
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    assert "chorus_no_escalation" not in _codes(report)


def test_dynamics_contrast_warn_and_ceiling_info(tmp_path: Path) -> None:
    mod = load_module()
    # 主歌全高动态、副歌反而平 → no_dynamics_contrast warn
    clips = [
        _clip("Clip_01", section="verse", camera_movement="环绕甩镜"),
        _clip("Clip_02", section="verse", camera_movement="穿越冲"),
        _clip("Clip_03", section="chorus", camera_movement="固定"),
        _clip("Clip_04", section="chorus", camera_movement="缓推"),
    ]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    assert "no_dynamics_contrast" in _codes(report)
    # 主歌收着、副歌放 → 安静
    clips2 = [
        _clip("Clip_01", section="verse", camera_movement="跟拍"),
        _clip("Clip_02", section="verse", camera_movement="缓推"),
        _clip("Clip_03", section="chorus", camera_movement="环绕甩镜"),
        _clip("Clip_04", section="chorus", camera_movement="冲击变焦"),
    ]
    write_plan(tmp_path, clips2)
    report = mod.build_report(str(tmp_path))
    assert "no_dynamics_contrast" not in _codes(report)


def test_hook_visibility(tmp_path: Path) -> None:
    mod = load_module()
    # 有表演线但副歌没有上脸演唱近景 → warn
    clips = [
        _clip("Clip_01", section="verse", action_family="performance_vocal", shot_size="全景"),
        _clip("Clip_02", section="chorus", shot_size="全景", camera_movement="环绕"),
    ]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    assert "hook_not_sung_on_camera" in _codes(report)
    # 副歌加一个演唱特写 → 安静
    clips.append(_clip("Clip_03", section="chorus", action_family="performance_vocal", shot_size="特写"))
    write_plan(tmp_path, clips)
    assert "hook_not_sung_on_camera" not in _codes(mod.build_report(str(tmp_path)))
    # 全曲无表演线 → info 自检
    clips3 = [_clip("Clip_01", section="verse"), _clip("Clip_02", section="chorus")]
    write_plan(tmp_path, clips3)
    assert "no_performance_line" in _codes(mod.build_report(str(tmp_path)))


def test_cold_open_too_long(tmp_path: Path) -> None:
    mod = load_module()
    clips = [
        _clip("Clip_01", section="intro", duration=5.0, location_id="A"),
        _clip("Clip_02", section="intro", duration=5.0, location_id="A"),
        _clip("Clip_03", section="verse", duration=4.0, location_id="A"),
        _clip("Clip_04", section="chorus", duration=4.0, shot_size="特写"),
    ]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    hit = _f(report, "cold_open_too_long")
    assert hit["severity"] == "warn" and "Clip_01" in hit["clips"]
    # 开场镜就是近景钩 → 安静
    clips[0] = _clip("Clip_01", section="intro", duration=5.0, shot_size="大特写")
    write_plan(tmp_path, clips)
    assert "cold_open_too_long" not in _codes(mod.build_report(str(tmp_path)))


def test_key_clip_coverage_info_then_warn(tmp_path: Path) -> None:
    mod = load_module()
    # 全 plan 无候选字段 → 单条 info 建议
    clips = [_clip("Clip_01", section="chorus", shot_size="特写")]
    write_plan(tmp_path, clips)
    assert "key_clip_coverage_unplanned" in _codes(mod.build_report(str(tmp_path)))
    # 有字段但 key 镜 <2 → warn；≥2 → 安静
    clips = [_clip("Clip_01", section="chorus", candidate_count=1),
             _clip("Clip_02", section="chorus", candidate_count=3)]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    hit = _f(report, "key_clip_single_candidate")
    assert hit["clips"] == ["Clip_01"]


def test_bridge_no_look_shift_info(tmp_path: Path) -> None:
    mod = load_module()
    clips = [
        _clip("Clip_01", section="verse", location_id="街道", camera_movement="跟拍"),
        _clip("Clip_02", section="bridge", location_id="街道", camera_movement="跟拍"),
    ]
    write_plan(tmp_path, clips)
    assert "bridge_no_look_shift" in _codes(mod.build_report(str(tmp_path)))
    # bridge 换了场景 → 安静
    clips[1] = _clip("Clip_02", section="bridge", location_id="海边", camera_movement="跟拍")
    write_plan(tmp_path, clips)
    assert "bridge_no_look_shift" not in _codes(mod.build_report(str(tmp_path)))


def test_lyric_visual_echo_zero_info(tmp_path: Path) -> None:
    mod = load_module()
    clips = [_clip("Clip_01", section="verse", desc="城市夜景空镜", location_id="A")]
    write_plan(tmp_path, clips)
    lyr = tmp_path / "词" / "lyrics.md"
    lyr.parent.mkdir(parents=True, exist_ok=True)
    lyr.write_text("[chorus]\n蝴蝶飞过沧海月光坠落荒原星辰燃烧成灰烬\n", encoding="utf-8")
    assert "lyric_visual_echo_zero" in _codes(mod.build_report(str(tmp_path)))
    # 画面里落了歌词意象 → 安静
    clips[0]["desc"] = "月光下蝴蝶飞过她的肩"
    write_plan(tmp_path, clips)
    assert "lyric_visual_echo_zero" not in _codes(mod.build_report(str(tmp_path)))


def test_write_exit_zero_never_block(tmp_path: Path) -> None:
    mod = load_module()
    write_plan(tmp_path, [_clip("Clip_01", section="chorus")])
    rc = mod.main([str(tmp_path), "--write"])
    assert rc == 0
    payload = json.loads((tmp_path / "生产数据" / "craft_audit" / "craft_audit.json").read_text(encoding="utf-8"))
    assert payload["kind"] == "mv_craft_audit"
    assert payload["summary"]["block"] == 0
