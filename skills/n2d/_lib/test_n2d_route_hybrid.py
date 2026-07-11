from __future__ import annotations

import json
from pathlib import Path

import n2d_route as route


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _ready_row() -> tuple[list[str], dict[str, str]]:
    header = [
        "集", "剧本改编", "bgm", "封面", "配音", "分镜设计", "素材清单",
        "字幕中", "字幕英", "出图prompt", "出图", "视频prompt", "视频", "成片", "验收",
    ]
    row = {key: "✅" for key in header}
    row.update({"集": "第1集", "_ep": "第1集", "成片": "⬜", "验收": "⬜"})
    return header, row


def test_hybrid_route_returns_to_post_lipsync_before_compose(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "- 制作模式: 混合自动路由\n- 合成阶段: 启用\n", encoding="utf-8",
    )
    _write_json(tmp_path / "合成" / "第1集" / "配音" / "时长清单.json", [
        {"idx": 0, "时长": 1.0, "占位": False, "voice_key": "locked:hero"},
    ])
    _write_json(tmp_path / "出视频" / "第1集" / "prompt" / "video_model_routes.json", {
        "routes": [{
            "clip_id": "Clip_01",
            "audio_strategy": "base_video_then_post_lipsync",
            "post_lipsync_required": True,
            "post_lipsync_output": "出视频/第1集/视频_lipsync/Clip_01_lipsync.mp4",
        }],
    })
    header, row = _ready_row()

    result = route.stage_of(str(tmp_path), row, header)

    assert result["skill"] == "n2d-video"
    assert result["label"] == "完成后期口型/表演 pass"
    assert "Clip_01" in str(result["note"])


def test_hybrid_route_reaches_compose_after_post_lipsync_exists(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "- 制作模式: 混合自动路由\n- 合成阶段: 启用\n", encoding="utf-8",
    )
    _write_json(tmp_path / "合成" / "第1集" / "配音" / "时长清单.json", [
        {"idx": 0, "时长": 1.0, "占位": False, "voice_key": "locked:hero"},
    ])
    _write_json(tmp_path / "出视频" / "第1集" / "prompt" / "video_model_routes.json", {
        "routes": [{
            "clip_id": "Clip_01",
            "audio_strategy": "base_video_then_post_lipsync",
            "post_lipsync_required": True,
        }],
    })
    final = tmp_path / "出视频" / "第1集" / "视频_lipsync" / "Clip_01_lipsync.mp4"
    final.parent.mkdir(parents=True)
    final.write_bytes(b"post-lipsync")
    header, row = _ready_row()

    result = route.stage_of(str(tmp_path), row, header)

    assert result["skill"] == "n2d-compose"
