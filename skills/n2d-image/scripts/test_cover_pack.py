#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cover_pack


def _project(root: Path, **meta_fields):
    meta = {"schema_version": 1, "kind": "n2d_project", "line": "n2d", "title": "斩妖记"}
    meta.update(meta_fields)
    (root / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def _identity_registry(root: Path, *, ready: bool):
    shared = root / "出图" / "共享"
    imgdir = shared / "图片"
    imgdir.mkdir(parents=True, exist_ok=True)
    anchor_rel = "出图/共享/图片/定妆_CHAR_01__常态.png"
    if ready:
        (root / anchor_rel).write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    reg = {
        "kind": "n2d_identity_registry",
        "characters": [
            {
                "id": "CHAR_01",
                "name": "姜月初",
                "tier": "核心长线",
                "library_tier": "core_full",
                "planned_episode_count": 10,
                "forms": [
                    {
                        "form": "常态",
                        "anchor_phrase": "十八岁冷白清丽脸·高马尾·玄黑劲装。",
                        "drift_forbidden": ["不要换脸"],
                        "reference_group": {
                            "front": {
                                "path": anchor_rel,
                                "status": "ready" if ready else "planned",
                                "sha256": "abc123",
                            }
                        },
                    }
                ],
            }
        ],
    }
    (shared / "identity_registry.json").write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")


def test_build_pack_binds_identity_and_model(tmp_path):
    _project(tmp_path, synopsis="穿越少女斩妖逆袭。")
    _identity_registry(tmp_path, ready=True)
    pack = cover_pack.build_pack(tmp_path)
    assert pack["kind"] == cover_pack.KIND
    assert pack["orientation"] == "portrait"
    assert pack["aspect_ratio"] == "9:16"
    # C5: 生图模型必须是具体模型名，不能是空/渠道壳。
    assert pack["生图模型"]
    assert "渠道" not in pack["生图模型"] and "Codex" != pack["生图模型"]
    binding = pack["identity_bindings"][0]
    assert binding["carries_identity"] == "CHAR_01/常态"
    assert binding["face_anchor_ready"] is True
    assert pack["render_blocking"] == []
    assert pack["cover_meta_field"] is None
    assert pack["output_path"] == "出图/封面/cover.png"


def test_build_pack_flags_unready_anchor_without_blocking(tmp_path):
    _project(tmp_path)
    _identity_registry(tmp_path, ready=False)
    pack = cover_pack.build_pack(tmp_path)
    binding = pack["identity_bindings"][0]
    assert binding["face_anchor_ready"] is False
    assert "missing_ready_face_anchor" in pack["render_blocking"]
    # 仍然产出完整 job 包，不硬阻断。
    assert pack["prompt"]["zh"]


def test_build_pack_without_characters_degrades(tmp_path):
    _project(tmp_path, synopsis="纯风景悬疑短剧。")
    pack = cover_pack.build_pack(tmp_path)
    assert pack["identity_bindings"] == []
    assert pack["render_blocking"] == []
    assert pack["prompt"]["zh"]


def test_write_outputs_and_no_png_generated(tmp_path):
    _project(tmp_path, synopsis="穿越少女斩妖逆袭。")
    _identity_registry(tmp_path, ready=True)
    pack = cover_pack.build_pack(tmp_path)
    jp, mp = cover_pack.write_outputs(tmp_path, pack)
    assert jp.is_file() and mp.is_file()
    # 无成本 writer：不生成 cover.png。
    assert not (tmp_path / "出图" / "封面" / "cover.png").exists()
    assert pack["compliance"]["degraded_no_backend_call"] is True


def test_backfill_cli_after_render(tmp_path):
    _project(tmp_path, synopsis="穿越少女斩妖逆袭。", cover=None)
    png = tmp_path / "出图" / "封面" / "cover.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    rc = cover_pack.main([str(tmp_path), "--backfill-cover"])
    assert rc == 0
    meta = json.loads((tmp_path / "_meta.json").read_text(encoding="utf-8"))
    assert meta["cover"] == "出图/封面/cover.png"


def test_cover_strategy_ref_reused(tmp_path):
    _project(tmp_path)
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "封面.md").write_text("# 封面策略", encoding="utf-8")
    pack = cover_pack.build_pack(tmp_path)
    assert pack["cover_strategy_ref"] == "脚本/第1集/封面.md"
