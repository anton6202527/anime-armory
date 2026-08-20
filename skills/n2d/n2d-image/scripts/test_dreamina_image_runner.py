"""Dreamina runner tests (cd skills/n2d/n2d-image/scripts && python -m pytest test_dreamina_image_runner.py).

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


def test_dreamina_reuse_binds_current_inputs_and_output_pixels(tmp_path: Path) -> None:
    target = _project(tmp_path)
    (tmp_path / "_设置.md").write_text("生图AI：Dreamina\n", encoding="utf-8")
    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")
    reference_inputs = dreamina.dreamina_reference_inputs(tmp_path, target, refs, "第1集")
    compiled = dreamina.build_dreamina_compiled_request(
        tmp_path,
        "第1集",
        target,
        reference_inputs,
        model_version="seedream-5",
        resolution_type="2k",
    )
    fingerprint = dreamina.dreamina_generation_input_fingerprint(
        tmp_path,
        "第1集",
        target,
        seed="seed-1",
        compiled_request=compiled,
        reference_inputs=reference_inputs,
    )
    artifact = tmp_path / target.rel_path
    previous = {
        "status": "pass",
        "input_fingerprint": fingerprint,
        "artifact_sha256": base.file_sha256(artifact),
    }
    assert base.generation_reuse_allowed(
        previous,
        fingerprint,
        artifact_valid=True,
        current_artifact_sha256=base.file_sha256(artifact),
    )

    artifact.write_bytes(b"\x89PNG\r\n\x1a\n" + b"replacement" * 8)
    assert not base.generation_reuse_allowed(
        previous,
        fingerprint,
        artifact_valid=True,
        current_artifact_sha256=base.file_sha256(artifact),
    )
    changed = dreamina.build_dreamina_compiled_request(
        tmp_path,
        "第1集",
        target,
        reference_inputs,
        model_version="seedream-5-new",
        resolution_type="2k",
    )
    changed_fingerprint = dreamina.dreamina_generation_input_fingerprint(
        tmp_path,
        "第1集",
        target,
        seed="seed-1",
        compiled_request=changed,
        reference_inputs=reference_inputs,
    )
    assert changed_fingerprint != fingerprint


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


def test_dreamina_main_scopes_shared_first_interlock_to_selected_targets(tmp_path: Path, monkeypatch) -> None:
    target = _project(tmp_path)
    captured = {}
    monkeypatch.setattr(dreamina, "require_dreamina_image_signoff", lambda _root: None)
    monkeypatch.setattr(base, "build_targets", lambda *_args, **_kwargs: [target])

    def scoped_interlock(_root, _episode, targets=None):
        captured["targets"] = targets
        return False

    monkeypatch.setattr(base, "enforce_shared_first_interlock", scoped_interlock)

    assert dreamina.main([str(tmp_path), "第1集", "--shots", "Clip_02_a1"]) == 1
    assert captured["targets"] == [target]


def test_dreamina_dry_run_resolves_shared_targets_without_episode_preflight(tmp_path: Path, monkeypatch) -> None:
    target = _project(tmp_path)
    captured = {"processed": []}
    monkeypatch.setattr(base, "build_shared_targets", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(
        dreamina,
        "process_target",
        lambda _root, _episode, resolved, **_kwargs: captured["processed"].append(resolved) or True,
    )
    monkeypatch.setattr(base, "run_shared_asset_preflight", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("dry-run must not preflight")))
    monkeypatch.setattr(base, "run_image_gate", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("shared target must not run episode gate")))

    assert dreamina.main([str(tmp_path), "第1集", "--shared-targets", "VFX_01", "--dry-run"]) == 0
    assert captured["processed"] == [target]


def test_dreamina_shared_target_uses_shared_preflight_not_episode_preflight(tmp_path: Path, monkeypatch) -> None:
    target = _project(tmp_path)
    calls = []
    monkeypatch.setattr(dreamina, "require_dreamina_image_signoff", lambda _root: None)
    monkeypatch.setattr(base, "build_shared_targets", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(base, "strict_single_image_review_enabled", lambda _root: False)
    monkeypatch.setattr(base, "run_shared_asset_preflight", lambda *_args, **_kwargs: calls.append("shared") or True)
    monkeypatch.setattr(base, "run_image_gate", lambda *_args, **_kwargs: calls.append("episode") or True)
    monkeypatch.setattr(dreamina, "process_target", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(base, "run_target_image_qc", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(base, "sync_image_progress", lambda *_args, **_kwargs: None)

    assert dreamina.main([str(tmp_path), "第1集", "--shared-targets", "VFX_01"]) == 0
    assert calls == ["shared"]


def test_dreamina_strict_review_rejects_multi_target_paid_call(tmp_path: Path, monkeypatch) -> None:
    target = _project(tmp_path)
    second = base.Target(
        shot="VFX_02", clip="VFX_02", mode="shared",
        rel_path="出图/共享/图片/第二张.png", section=target.section,
    )
    monkeypatch.setattr(dreamina, "require_dreamina_image_signoff", lambda _root: None)
    monkeypatch.setattr(base, "build_shared_targets", lambda *_args, **_kwargs: [target, second])
    monkeypatch.setattr(base, "strict_single_image_review_enabled", lambda _root: True)

    assert dreamina.main([str(tmp_path), "第1集", "--shared-targets", "all"]) == 1


def test_dreamina_record_event_writes_release_grade_recipe_evidence(tmp_path: Path, monkeypatch) -> None:
    target = _project(tmp_path)
    final = tmp_path / target.rel_path
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(b"final-png")
    capability = tmp_path / "生产数据" / "image_backend_capabilities" / "dreamina.json"
    capability.parent.mkdir(parents=True, exist_ok=True)
    capability.write_text('{"backend":"dreamina"}', encoding="utf-8")
    captured = {}

    def capture_run(cmd, **_kwargs):
        captured["cmd"] = cmd
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(dreamina.subprocess, "run", capture_run)
    dreamina.record_event(
        tmp_path,
        "第1集",
        target,
        status="pass",
        duration_sec=1.0,
        task_id="dreamina-test",
        seed="1234",
        temp_path=tmp_path / "temp.png",
        submit_id="submit-1",
        refs=[tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_脸部特写.png"],
        archive_path=None,
        compiled_request={
            "kind": "n2d_compiled_image_prompt",
            "version": 1,
            "model": "Seedream 5.0",
            "channel": "Dreamina/即梦官方 CLI",
            "compiled_request_sha256": "compiled-sha",
            "reference_inputs_sha256": "refs-sha",
            "request_params": {"model_version": "5.0", "resolution_type": "2k"},
        },
        submitted_prompt="test prompt",
        input_fingerprint="pre-spend-fingerprint",
    )

    cmd = captured["cmd"]
    meta = {
        cmd[index + 1].split("=", 1)[0]: cmd[index + 1].split("=", 1)[1]
        for index, token in enumerate(cmd[:-1])
        if token == "--meta" and "=" in cmd[index + 1]
    }
    for key in (
        "model", "channel", "route_hash", "capability_evidence_id", "recipe_hash",
        "prompt_sha256", "reference_bundle_sha256", "backend_version", "quality_tier",
        "actual_image_inputs", "artifact_sha256", "seed_effective", "seed_support",
    ):
        assert meta[key]
    assert meta["reference_bundle_sha256"] == "refs-sha"
    assert meta["seed_effective"] == "false"
    assert meta["input_fingerprint"] == "pre-spend-fingerprint"


def test_dreamina_midframe_pass_records_generation_self_check(tmp_path: Path, monkeypatch) -> None:
    section = base.ClipSection(
        clip="Clip_02", title="## 镜头 2", body="",
        target_line="`出图/第1集/图片/EP01_CLIP02_a1.png`",
    )
    target = base.Target(
        shot="Clip_02_a1", clip="Clip_02", mode="midframe",
        rel_path="出图/第1集/图片/EP01_CLIP02_a1.png", section=section,
    )
    final = tmp_path / target.rel_path
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(b"midframe-png")
    first = base.Target(
        shot="Clip_02_first", clip="Clip_02", mode="firstframe",
        rel_path="出图/第1集/图片/Clip02_first.png", section=section,
    )
    captured = {}

    def capture_run(cmd, **_kwargs):
        captured["cmd"] = cmd
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(base, "target_for_shot", lambda *_args: first)
    monkeypatch.setattr(dreamina.subprocess, "run", capture_run)

    dreamina.record_event(
        tmp_path, "第1集", target,
        status="pass", duration_sec=1.0, task_id="dreamina-test", seed="1234",
        temp_path=tmp_path / "temp.png", submit_id="submit-mid",
        refs=[], archive_path=None,
        compiled_request={"kind": "n2d_compiled_image_prompt", "version": 1},
        submitted_prompt="mid prompt",
    )

    cmd = captured["cmd"]
    meta = {
        cmd[index + 1].split("=", 1)[0]: cmd[index + 1].split("=", 1)[1]
        for index, token in enumerate(cmd[:-1])
        if token == "--meta" and "=" in cmd[index + 1]
    }
    assert meta["self_check"] == "pass"
    assert meta["midframe_role"] == "between_first_and_end"
    assert meta["source_image"] == "出图/第1集/图片/Clip02_first.png"


def _combat_target(body: str) -> "base.Target":
    positive = base.re.search(r"\*\*正向 prompt（中文）\*\*[：:]\s*([^\n]+)", body)
    negative = base.re.search(r"\*\*负向 prompt\*\*[：:]\s*([^\n]+)", body)
    if positive:
        body = (
            "## 镜头 7\n### 正向 prompt（中文）\n"
            f"动作瞬间：{positive.group(1)}\n"
            "### 负向 prompt\n"
            f"{negative.group(1) if negative else ''}"
        )
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


def test_dreamina_relay_keeps_source_first_and_drops_nonfocus_character(tmp_path: Path, monkeypatch) -> None:
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    shared_dir = tmp_path / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    shared_dir.mkdir(parents=True)
    source = image_dir / "EP01_CLIP02.png"
    focus = shared_dir / "CHAR_01_face.png"
    excluded = shared_dir / "CHAR_02_face.png"
    for path in (source, focus, excluded):
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    section = base.ClipSection(
        clip="Clip_02", title="## 镜头 2", body="",
        target_line="`出图/第1集/图片/EP01_CLIP02_a2.png`",
    )
    target = base.Target(
        shot="Clip_02_a2", clip="Clip_02", mode="midframe",
        rel_path="出图/第1集/图片/EP01_CLIP02_a2.png", section=section,
    )
    source_target = base.Target(
        shot="Clip_02_first", clip="Clip_02", mode="firstframe",
        rel_path="出图/第1集/图片/EP01_CLIP02.png", section=section,
    )
    monkeypatch.setattr(base, "target_for_shot", lambda *_args: source_target)
    monkeypatch.setattr(base, "storyboard_anchor_beat", lambda *_args: {
        "single_reaction": True, "focus_ids": ["CHAR_01"],
    })
    monkeypatch.setattr(base, "reference_bundle_for_target", lambda *_args: {"items": [
        {"kind": "character", "id": "CHAR_01", "paths": ["出图/共享/图片/CHAR_01_face.png"]},
        {"kind": "character", "id": "CHAR_02", "paths": ["出图/共享/图片/CHAR_02_face.png"]},
    ]})

    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")
    inputs = dreamina.dreamina_reference_inputs(tmp_path, target, refs, "第1集")

    assert refs[0] == source
    assert focus in refs
    assert excluded not in refs
    assert inputs[0]["role"] == "source_frame"


def test_dreamina_balances_three_character_references_and_plot_context(
    tmp_path: Path, monkeypatch,
) -> None:
    image_dir = tmp_path / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    items = []
    for character_id in ("CHAR_01", "CHAR_02", "CHAR_04"):
        paths = []
        for suffix in ("front", "face_anchor", "half", "side", "back"):
            rel = f"出图/共享/图片/{character_id}_{suffix}.png"
            (tmp_path / rel).write_bytes((character_id + suffix).encode())
            paths.append(rel)
        items.append({"kind": "character", "id": character_id, "paths": paths})
    for asset_id, filename in (
        ("LOC_01", "location.png"),
        ("WEAPON_01", "weapon.png"),
    ):
        rel = f"出图/共享/图片/{filename}"
        (tmp_path / rel).write_bytes(asset_id.encode())
        items.append({"kind": "asset", "id": asset_id, "paths": [rel]})
    section = base.ClipSection(
        clip="Clip_01",
        title="## 镜头 1",
        body="**参考图**：多人近景，LOC_01，WEAPON_01",
        target_line="`出图/第1集/图片/Clip01_first.png`",
    )
    target = base.Target(
        shot="Clip_01_first",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip01_first.png",
        section=section,
    )
    monkeypatch.setattr(base, "reference_bundle_for_target", lambda *_args: {"items": items})
    monkeypatch.setattr(base, "storyboard_anchor_beat", lambda *_args: {})

    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")
    names = [path.name for path in refs]

    assert len(refs) == dreamina.MAX_REFERENCES
    for character_id in ("CHAR_01", "CHAR_02", "CHAR_04"):
        assert f"{character_id}_face_anchor.png" in names
        assert f"{character_id}_front.png" in names
    assert "location.png" in names
    assert "weapon.png" in names


def test_clip02_first_excludes_later_complete_hengdao_reference(
    tmp_path: Path, monkeypatch,
) -> None:
    image_dir = tmp_path / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    face = image_dir / "CHAR_01_face.png"
    location = image_dir / "location.png"
    weapon = image_dir / "hengdao.png"
    for path in (face, location, weapon):
        path.write_bytes(path.name.encode())
    items = [
        {"kind": "character", "id": "CHAR_01", "paths": [str(face.relative_to(tmp_path))]},
        {"kind": "asset", "id": "LOC_01", "paths": [str(location.relative_to(tmp_path))]},
        {"kind": "asset", "id": "PROP_横刀", "paths": [str(weapon.relative_to(tmp_path))]},
    ]
    section = base.ClipSection(
        clip="Clip_02", title="## 镜头 2",
        body="尸场空间一次建立。姜月初摸到囚服。断刀封路。",
        target_line="`出图/第1集/图片/Clip02_first.png`",
    )
    target = base.Target(
        shot="Clip_02_first", clip="Clip_02", mode="firstframe",
        rel_path="出图/第1集/图片/Clip02_first.png", section=section,
    )
    monkeypatch.setattr(base, "reference_bundle_for_target", lambda *_args: {"items": items})
    monkeypatch.setattr(base, "storyboard_anchor_beat", lambda *_args: {})

    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")

    assert face in refs
    assert location in refs
    assert weapon not in refs


def test_clip04_first_includes_accepted_clip02_humanoid_tiger_pose(
    tmp_path: Path, monkeypatch,
) -> None:
    image_dir = tmp_path / "出图" / "第1集" / "图片"
    image_dir.mkdir(parents=True)
    pose_source = image_dir / "Clip02_first.png"
    pose_source.write_bytes(b"accepted full frame with humanoid tiger prone pose")
    pose = (
        tmp_path / "生产数据" / "reference_crops" / "第1集"
        / "Clip02_tiger_prone_pose.png"
    )
    pose.parent.mkdir(parents=True)
    pose.write_bytes(b"cropped humanoid tiger prone pose")
    pose.with_suffix(".json").write_text(json.dumps({
        "source": "出图/第1集/图片/Clip02_first.png",
        "source_sha256": base.file_sha256(pose_source),
        "output_sha256": base.file_sha256(pose),
    }, ensure_ascii=False), encoding="utf-8")
    face = tmp_path / "出图" / "共享" / "图片" / "CHAR_01_face.png"
    face.parent.mkdir(parents=True)
    face.write_bytes(b"face")
    section = base.ClipSection(
        clip="Clip_04", title="## 镜头 4",
        body="50mm双人镜，伪死虎妖后景不消失。",
        target_line="`出图/第1集/图片/Clip04_first.png`",
    )
    target = base.Target(
        shot="Clip_04_first", clip="Clip_04", mode="firstframe",
        rel_path="出图/第1集/图片/Clip04_first.png", section=section,
    )
    bundle = {"items": [{
        "kind": "character", "id": "CHAR_01",
        "paths": [str(face.relative_to(tmp_path))],
    }]}
    monkeypatch.setattr(dreamina, "_accepted_current_hash", lambda *_args: True)

    refs = dreamina.select_dreamina_reference_paths(
        target, bundle, [face], root=tmp_path, source_path=None,
    )

    assert pose in refs
    assert face in refs
    assert refs.index(pose) < refs.index(face)


def test_firstframe_exact_state_relay_uses_previous_accepted_last_anchor_as_source(
    tmp_path: Path, monkeypatch,
) -> None:
    previous = tmp_path / "出图" / "第1集" / "图片" / "EP01_CLIP04_a2.png"
    previous.parent.mkdir(parents=True)
    previous.write_bytes(b"previous-final-anchor")
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [
        {
            "id": "EP01_CLIP04",
            "continuity": {
                "end_state": "少年右肩挑两桶向画左行进",
                "anchors": [{"anchor_png": "出图/第1集/图片/EP01_CLIP04_a2.png"}],
            },
            "shots": [{"t": "0-1s", "lens": "MS", "desc": "少年行进"}],
        },
        {
            "id": "EP01_CLIP05",
            "continuity": {"start_state": "少年右肩挑两桶向画左行进"},
            "shots": [{"t": "0-2s", "lens": "WS", "desc": "少年步幅变小"}],
        },
    ]}, ensure_ascii=False), encoding="utf-8")
    shared = tmp_path / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text('{"characters": []}', encoding="utf-8")
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text(json.dumps({
        "stage": "image", "event": "qa",
        "generation": {
            "asset": "出图/第1集/图片/EP01_CLIP04_a2.png",
            "status": "accepted",
        },
        "meta": {"artifact_sha256": base.file_sha256(previous)},
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    section = base.ClipSection(
        clip="Clip_05", title="## 镜头 5", body="",
        target_line="`出图/第1集/图片/EP01_CLIP05.png`",
    )
    target = base.Target(
        shot="Clip_05_first", clip="Clip_05", mode="firstframe",
        rel_path="出图/第1集/图片/EP01_CLIP05.png", section=section,
    )
    monkeypatch.setattr(base, "reference_bundle_for_target", lambda *_args: {"items": []})

    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")
    inputs = dreamina.dreamina_reference_inputs(tmp_path, target, refs, "第1集")

    assert refs[0] == previous
    assert inputs[0]["role"] == "source_frame"
    assert inputs[0]["owner"] == "Clip_05"


def test_firstframe_does_not_relay_across_intentional_time_discontinuity(
    tmp_path: Path, monkeypatch,
) -> None:
    previous = tmp_path / "出图" / "第1集" / "图片" / "EP01_CLIP01_a1.png"
    previous.parent.mkdir(parents=True)
    previous.write_bytes(b"future-cold-open")
    storyboard = tmp_path / "脚本" / "第1集" / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [
        {
            "id": "EP01_CLIP01",
            "continuity": {
                "end_state": "刀尖停在裴长青胸前",
                "transition": "时间回切",
                "seam_mode": "intentional_discontinuity",
                "seam_evidence": {"reason": "冷开未来片段切回十分钟前"},
                "anchors": [{"anchor_png": "出图/第1集/图片/EP01_CLIP01_a1.png"}],
            },
        },
        {
            "id": "EP01_CLIP02",
            "continuity": {
                "start_state": "刀尖停在裴长青胸前",
                "previous_start_state_note": "姜月初刚在尸场醒来，未持刀",
            },
        },
    ]}, ensure_ascii=False), encoding="utf-8")
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text(json.dumps({
        "stage": "image",
        "event": "qa",
        "generation": {
            "asset": "出图/第1集/图片/EP01_CLIP01_a1.png",
            "status": "accepted",
        },
        "meta": {"artifact_sha256": base.file_sha256(previous)},
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    section = base.ClipSection(
        clip="Clip_02",
        title="## 镜头 2",
        body="",
        target_line="`出图/第1集/图片/Clip02_first.png`",
    )
    target = base.Target(
        shot="Clip_02_first",
        clip="Clip_02",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip02_first.png",
        section=section,
    )
    monkeypatch.setattr(base, "reference_bundle_for_target", lambda *_args: {"items": []})
    monkeypatch.setattr(base, "storyboard_anchor_beat", lambda *_args: {})

    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")

    assert previous not in refs


def test_same_target_exact_hash_rejection_uses_current_pixels_as_correction_source(
    tmp_path: Path, monkeypatch,
) -> None:
    first = tmp_path / "出图" / "第1集" / "图片" / "EP01_CLIP05.png"
    current = first.with_name("EP01_CLIP05_a1.png")
    first.parent.mkdir(parents=True)
    first.write_bytes(b"accepted-first")
    current.write_bytes(b"rejected-current")
    face = tmp_path / "出图" / "共享" / "图片" / "CHAR_01_face.png"
    face.parent.mkdir(parents=True)
    face.write_bytes(b"canonical-face")
    events = tmp_path / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text(json.dumps({
        "stage": "image", "event": "qa",
        "generation": {
            "asset": "出图/第1集/图片/EP01_CLIP05_a1.png",
            "status": "rejected",
        },
        "qa": {"msg": "删除多余的第3只桶"},
        "meta": {
            "artifact_sha256": base.file_sha256(current),
            "review_kind": "executor_visual",
        },
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    section = base.ClipSection(
        clip="Clip_05", title="## 镜头 5", body="",
        target_line="`出图/第1集/图片/EP01_CLIP05_a1.png`",
    )
    target = base.Target(
        shot="Clip_05_a1", clip="Clip_05", mode="midframe",
        rel_path="出图/第1集/图片/EP01_CLIP05_a1.png", section=section,
    )
    monkeypatch.setattr(base, "target_for_shot", lambda *_args: base.Target(
        shot="Clip_05_first", clip="Clip_05", mode="firstframe",
        rel_path="出图/第1集/图片/EP01_CLIP05.png", section=section,
    ))
    monkeypatch.setattr(base, "reference_bundle_for_target", lambda *_args: {"items": [{
        "kind": "character", "id": "CHAR_01",
        "paths": ["出图/共享/图片/CHAR_01_face.png"],
    }]})
    monkeypatch.setattr(base, "storyboard_anchor_beat", lambda *_args: {})

    refs = dreamina.prompt_reference_paths(tmp_path, target, "第1集")
    inputs = dreamina.dreamina_reference_inputs(tmp_path, target, refs, "第1集")

    assert refs[0] == current
    assert first not in refs
    assert inputs[0]["role"] == "source_frame"

    reset_refs = dreamina.prompt_reference_paths(
        tmp_path, target, "第1集", canonical_reset=True,
    )
    reset_inputs = dreamina.dreamina_reference_inputs(
        tmp_path, target, reset_refs, "第1集", canonical_reset=True,
    )

    assert reset_refs[0] == face
    assert current not in reset_refs
    assert first not in reset_refs
    assert reset_inputs[0]["role"] == "character"


def test_canonical_reset_excludes_rejected_target_reintroduced_by_registry(
    tmp_path: Path, monkeypatch,
) -> None:
    current = tmp_path / "出图/共享/图片/定妆_CHAR_02__常态_后45度.png"
    face = tmp_path / "出图/共享/图片/定妆_CHAR_02__常态_脸部特写.png"
    current.parent.mkdir(parents=True)
    current.write_bytes(b"rejected-current")
    face.write_bytes(b"independent-face")
    section = base.ClipSection(
        clip="CHAR_02", title="## CHAR_02", body="",
        target_line="`出图/共享/图片/定妆_CHAR_02__常态_后45度.png`",
    )
    target = base.Target(
        shot="CHAR_02::后45度", clip="CHAR_02", mode="shared",
        rel_path="出图/共享/图片/定妆_CHAR_02__常态_后45度.png", section=section,
    )
    monkeypatch.setattr(base, "reference_bundle_for_target", lambda *_args: {"items": [{
        "kind": "character", "id": "CHAR_02",
        "paths": [
            "出图/共享/图片/定妆_CHAR_02__常态_后45度.png",
            "出图/共享/图片/定妆_CHAR_02__常态_脸部特写.png",
        ],
    }]})
    monkeypatch.setattr(base, "storyboard_anchor_beat", lambda *_args: {})

    reset_refs = dreamina.prompt_reference_paths(
        tmp_path, target, "第1集", canonical_reset=True,
    )

    assert current not in reset_refs
    assert face in reset_refs


def test_dreamina_requeries_same_async_submit_until_image_exists(tmp_path: Path, monkeypatch) -> None:
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"ref")
    section = base.ClipSection(
        clip="Clip_01", title="## 镜头 1", body="",
        target_line="`出图/第1集/图片/EP01_CLIP01.png`",
    )
    target = base.Target(
        shot="Clip_01_first", clip="Clip_01", mode="firstframe",
        rel_path="出图/第1集/图片/EP01_CLIP01.png", section=section,
    )
    temp_path = tmp_path / "work" / "frame.png"
    calls = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        if cmd[1] == "image2image":
            return type("Result", (), {"returncode": 0, "stdout": '{"submit_id":"sid-1"}', "stderr": ""})()
        if len([call for call in calls if call[1] == "query_result"]) == 1:
            return type("Result", (), {
                "returncode": 0,
                "stdout": '{"submit_id":"sid-1","gen_status":"querying","queue_info":{"queue_status":"Generating"}}',
                "stderr": "",
            })()
        download = Path(cmd[cmd.index("--download_dir") + 1])
        download.mkdir(parents=True, exist_ok=True)
        (download / "result.jpg").write_bytes(b"result")
        return type("Result", (), {"returncode": 0, "stdout": '{"gen_status":"done"}', "stderr": ""})()

    monkeypatch.setattr(dreamina.subprocess, "run", fake_run)
    monkeypatch.setattr(dreamina.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(dreamina, "materialize_png", lambda _src, _out: True)

    ok, submit_id, error, _refs = dreamina.run_dreamina(
        target,
        root=tmp_path,
        episode="第1集",
        temp_path=temp_path,
        timeout_sec=30,
        poll_sec=1,
        model_version="5.0",
        resolution_type="2k",
        refs=[ref],
        compiled_request={"prompt": "test prompt", "request_params": {}},
    )

    assert ok is True
    assert submit_id == "sid-1"
    assert error == ""
    assert len([call for call in calls if call[1] == "query_result"]) == 2


def test_dreamina_recovers_paid_submit_from_list_task_after_history_error(
    tmp_path: Path, monkeypatch,
) -> None:
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"ref")
    section = base.ClipSection(
        clip="Clip_01", title="## 镜头 1", body="",
        target_line="`出图/第1集/图片/EP01_CLIP01.png`",
    )
    target = base.Target(
        shot="Clip_01_first", clip="Clip_01", mode="firstframe",
        rel_path="出图/第1集/图片/EP01_CLIP01.png", section=section,
    )
    temp_path = tmp_path / "work" / "frame.png"
    calls = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        if cmd[1] == "image2image":
            return type("Result", (), {
                "returncode": 1, "stdout": "",
                "stderr": "get_history_by_ids failed: ret=2008",
            })()
        if cmd[1] == "list_task":
            return type("Result", (), {
                "returncode": 0,
                "stdout": json.dumps([{
                    "submit_id": "sid-recovered",
                    "prompt": "single-frame-prompt",
                    "gen_status": "querying",
                }]),
                "stderr": "",
            })()
        if cmd[1] == "query_result":
            download_dir = Path(cmd[cmd.index("--download_dir") + 1])
            download_dir.mkdir(parents=True, exist_ok=True)
            (download_dir / "result.png").write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"0" * 64
            )
            return type("Result", (), {
                "returncode": 0, "stdout": '{"gen_status":"success"}', "stderr": "",
            })()
        raise AssertionError(cmd)

    monkeypatch.setattr(dreamina.subprocess, "run", fake_run)
    monkeypatch.setattr(dreamina, "materialize_png", lambda _src, out: out.write_bytes(b"ok") or True)
    ok, sid, error, _refs = dreamina.run_dreamina(
        target,
        root=tmp_path,
        episode="第1集",
        temp_path=temp_path,
        timeout_sec=30,
        poll_sec=1,
        model_version="5.0",
        resolution_type="2k",
        refs=[ref],
        compiled_request={"prompt": "single-frame-prompt"},
    )

    assert ok is True
    assert sid == "sid-recovered"
    assert error == ""
    assert len([call for call in calls if call[1] == "image2image"]) == 1
    assert len([call for call in calls if call[1] == "list_task"]) == 1
