from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("visual_checks.py")
spec = importlib.util.spec_from_file_location("n2d_score_visual_checks", SCRIPT)
visual = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(visual)


def write_storyboard(root: Path) -> None:
    clips = [{"id": f"c{i}", "duration": 10, "continuity": {}} for i in range(1, 5)]
    path = root / "脚本" / "第1集" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"episode": 1, "total_duration": 40, "clips": clips}, ensure_ascii=False), encoding="utf-8")


def write_manifest(root: Path) -> None:
    rows = [
        {"文本": "开场", "钩子": "hook"},
        {"文本": "铺垫", "钩子": ""},
        {"文本": "继续铺垫", "钩子": ""},
        {"文本": "仍然铺垫", "钩子": ""},
    ]
    path = root / "出视频" / "第1集" / "配音" / "时长清单.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def test_manifest_prefers_compose_dir(tmp_path: Path) -> None:
    old = tmp_path / "出视频" / "第1集" / "配音" / "时长清单.json"
    new = tmp_path / "合成" / "第1集" / "配音" / "时长清单.json"
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_text(json.dumps([{"文本": "旧", "钩子": ""}], ensure_ascii=False), encoding="utf-8")
    new.write_text(json.dumps([{"文本": "新", "钩子": "hook"}], ensure_ascii=False), encoding="utf-8")

    assert visual.load_manifest(str(tmp_path), "第1集")[0]["文本"] == "新"


def test_voice_candidates_prefer_compose_dir(tmp_path: Path) -> None:
    old = tmp_path / "出视频" / "第1集" / "配音" / "voice_zh.wav"
    new = tmp_path / "合成" / "第1集" / "配音" / "voice_zh.wav"
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_bytes(b"old")
    new.write_bytes(b"new")

    candidates = visual.voice_candidates(str(tmp_path), "第1集")

    assert candidates[0] == str(new)
    assert candidates[1] == str(old)


def test_final_rhythm_density_uses_storyboard_when_final_missing(tmp_path: Path) -> None:
    write_storyboard(tmp_path)
    write_manifest(tmp_path)

    sec = visual.check_final_rhythm_density(str(tmp_path), "第1集")

    assert sec["metrics"]["shot_density_per_min"] == 6.0
    assert sec["blocks"] == 1
    assert "平均钩子间隔" in " ".join(sec["evidence"])


def write_pacing_report(root: Path) -> None:
    """模拟 pacing_retention.py 写的 storyboard 态 advisory（advisory·blocks 恒 0）。"""
    path = root / "生产数据" / "pacing_retention_第1集.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "blocks": 0, "warnings": 2, "infos": 0,
        "evidence": ["C1: 首屏钩疑仅靠声音/旁白，静音掉钩", "节奏/留存 advisory 分 62 偏低"],
        "metrics": {"available": True, "verdict": "warn", "score": 62.0,
                    "hook_score": 55.0, "pacing_score": 70.0, "retention_score": 60.0,
                    "risk_shot_count": 1},
    }, ensure_ascii=False), encoding="utf-8")


def test_final_rhythm_density_folds_pacing_advisory(tmp_path: Path) -> None:
    # ① score 接 pacing_retention：成片侧硬闸保留 + storyboard 态 advisory 折入
    write_storyboard(tmp_path)
    write_manifest(tmp_path)
    write_pacing_report(tmp_path)

    sec = visual.check_final_rhythm_density(str(tmp_path), "第1集")

    assert sec["blocks"] == 1                                  # 成片侧 hook_interval>30s 硬闸仍在
    assert sec["warnings"] >= 2                                # 叠加了 pacing advisory 的 2 个 warn
    assert sec["metrics"]["pacing_advisory"]["verdict"] == "warn"
    assert sec["metrics"]["shot_density_per_min"] == 6.0       # 成片侧 metrics 未被覆盖
    assert any("pacing_retention" in e for e in sec["evidence"])


def test_final_rhythm_density_surfaces_pacing_when_no_final(tmp_path: Path) -> None:
    # 成片/storyboard 都没有，但 storyboard 态 advisory 在 → 不整段 skip，浮现 advisory
    write_pacing_report(tmp_path)

    sec = visual.check_final_rhythm_density(str(tmp_path), "第1集")

    assert sec["available"] is True                            # 没被 mark_skip 吞掉
    assert sec["warnings"] >= 2
    assert sec["metrics"]["final_density_available"] is False
    assert sec["blocks"] == 0                                  # advisory 永不硬阻断


def test_final_rhythm_density_pacing_block_downgraded_to_warn(tmp_path: Path) -> None:
    # 防越权：advisory 报告即便误写了 block，折入时也降为 warn，不污染成片硬闸口径
    path = tmp_path / "生产数据" / "pacing_retention_第1集.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"blocks": 1, "warnings": 0, "infos": 0,
                                "evidence": ["越权 block"], "metrics": {"verdict": "warn"}},
                               ensure_ascii=False), encoding="utf-8")

    sec = visual.check_final_rhythm_density(str(tmp_path), "第1集")

    assert sec["blocks"] == 0
    assert sec["warnings"] == 1
