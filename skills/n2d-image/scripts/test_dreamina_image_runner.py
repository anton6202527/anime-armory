"""Dreamina runner tests (cd skills/n2d-image/scripts && python -m pytest test_dreamina_image_runner.py).

Focus: the carried-identity face-anchor parity with the Codex backend — a plate
that depicts a character must always inherit that character's face anchor, even
when the hand-written 参考图 prose block lists an unrelated placeholder image.
"""
import importlib.util
import json
import sys
from pathlib import Path


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


base = _load("codex_image_runner")
dreamina = _load("dreamina_image_runner")


def _project(tmp_path: Path) -> dreamina.base.Target:
    img = tmp_path / "出图" / "共享" / "图片"
    img.mkdir(parents=True)
    for name in ("定妆_沈念_脸部特写.png", "占位图.png", "定妆_万妖血脉觉醒前兆.png"):
        (img / name).write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_01",
            "forms": [{
                "form": "冷宫废妃常态",
                "reference_group": {"face_anchor_refs": [
                    {"path": "出图/共享/图片/定妆_沈念_脸部特写.png", "status": "ready"}]},
            }],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    (shared / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "VFX_01", "type": "vfx", "name": "万妖血脉觉醒前兆",
            "carries_identity": ["CHAR_01/冷宫废妃常态"],
            "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
        }]
    }, ensure_ascii=False), encoding="utf-8")
    section = base.ClipSection(
        clip="VFX_01", title="## ① VFX_01 万妖血脉觉醒前兆",
        # prose lists ONLY an unrelated placeholder — must NOT suppress the face anchor.
        body="**目标存档**：`出图/共享/图片/定妆_万妖血脉觉醒前兆.png`\n**参考图**：`出图/共享/图片/占位图.png`",
        target_line="`出图/共享/图片/定妆_万妖血脉觉醒前兆.png`")
    target = base.Target(shot="VFX_01::定妆_万妖血脉觉醒前兆", clip="VFX_01", mode="shared",
                         rel_path="出图/共享/图片/定妆_万妖血脉觉醒前兆.png", section=section)
    setattr(target, "aliases", {"VFX_01"})
    return target


def test_dreamina_merges_carried_face_anchor_despite_prose_placeholder(tmp_path: Path) -> None:
    target = _project(tmp_path)
    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")
    names = [p.name for p in refs]
    # The 沈念 face anchor is present AND ranked ahead of the placeholder.
    assert "定妆_沈念_脸部特写.png" in names
    assert names.index("定妆_沈念_脸部特写.png") < names.index("占位图.png")


def test_dreamina_unanchored_check_matches_attached_paths(tmp_path: Path) -> None:
    target = _project(tmp_path)
    bundle = base.reference_bundle_for_target(tmp_path, "第1集", target)
    assert bundle["carried_identity"] == ["CHAR_01/冷宫废妃常态"]
    # With the real refs attached (rel-normalized), the plate is anchored.
    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")
    attached_rel = [str(p.relative_to(tmp_path)) for p in refs]
    assert base.carried_identity_unanchored(bundle, attached_rel) is False
    # With nothing identity-bearing attached, it is unanchored → would block spend.
    assert base.carried_identity_unanchored(bundle, ["出图/共享/图片/占位图.png"]) is True
