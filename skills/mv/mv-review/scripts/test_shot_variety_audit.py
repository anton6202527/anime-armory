from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("shot_variety_audit.py")
    spec = importlib.util.spec_from_file_location("mv_shot_variety_audit", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write_plan(root: Path, clips: list[dict]) -> None:
    p = root / "分镜" / "clip_plan.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"kind": "mv_clip_plan", "clips": clips}, ensure_ascii=False), encoding="utf-8")


def _codes(report: dict) -> set[str]:
    return {f["code"] for f in report["findings"]}


def _clip(cid, **kw):
    sd = {k: kw.pop(k) for k in ("shot_size", "angle", "camera_movement", "lens_feel",
                                 "location_id", "setup_group", "location_name") if k in kw}
    clip = {"clip_id": cid, "shot_design": sd}
    clip.update(kw)
    return clip


def test_repeated_composition_flagged_and_chorus_hook_downgraded(tmp_path: Path) -> None:
    mod = load_module()
    # verse 里两个完全相同构图 → warn
    clips = [
        _clip("Clip_01", section="verse", shot_size="中景", angle="平视", camera_movement="推", location_id="街道"),
        _clip("Clip_02", section="verse", shot_size="中景", angle="平视", camera_movement="推", location_id="街道"),
    ]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    assert "repeated_composition_plan" in _codes(report)
    rc = [f for f in report["findings"] if f["code"] == "repeated_composition_plan"][0]
    assert rc["severity"] == "warn"

    # 同一副歌段的重复 hook → 降 info（有意母题）
    clips2 = [
        _clip("Clip_10", section="chorus", beat_role="key", shot_size="特写", angle="平视", camera_movement="环绕", location_id="舞台"),
        _clip("Clip_11", section="chorus", beat_role="key", shot_size="特写", angle="平视", camera_movement="环绕", location_id="舞台"),
    ]
    write_plan(tmp_path, clips2)
    report2 = mod.build_report(str(tmp_path))
    rc2 = [f for f in report2["findings"] if f["code"] == "repeated_composition_plan"][0]
    assert rc2["severity"] == "info"


def test_lens_variety_low_on_long_same_location_run(tmp_path: Path) -> None:
    mod = load_module()
    # 6 个连续同场景 clip，只有 2 种景别 → lens_variety_low
    clips = [_clip(f"Clip_{i:02d}", section="verse", location_id="房间",
                   shot_size="中景" if i % 2 else "全景", angle="平视",
                   camera_movement=f"移动{i}") for i in range(6)]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    assert "lens_variety_low" in _codes(report)


def test_static_key_clip_flagged_but_hold_intent_exempt(tmp_path: Path) -> None:
    mod = load_module()
    clips = [_clip("Clip_01", section="chorus", beat_role="key",
                   shot_size="全景", angle="平视", camera_movement="固定锁定")]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    assert "static_key_clip" in _codes(report)

    # 明确留白意图 → 豁免
    clips2 = [_clip("Clip_01", section="chorus", beat_role="key",
                    shot_size="全景", angle="平视", camera_movement="固定", visual_motif="留白空镜")]
    write_plan(tmp_path, clips2)
    report2 = mod.build_report(str(tmp_path))
    assert "static_key_clip" not in _codes(report2)


def test_location_monotony_and_run(tmp_path: Path) -> None:
    mod = load_module()
    # 8 个全在同一场景 + 1 个别处 → 覆盖 88% 触发 monotony；连续 8 触发 run_long
    clips = [_clip(f"Clip_{i:02d}", section="verse", location_id="天台",
                   shot_size="中景" if i % 3 == 0 else ("全景" if i % 3 == 1 else "特写"),
                   angle=f"a{i}", camera_movement=f"m{i}") for i in range(8)]
    clips.append(_clip("Clip_08", section="verse", location_id="海边",
                       shot_size="远景", angle="俯", camera_movement="推"))
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    codes = _codes(report)
    assert "location_monotony" in codes
    assert "location_run_long" in codes


def test_reference_gap_on_closeup_without_reference(tmp_path: Path) -> None:
    mod = load_module()
    clips = [
        _clip("Clip_01", section="verse", shot_size="大特写", angle="平视",
              camera_movement="推", location_id="房间", reference_inputs=[]),
        _clip("Clip_02", section="verse", shot_size="中景", angle="平视",
              camera_movement="移", location_id="房间",
              reference_inputs=[{"path": "出图/共享/图片/定妆_主角.png", "use": "identity"}]),
    ]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    gap = [f for f in report["findings"] if f["code"] == "reference_gap"]
    assert gap and "Clip_01" in gap[0]["clips"] and "Clip_02" not in gap[0]["clips"]


def test_report_only_never_blocks_and_missing_plan_noop(tmp_path: Path) -> None:
    mod = load_module()
    # 缺 clip_plan → 记 note，无 finding，summary.block==0
    report = mod.build_report(str(tmp_path))
    assert report["summary"]["block"] == 0
    assert report["findings"] == []
    assert any("clip_plan" in n for n in report["notes"])
    assert mod.main([str(tmp_path)]) == 0

    # 有 warn 也永不 block，退出码仍 0
    write_plan(tmp_path, [
        _clip("Clip_01", section="verse", shot_size="中景", angle="平视", camera_movement="推", location_id="街道"),
        _clip("Clip_02", section="verse", shot_size="中景", angle="平视", camera_movement="推", location_id="街道"),
    ])
    report2 = mod.build_report(str(tmp_path))
    assert report2["summary"]["block"] == 0
    assert report2["summary"]["warn"] >= 1
    assert mod.main([str(tmp_path), "--write", "--json"]) == 0
    assert (tmp_path / "生产数据" / "shot_variety" / "shot_variety.json").exists()


def test_kind_and_schema(tmp_path: Path) -> None:
    mod = load_module()
    write_plan(tmp_path, [_clip("Clip_01", section="verse", shot_size="中景",
                                angle="平视", camera_movement="推", location_id="街道")])
    report = mod.build_report(str(tmp_path))
    assert report["kind"] == "mv_shot_variety_audit"
    assert "inputs_sha256" in report and "分镜/clip_plan.json" in report["inputs_sha256"]
    assert set(report["summary"]) >= {"block", "warn", "info", "clips_checked", "verdict"}
