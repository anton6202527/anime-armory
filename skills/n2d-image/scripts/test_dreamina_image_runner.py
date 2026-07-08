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


def test_dreamina_image_runner_requires_signed_exception(tmp_path: Path) -> None:
    try:
        dreamina.require_dreamina_image_signoff(tmp_path)
    except RuntimeError as exc:
        assert "Codex image2" in str(exc)
        assert "image_backend_override.json" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    signoff = tmp_path / "合规" / "image_backend_override.json"
    signoff.parent.mkdir(parents=True)
    signoff.write_text(json.dumps({
        "approved": True,
        "scope": "image",
        "backend": "dreamina_official",
        "reason": "用户明确指定",
    }, ensure_ascii=False), encoding="utf-8")
    dreamina.require_dreamina_image_signoff(tmp_path)


def _combat_target(body: str) -> "base.Target":
    section = base.ClipSection(
        clip="Clip_07", title="## 镜头 7", body=body, target_line="`出图/第1集/图片/镜头7.png`")
    return base.Target(shot="Clip_07::镜头7", clip="Clip_07", mode="firstframe",
                       rel_path="出图/第1集/图片/镜头7.png", section=section)


def test_dreamina_injects_camera_gaze_backstop_for_combat(tmp_path: Path) -> None:
    # 非 POV 打斗镜：即使作者没在「视线方向」里手写防呆，即梦 prompt 也必须含旁观者视线锁 + 负面词。
    body = "**正向 prompt（中文）**：近景，少年挥剑劈砍，对手格挡。\n**负向 prompt**：模糊"
    prompt = dreamina.build_dreamina_prompt(tmp_path, "第1集", _combat_target(body))
    assert "镜头为旁观者视角" in prompt
    assert "不看镜头" in prompt
    assert "直视镜头" in prompt  # 负面词来自 n2d_const.CAMERA_GAZE_NEGATIVES
    # 与 Codex 后端同源：两条 helper 对同一 body 的判定一致。
    assert base.camera_gaze_negatives_for(body)


def test_dreamina_pov_shot_is_exempt(tmp_path: Path) -> None:
    # 显式 POV / 破第四墙镜：不得注入防呆（否则破坏主观镜头/对观众压迫特写）。
    body = "**正向 prompt（中文）**：opponent POV 主观镜头，破第四墙，角色直视镜头压迫观众。"
    prompt = dreamina.build_dreamina_prompt(tmp_path, "第1集", _combat_target(body))
    assert "镜头为旁观者视角" not in prompt
    assert base.camera_gaze_negatives_for(body) == ""


def test_dreamina_injects_spectacle_richness_for_combat(tmp_path: Path) -> None:
    # 打斗镜：即梦 prompt 必须含「经费在燃烧」四层（体积光/大气纵深/环境受力/运动能量）。
    body = "**正向 prompt（中文）**：少年挥剑劈砍，命中炸开冲击波。\n**负向 prompt**：模糊"
    prompt = dreamina.build_dreamina_prompt(tmp_path, "第1集", _combat_target(body))
    assert "经费在燃烧" in prompt
    assert "体积光" in prompt and "大气透视" in prompt
    assert base.combat_spectacle_richness_for(body)


def test_dreamina_injects_hand_limb_ownership_backstop(tmp_path: Path) -> None:
    body = (
        "**正向 prompt（中文）**：`CHAR_01/常态` 少女一手按住金色古卷，"
        "另一手握住横刀刀柄。\n**负向 prompt**：模糊"
    )
    prompt = dreamina.build_dreamina_prompt(tmp_path, "第1集", _combat_target(body))
    assert "手部/肢体归属铁律" in prompt
    assert "镜像右手/镜像左手" in prompt
    assert "另一只手和武器的归属必须明确" in prompt
    assert base.hand_limb_anatomy_guidance(_combat_target(body))


def test_dreamina_no_spectacle_richness_for_calm_shot(tmp_path: Path) -> None:
    # 平静对白/无动作镜：不得注入盛宴层（避免给每个镜堆特效·稀释 prompt）。
    body = "**正向 prompt（中文）**：少女在窗边静静喝茶，神情温柔。\n**负向 prompt**：模糊"
    prompt = dreamina.build_dreamina_prompt(tmp_path, "第1集", _combat_target(body))
    assert "经费在燃烧" not in prompt
    assert base.combat_spectacle_richness_for(body) == ""


def _write_style_contract(tmp_path: Path, style_name: str) -> None:
    p = tmp_path / "脚本" / "第1集"
    p.mkdir(parents=True, exist_ok=True)
    (p / "storyboard.json").write_text(
        json.dumps({"style_contract": {"风格名": style_name}}, ensure_ascii=False),
        encoding="utf-8")


def test_dreamina_spectacle_adapts_to_cel_style(tmp_path: Path) -> None:
    # P0-1：赛璐璐风格的打斗镜，盛宴层换成赛璐璐速度线变体，绝不硬塞写实体积光/motion blur 长拖影。
    _write_style_contract(tmp_path, "二次元赛璐璐")
    body = "**正向 prompt（中文）**：少年挥剑劈砍，命中炸开冲击波。\n**负向 prompt**：模糊"
    prompt = dreamina.build_dreamina_prompt(tmp_path, "第1集", _combat_target(body))
    assert "赛璐璐" in prompt and "速度线" in prompt
    assert "丁达尔光束穿过烟尘" not in prompt
    assert "顺攻击方向给速度线 + 拖影 motion blur" not in prompt


def test_dreamina_spectacle_adapts_to_ink_style(tmp_path: Path) -> None:
    # 水墨风格的打斗镜：飞白泼墨气劲 + 留白纵深，不用写实体积光/景深。
    _write_style_contract(tmp_path, "水墨国风")
    body = "**正向 prompt（中文）**：剑客御剑斩击，剑气迸射。\n**负向 prompt**：模糊"
    prompt = dreamina.build_dreamina_prompt(tmp_path, "第1集", _combat_target(body))
    assert "飞白" in prompt and "留白" in prompt
    assert "丁达尔光束穿过烟尘" not in prompt


def test_dreamina_spectacle_stays_cinematic_for_realist_style(tmp_path: Path) -> None:
    # 写实风格：仍走原写实四层（含「经费在燃烧」「丁达尔」），与历史行为一致。
    _write_style_contract(tmp_path, "写实电影感")
    body = "**正向 prompt（中文）**：武者出拳，命中震飞对手。\n**负向 prompt**：模糊"
    prompt = dreamina.build_dreamina_prompt(tmp_path, "第1集", _combat_target(body))
    assert "经费在燃烧" in prompt and "丁达尔" in prompt


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
