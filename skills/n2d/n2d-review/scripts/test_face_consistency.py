"""face_consistency 纯数学单测（无需 insightface/GPU）。
cd skills/n2d/n2d-review/scripts && python -m pytest test_face_consistency.py
"""
import math
import os
import json

import face_consistency as fc


def test_cosine_basic():
    assert fc.cosine([1, 0], [1, 0]) == 1.0
    assert abs(fc.cosine([1, 0], [0, 1])) < 1e-9
    assert fc.cosine([1, 0], [-1, 0]) == -1.0
    assert fc.cosine([0, 0], [1, 1]) == 0.0  # 零向量保护


def test_cosine_dim_mismatch():
    try:
        fc.cosine([1, 2, 3], [1, 2])
        assert False
    except ValueError:
        pass


def test_calibrate_floor_takes_min_above_conservative_guard():
    assert fc.calibrate_floor([0.9, 0.7, 0.82]) == 0.7


def test_calibrate_floor_bad_variant_cannot_collapse_identity_gate():
    assert fc.calibrate_floor([0.91, 0.84, 0.032]) == 0.50


def test_best_anchor_score_takes_max_over_views():
    # 侧脸镜：vs 正脸低、vs 侧脸高 → 取最大（角度感知，去正脸偏惩罚）
    front = [1.0, 0.0]
    side = [0.0, 1.0]
    shot_sideish = [0.1, 0.99]  # 明显更像 side
    s = fc.best_anchor_score(shot_sideish, [front, side])
    assert abs(s - fc.cosine(shot_sideish, side)) < 1e-9   # = 最像那个视图
    assert s > fc.cosine(shot_sideish, front)               # 比只比正脸高
    # 真崩脸：对哪个视图都不像 → 最大值仍低（不放过）
    drifted = [-1.0, 0.0]
    assert fc.best_anchor_score(drifted, [front, side]) <= 0.0
    # 无 variant → None
    assert fc.best_anchor_score(shot_sideish, []) is None


def test_best_face_match_selects_expected_face_not_largest():
    # 输入顺序模拟 detector 面积排序：face0 是最大脸但不像主角，face1 较小但像主角。
    main = [1.0, 0.0]
    side = [0.7, 0.7]
    faces = [[0.0, 1.0], [0.98, 0.02]]
    score, score_vs_main, face_idx = fc.best_face_match(faces, main, [main, side])
    assert face_idx == 1
    assert score > 0.95
    assert score_vs_main > 0.95


def test_calibrate_floor_fallback_when_single():
    # 单张定妆（无内部对）→ 回退保守同人下限
    assert fc.calibrate_floor([]) == 0.50
    assert fc.calibrate_floor([], fallback=0.55) == 0.55


def test_episode_mean():
    assert fc.episode_mean([0.8, 0.6, 0.7]) == 0.7
    assert fc.episode_mean([0.8, None, 0.6]) == 0.7
    assert fc.episode_mean([None, None]) is None
    assert fc.episode_mean([]) is None


def test_cross_episode_drift_flags_systematic_decline():
    # ep1 基线 0.75 → ep2 0.55（掉 0.20 ≥ block 阈）→ high；尽管各集可能都过了自己的 floor
    seq = [("第1集", 0.75), ("第2集", 0.55)]
    out = fc.cross_episode_drift(seq)
    assert len(out) == 1
    assert out[0]["episode_from"] == "第1集" and out[0]["episode_to"] == "第2集"
    assert out[0]["severity"] == "high" and out[0]["drop"] == 0.2


def test_cross_episode_drift_medium_and_stable():
    # 掉 0.10 → medium；掉 0.03 → 不报
    assert fc.cross_episode_drift([("第1集", 0.75), ("第2集", 0.65)])[0]["severity"] == "medium"
    assert fc.cross_episode_drift([("第1集", 0.75), ("第2集", 0.72)]) == []


def test_cross_episode_drift_abs_low_without_block_drop_is_medium():
    # 绝对分偏低但没有达到跨集掉幅 block 阈，只做趋势预警，不当成系统性退化 hard block。
    out = fc.cross_episode_drift([("第1集", 0.50), ("第2集", 0.44)])
    assert out and out[0]["severity"] == "medium" and out[0]["below_abs_low"] is True


def test_cross_episode_drift_abs_low_with_block_drop_is_high():
    out = fc.cross_episode_drift([("第1集", 0.75), ("第2集", 0.44)])
    assert out and out[0]["severity"] == "high" and out[0]["below_abs_low"] is True


def test_cross_episode_drift_needs_two_episodes():
    assert fc.cross_episode_drift([("第1集", 0.7)]) == []
    assert fc.cross_episode_drift([("第1集", None), ("第2集", 0.4)]) == []


def test_band_three_zones():
    floor = 0.70  # warn 区 = [0.62, 0.70)，block = <0.62
    assert fc.band(0.80, floor, margin=0.08) == "ok"      # ≥floor
    assert fc.band(0.70, floor, margin=0.08) == "ok"      # =floor 放行
    assert fc.band(0.66, floor, margin=0.08) == "warn"    # floor-margin..floor
    assert fc.band(0.64, floor, margin=0.08) == "warn"    # 区内
    assert fc.band(0.60, floor, margin=0.08) == "block"   # <floor-margin
    assert fc.band(0.20, floor, margin=0.08) == "block"


def test_is_character_asset():
    assert fc.is_character_asset("王敦")
    assert fc.is_character_asset("少年王敦")
    assert fc.is_character_asset("小妖A_覆鳞宫女")
    assert not fc.is_character_asset("灵药谷山洞")   # 场景
    assert not fc.is_character_asset("淡青系统符纹光幕")  # 特效
    assert not fc.is_character_asset("豆油灯")        # 道具(灯)
    assert not fc.is_character_asset("未来神界主桌剪影")  # 剪影
    assert not fc.is_character_asset("斑驳铜镜")
    assert not fc.is_character_asset("毒酒碎瓷")


def test_resolve_project_path_does_not_duplicate_prefixed_root():
    root = os.path.join("projects", "demo")
    already_prefixed = os.path.join(root, "出图", "共享", "图片", "定妆_main.png")
    project_relative = os.path.join("出图", "共享", "图片", "定妆_main.png")
    absolute = os.path.abspath(already_prefixed)

    assert fc._resolve_project_path(root, already_prefixed) == already_prefixed
    assert fc._resolve_project_path(root, project_relative) == already_prefixed
    assert fc._resolve_project_path(root, absolute) == absolute


def test_discover_costume_sets_uses_identity_registry_filter(tmp_path):
    import json

    root = tmp_path
    shared = root / "出图" / "共享"
    img_dir = shared / "图片"
    img_dir.mkdir(parents=True)
    for name in [
        "定妆_沈念_常态.png",
        "定妆_沈念_常态_侧.png",
        "定妆_沈念_常态_脸部特写.png",
        "定妆_小妖A_覆鳞宫女.png",
        "定妆_斑驳铜镜.png",
        "定妆_毒酒碎瓷.png",
    ]:
        (img_dir / name).write_bytes(b"")
    (shared / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {"id": "CHAR_01", "forms": [{"form": "常态", "asset_key": "沈念_常态"}]},
                    {"id": "CHAR_06", "forms": [{"form": "常态", "asset_key": "小妖A_覆鳞宫女"}]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    sets = fc.discover_costume_sets(str(root))
    assert sorted(sets) == ["小妖A_覆鳞宫女", "沈念_常态"]
    assert sorted(sets["沈念_常态"]) == ["主", "侧", "脸部特写"]


def test_discover_costume_sets_reads_registry_45_and_face_anchor(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    img_dir = root / "出图" / "共享" / "图片"
    img_dir.mkdir(parents=True)
    for name in [
        "定妆_沈念_常态.png",
        "定妆_沈念_常态_45度.png",
        "定妆_沈念_常态_脸部特写.png",
    ]:
        (img_dir / name).write_bytes(b"png")
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_01",
                        "forms": [
                            {
                                "form": "常态",
                                "asset_key": "沈念_常态",
                                "reference_group": {
                                    "front": "出图/共享/图片/定妆_沈念_常态.png",
                                    "three_quarter": "出图/共享/图片/定妆_沈念_常态_45度.png",
                                    "face_anchor_refs": [
                                        {"path": "出图/共享/图片/定妆_沈念_常态_脸部特写.png"}
                                    ],
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    sets = fc.discover_costume_sets(str(root))
    assert sorted(sets["沈念_常态"]) == ["45度", "主", "脸部特写"]


def test_discover_costume_sets_reads_registry_path_objects(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    img_dir = root / "出图" / "共享" / "图片"
    img_dir.mkdir(parents=True)
    for name in ["CHAR_SHENNIAN_常态.png", "CHAR_SHENNIAN_常态_脸部特写.png"]:
        (img_dir / name).write_bytes(b"png")
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_SHENNIAN",
                        "forms": [
                            {
                                "form": "常态",
                                "asset_key": "沈念_常态",
                                "reference_group": {
                                    "front": {"path": "出图/共享/图片/CHAR_SHENNIAN_常态.png", "status": "ready"},
                                    "face_anchor_refs": [
                                        {"path": "出图/共享/图片/CHAR_SHENNIAN_常态_脸部特写.png", "status": "ready"}
                                    ],
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    sets = fc.discover_costume_sets(str(root))
    assert sorted(sets["沈念_常态"]) == ["主", "脸部特写"]


def test_identity_ref_regex_ignores_char_file_stems():
    import face_consistency as fc

    text = "`出图/共享/图片/CHAR_SHENNIAN_常态.png` `CHAR_SHENNIAN/常态`"
    assert fc.IDENTITY_REF_RE.findall(text) == ["CHAR_SHENNIAN/常态"]


def test_severity_order():
    assert fc._sev("block") > fc._sev("warn") > fc._sev("ok") > fc._sev("noface")


def test_anchor_verdict():
    assert fc.anchor_verdict(0, 0.0) == "block"                  # 锚点没脸
    assert fc.anchor_verdict(2, 0.3) == "block"                  # 多张脸
    assert fc.anchor_verdict(1, 0.02, min_ratio=0.06) == "warn"  # 脸太小
    assert fc.anchor_verdict(1, 0.20, min_ratio=0.06) == "ok"    # 单张够大正脸
    assert fc.anchor_verdict(1, 0.06, min_ratio=0.06) == "ok"    # 等于下限放行


def test_registry_anchor_policy_marks_non_human_creature(tmp_path):
    reg_dir = tmp_path / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(json.dumps({
        "characters": [{
            "id": "CHAR_YUNLING",
            "forms": [{
                "form": "金翅大鹏真身",
                "asset_key": "CHAR_YUNLING_GOLDEN_ROC",
                "anchor_policy": {"type": "non_human_creature"},
            }],
        }],
    }, ensure_ascii=False), encoding="utf-8")
    policies = fc.registry_anchor_policies(str(tmp_path))
    assert fc.is_non_human_anchor_policy(policies["CHAR_YUNLING_GOLDEN_ROC"])
    assert not fc.is_non_human_anchor_policy({"type": "humanoid_face"})


def test_registry_anchor_policy_infers_tiger_headed_creature(tmp_path):
    reg_dir = tmp_path / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(json.dumps({
        "characters": [
            {
                "id": "CHAR_03",
                "name": "虎山神 / 虎妖",
                "forms": [{
                    "form": "诈死复苏态",
                    "asset_key": "CHAR_03__诈死复苏态",
                    "anchor_phrase": "虎首人身·巨型如山·黄黑虎纹",
                    "character_dna": {"face": "妖物；虎头人身，金黄凶眼。"},
                }],
            },
            {
                "id": "CHAR_04",
                "name": "人形狐妖",
                "forms": [{
                    "form": "常态",
                    "asset_key": "CHAR_04__常态",
                    "character_dna": {"face": "人形女子脸，狐媚眼型但五官为人脸。"},
                }],
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")

    policies = fc.registry_anchor_policies(str(tmp_path))
    assert fc.is_non_human_anchor_policy(policies["CHAR_03__诈死复苏态"])
    assert policies["CHAR_03__诈死复苏态"]["inferred"] is True
    assert "CHAR_04__常态" not in policies


def test_pillow_fallback_when_no_insightface(tmp_path):
    """无 insightface（本机真实环境）→ Pillow 降级档：有信号但 mode/precision 标降级，绝不输出相似度。"""
    import json
    import os

    import face_consistency as fc

    # 本机没有 insightface，analyze 应走 pillow_fallback（若装了 insightface 则跳过本用例）
    if fc._load_embedder() is not None:
        import pytest
        pytest.skip("本机装有 insightface，降级档不生效")
    image_mod = fc._load_pillow()
    if image_mod is None:
        import pytest
        pytest.skip("本机未装 Pillow，无法验证降级档（环境缺依赖，非逻辑问题）")

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    img_dir = root / "出图" / ep / "图片"
    img_dir.mkdir(parents=True)
    # 一镜引用沈念定妆：目标 PNG 存在（清晰大图）；另一镜 PNG 缺失
    from PIL import Image
    import random
    img = Image.new("RGB", (1024, 1024))
    img.putdata([(random.randint(0, 255),) * 3 for _ in range(1024 * 1024)])
    img.save(img_dir / "Clip_01.png")
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join([
            "## Clip 01",
            "目标：出图/第1集/图片/Clip_01.png",
            "参考图：定妆_沈念.png",
            "## Clip 02",
            "目标：出图/第1集/图片/Clip_02.png",
            "参考图：定妆_沈念.png",
        ]),
        encoding="utf-8",
    )

    result = fc.analyze(str(root), ep)
    assert result["available"] is True
    assert result["mode"] == fc.PILLOW_FALLBACK_MODE
    assert result["precision"] == "insufficient_precision"
    shots = {s["png"]: s for s in result["shots"]}
    assert "图片/Clip_02.png" in json.dumps(shots, ensure_ascii=False) or any(
        "Clip_02" in p for p in shots
    )
    missing = next(s for p, s in shots.items() if "Clip_02" in p)
    assert missing["verdict"] == "missing"
    assert missing["code"] == "image_target_missing"
    assert "尚未生成" in "；".join(missing["checks"])
    ok_shot = next(s for p, s in shots.items() if "Clip_01" in p)
    assert ok_shot["verdict"] in {"ok", "warn"}
    # 绝不臆造相似度
    assert "similarity" not in json.dumps(result)


def test_shot_character_map_prefers_identity_layer_over_background_refs(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {"id": "CHAR_01", "forms": [{"form": "觉醒态", "asset_key": "沈念_觉醒态"}]},
                    {"id": "CHAR_03", "forms": [{"form": "破皮惊恐态", "asset_key": "柳娘子_破皮惊恐态"}]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join(
            [
                "## Clip 18",
                "目标：出图/第1集/图片/Clip_18_铜镜金瞳.png",
                "参考图：",
                "- `出图/共享/图片/定妆_沈念_觉醒态.png`",
                "- `出图/共享/图片/定妆_柳娘子_破皮惊恐态.png`（右后景反应锚）",
                "**资产身份注册层**：`CHAR_01/觉醒态`；沈念为铜镜最大脸。",
            ]
        ),
        encoding="utf-8",
    )

    assert fc.shot_character_map(str(root), ep)["图片/Clip_18_铜镜金瞳.png"] == ["沈念_觉醒态"]


def test_shot_character_map_uses_storyboard_targets_when_prompt_has_no_target_line(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    script_dir = root / "脚本" / ep
    script_dir.mkdir(parents=True)
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {"id": "CHAR_01", "forms": [{"form": "常态", "asset_key": "沈念_常态"}]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (script_dir / "storyboard.json").write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "id": "EP01_CLIP01",
                        "firstframe_png": "出图/第1集/图片/Clip_01_毒酒抵唇.png",
                        "continuity": {
                            "midframe": {"midframe_png": "出图/第1集/图片/Clip_01_毒酒抵唇_mid.png"},
                            "endframe_png": "出图/第1集/图片/Clip_01_毒酒抵唇_end.png",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join(
            [
                "## 镜头 1（EP01_CLIP01 毒酒抵唇）",
                "参考图：`出图/共享/图片/定妆_沈念_常态.png`",
                "**资产身份注册层**：`CHAR_01/常态*`；不得纯文生图。",
                "**中段锚帧生成方式**：`Clip_01_毒酒抵唇_mid.png` 以首帧为母图。",
            ]
        ),
        encoding="utf-8",
    )

    shot_map = fc.shot_character_map(str(root), ep)
    assert shot_map["图片/Clip_01_毒酒抵唇.png"] == ["沈念_常态"]
    assert shot_map["图片/Clip_01_毒酒抵唇_mid.png"] == ["沈念_常态"]
    assert shot_map["图片/Clip_01_毒酒抵唇_end.png"] == ["沈念_常态"]


def test_shot_character_map_uses_starred_primary_identity(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {"id": "CHAR_01", "forms": [{"form": "觉醒态", "asset_key": "沈念_觉醒态"}]},
                    {"id": "CHAR_03", "forms": [{"form": "破皮惊恐态", "asset_key": "柳娘子_破皮惊恐态"}]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join(
            [
                "## Clip 07",
                "目标：出图/第1集/图片/Clip_07_人皮裂鳞.png",
                "**资产身份注册层**：`CHAR_01/觉醒态`；`CHAR_03*/破皮惊恐态`；柳娘子为主检脸。",
                "## Clip 16",
                "目标：出图/第1集/图片/Clip_16_一次只够吃一个.png",
                "**资产身份注册层**：`CHAR_01*/觉醒态`；`CHAR_03/破皮惊恐态`；兼容旧星标写法。",
            ]
        ),
        encoding="utf-8",
    )

    shot_map = fc.shot_character_map(str(root), ep)
    assert shot_map["图片/Clip_07_人皮裂鳞.png"] == ["柳娘子_破皮惊恐态"]
    assert shot_map["图片/Clip_16_一次只够吃一个.png"] == ["沈念_觉醒态"]


def test_shot_character_map_uses_primary_slot_marker(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {"id": "CHAR_01", "forms": [{"form": "常态", "asset_key": "沈念_常态"}]},
                    {"id": "CHAR_02", "forms": [{"form": "常态", "asset_key": "张老大_常态"}]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join(
            [
                "## Clip 02",
                "目标：出图/第1集/图片/Clip02_first.png",
                "**资产身份注册层**：`CHAR_02/常态`, `CHAR_01/常态`；二人都登记。",
                "**多人同框身份槽位**：SLOT_1: `CHAR_02/常态` -> 画右前景，primary 星标；"
                "SLOT_2: `CHAR_01/常态` -> 画左低位反应。",
            ]
        ),
        encoding="utf-8",
    )

    shot_map = fc.shot_character_map(str(root), ep)
    assert shot_map["图片/Clip02_first.png"] == ["张老大_常态"]


def test_shot_character_map_uses_timed_reaction_anchor_focus(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生", "forms": [{"form": "常态", "asset_key": "贺平生_常态"}]},
        {"id": "CHAR_02", "name": "张老大", "forms": [{"form": "常态", "asset_key": "张老大_常态"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    (prompt_dir / "01_分镜出图.md").write_text("\n".join([
        "## Clip 02",
        "目标：出图/第1集/图片/EP01_CLIP02.png 出图/第1集/图片/EP01_CLIP02_a2.png",
        "**资产身份注册层**：`CHAR_01/常态`, `CHAR_02/常态`；二人都登记。",
        "**多人同框身份槽位**：SLOT_1: `CHAR_02/常态` -> primary 星标；SLOT_2: `CHAR_01/常态`。",
    ]), encoding="utf-8")
    storyboard = root / "脚本" / ep / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP02",
        "continuity": {"anchors": [{"anchor_png": "出图/第1集/图片/EP01_CLIP02_a2.png", "at_sec": 6.1}]},
        "shots": [
            {"t": "0-6.1s", "lens": "MCU", "desc": "张老大俯身下令"},
            {"t": "6.1-7.9s", "lens": "CU", "desc": "贺平生垂眼短促应下"},
        ],
    }]}, ensure_ascii=False), encoding="utf-8")

    shot_map = fc.shot_character_map(str(root), ep)
    assert shot_map["图片/EP01_CLIP02.png"] == ["张老大_常态"]
    assert shot_map["图片/EP01_CLIP02_a2.png"] == ["贺平生_常态"]


def test_shot_character_map_skips_prop_detail_insert_face(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "贺平生", "forms": [{"form": "常态", "asset_key": "贺平生_常态"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    (prompt_dir / "01_分镜出图.md").write_text("\n".join([
        "## Clip 07",
        "目标：出图/第1集/图片/EP01_CLIP07.png 出图/第1集/图片/EP01_CLIP07_a1.png",
        "**资产身份注册层**：`CHAR_01/常态`。",
    ]), encoding="utf-8")
    storyboard = root / "脚本" / ep / "storyboard.json"
    storyboard.parent.mkdir(parents=True)
    storyboard.write_text(json.dumps({"clips": [{
        "id": "EP01_CLIP07",
        "firstframe_png": "出图/第1集/图片/EP01_CLIP07.png",
        "continuity": {"anchors": [{"anchor_png": "出图/第1集/图片/EP01_CLIP07_a1.png", "at_sec": 2.4}]},
        "shots": [
            {"t": "0-2.4s", "lens": "MS", "desc": "贺平生抱盆转身"},
            {"t": "2.4-3.9s", "lens": "ECU insert", "desc": "水滴滑过破损盆底，细纹亮起"},
        ],
    }]}, ensure_ascii=False), encoding="utf-8")

    shot_map = fc.shot_character_map(str(root), ep)

    assert shot_map["图片/EP01_CLIP07.png"] == ["贺平生_常态"]
    assert "图片/EP01_CLIP07_a1.png" not in shot_map


def test_shot_character_map_explicit_star_overrides_primary_slot_text(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {"id": "CHAR_01", "forms": [{"form": "囚犯初醒态", "asset_key": "姜月初_囚犯初醒态"}]},
                    {"id": "CHAR_02", "forms": [{"form": "濒死战损态", "asset_key": "裴长青_濒死战损态"}]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join(
            [
                "## Clip 08",
                "目标：出图/第1集/图片/Clip08_first.png",
                "**资产身份注册层**：`CHAR_01/囚犯初醒态`, `CHAR_02/濒死战损态`；二人都登记。",
                "**主检脸星标**：`CHAR_02/濒死战损态*`；`CHAR_01/囚犯初醒态` 只作 OTS/手部。",
                "**多人同框身份槽位**：SLOT_1: `CHAR_01/囚犯初醒态` -> 画左前景，primary 星标；"
                "SLOT_2: `CHAR_02/濒死战损态` -> 画右下近景。",
            ]
        ),
        encoding="utf-8",
    )

    shot_map = fc.shot_character_map(str(root), ep)
    assert shot_map["图片/Clip08_first.png"] == ["裴长青_濒死战损态"]


def test_shot_character_map_ignores_offscreen_continuity_refs(tmp_path):
    import json
    import face_consistency as fc

    root = tmp_path
    ep = "第2集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    reg_dir = root / "出图" / "共享"
    reg_dir.mkdir(parents=True)
    (reg_dir / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {"id": "CHAR_01", "forms": [{"form": "囚犯初醒态", "asset_key": "姜月初_囚犯初醒态"}]},
                    {"id": "CHAR_02", "forms": [{"form": "濒死战损态", "asset_key": "裴长青_濒死战损态"}]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join(
            [
                "## Clip 10",
                "目标：出图/第2集/图片/Clip10_first.png 出图/第2集/图片/Clip10_mid.png 出图/第2集/图片/Clip10_end.png",
                "**资产身份注册层**：`CHAR_01/囚犯初醒态`；本镜从共享定妆 image2image / 多图参考派生。",
                "**本镜状态锁**：`CHAR_01`: 警觉迎新危机；`CHAR_02`: 欠命账象征。",
                "**专项镜头模板**：continuity_must=[\"CHAR_02 可画外保留，WEAPON_01 横刀也可画外保留；二者不是角色形态绑定\"]。",
                "身份锁定句：裴长青 `CHAR_02/濒死战损态` 必须与人物定妆保持同一张脸，但本镜不入画。",
            ]
        ),
        encoding="utf-8",
    )

    shot_map = fc.shot_character_map(str(root), ep)
    assert shot_map["图片/Clip10_first.png"] == ["姜月初_囚犯初醒态"]
    assert shot_map["图片/Clip10_mid.png"] == ["姜月初_囚犯初醒态"]
    assert shot_map["图片/Clip10_end.png"] == ["姜月初_囚犯初醒态"]


def test_shot_character_map_falls_back_to_reference_block_without_identity(tmp_path):
    import face_consistency as fc

    root = tmp_path
    ep = "第1集"
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "01_分镜出图.md").write_text(
        "\n".join(
            [
                "## Clip 01",
                "目标：出图/第1集/图片/Clip_01.png",
                "参考图：定妆_沈念_常态.png 定妆_柳娘子_人皮态.png",
            ]
        ),
        encoding="utf-8",
    )

    assert fc.shot_character_map(str(root), ep)["图片/Clip_01.png"] == ["沈念_常态", "柳娘子_人皮态"]


# ── T11: flag-band 单张样本降权（floor_calibrated）────────────────────────────
def test_floor_calibrated_predicate():
    import face_consistency as fc
    assert fc.floor_calibrated([]) is False          # 无内部对（单张定妆）→ 地板未自标定
    assert fc.floor_calibrated([None]) is False
    assert fc.floor_calibrated([0.7]) is True         # ≥1 对 → 已自标定
    assert fc.floor_calibrated([0.6, 0.8]) is True
    # 单张样本地板退回保守经验值；调用方据 floor_calibrated=False 降权而非硬判
    assert fc.calibrate_floor([]) == 0.50


# ── T11: 同框多角色串脸分配匹配（detect_face_swaps）──────────────────────────
def test_detect_face_swaps_clean_two_shot():
    import face_consistency as fc
    A, B = [1.0, 0.0], [0.0, 1.0]
    faces = [[0.98, 0.02], [0.03, 0.97]]  # 一张像A一张像B
    res = fc.detect_face_swaps(faces, {"沈念": A, "柳娘子": B})
    assert res["duplicate_chars"] == [] and res["missing_chars"] == []
    assert res["swap_suspected"] is False


def test_detect_face_swaps_both_faces_look_like_one_char():
    import face_consistency as fc
    A, B = [1.0, 0.0], [0.0, 1.0]
    faces = [[0.99, 0.01], [0.97, 0.03]]  # 两张脸都最像 A → 柳娘子被画成了沈念
    res = fc.detect_face_swaps(faces, {"沈念": A, "柳娘子": B})
    assert res["duplicate_chars"] == ["沈念"] and res["missing_chars"] == ["柳娘子"]
    assert res["swap_suspected"] is True


def test_detect_face_swaps_uses_variant_banks_for_profile_faces():
    import face_consistency as fc

    # A 的侧脸如果只和 A 正脸比，会比 B 正脸更低；用 A 的侧脸锚后应正确归到 A。
    A_front, A_side = [1.0, 0.0], [0.0, 1.0]
    B_front = [0.55, 0.45]
    faces = [[0.05, 0.95], [0.6, 0.4]]
    res = fc.detect_face_swaps(faces, {"沈念": [A_front, A_side], "柳娘子": [B_front]})
    assert res["duplicate_chars"] == []
    assert res["missing_chars"] == []
    assert res["swap_suspected"] is False


def test_detect_face_swaps_empty_or_no_chars():
    import face_consistency as fc
    assert fc.detect_face_swaps([], {"沈念": [1.0, 0.0]})["assignments"] == []
    assert fc.detect_face_swaps([[1.0, 0.0]], {})["assignments"] == []


def test_swap_verdict_escalates_confident_swap_to_block():
    import face_consistency as fc
    # 一多一少（张冠李戴）= 确凿穿帮 → block（即便起评 ok）
    swap_sus = {"duplicate_chars": ["沈念"], "missing_chars": ["柳娘子"], "swap_suspected": True}
    assert fc.swap_verdict(swap_sus, "ok") == "block"
    assert fc.swap_verdict(swap_sus, "warn") == "block"
    # 仅 duplicate/missing 之一（弱信号）→ 至少 warn，不到 block
    weak = {"duplicate_chars": ["沈念"], "missing_chars": [], "swap_suspected": False}
    assert fc.swap_verdict(weak, "ok") == "warn"
    # 无串脸信号 → 不动
    assert fc.swap_verdict({"duplicate_chars": [], "missing_chars": [], "swap_suspected": False}, "ok") == "ok"
    # 已是 block 不降级
    assert fc.swap_verdict(weak, "block") == "block"


def test_select_face_encoder_explicit_and_env(monkeypatch):
    monkeypatch.delenv("N2D_FACE_EMBEDDER", raising=False)
    assert fc.select_face_encoder("styleid") == "styleid"
    assert fc.select_face_encoder("arcface") == "arcface"
    # 显式 backend 覆盖 env
    monkeypatch.setenv("N2D_FACE_EMBEDDER", "arcface")
    assert fc.select_face_encoder("styleid") == "styleid"
    # 仅 env
    assert fc.select_face_encoder(None) == "arcface"
    monkeypatch.setenv("N2D_FACE_EMBEDDER", "styleid")
    assert fc.select_face_encoder(None) == "styleid"


def test_select_face_encoder_style_hint(monkeypatch):
    monkeypatch.delenv("N2D_FACE_EMBEDDER", raising=False)
    assert fc.select_face_encoder(None, "anime") == "styleid"
    assert fc.select_face_encoder(None, "illustration") == "styleid"
    assert fc.select_face_encoder(None, "photo") == "arcface"
    # 无法判定 → 保守 arcface（不擅自换后端）
    assert fc.select_face_encoder(None, "unknown") == "arcface"
    assert fc.select_face_encoder(None, None) == "arcface"


def test_styleid_missing_weights_falls_back_to_arcface(monkeypatch):
    # 诚实铁律：要 styleid 但权重缺 → 回退 arcface 标 fallback，绝不静默用裸 CLIP
    monkeypatch.delenv("N2D_STYLEID_MODEL", raising=False)
    assert fc._load_styleid_embedder() is None


def test_styleid_model_ref_reads_project_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_STYLEID_MODEL", raising=False)
    (tmp_path / "_设置.md").write_text(
        "# 设置\n- 脸一致性机检后端：styleid\n- N2D_STYLEID_MODEL：kwanY/styleid\n",
        encoding="utf-8",
    )
    assert fc._styleid_model_from_settings(str(tmp_path)) == "kwanY/styleid"


def test_load_embedder_passes_project_styleid_ref(monkeypatch):
    sentinel = object()
    seen = {}

    def fake_styleid(model_ref=None):
        seen["model_ref"] = model_ref
        return sentinel

    monkeypatch.setattr(fc, "_load_styleid_embedder", fake_styleid)
    app, encoder = fc._load_embedder("styleid", styleid_model="kwanY/styleid")
    assert app is sentinel
    assert encoder == fc.ENCODER_STYLEID
    assert seen["model_ref"] == "kwanY/styleid"


def test_fidelity_excluded_only_on_explicit_false():
    mask = {"a.png": {"canonical_pass": False}, "b.png": {"canonical_pass": True}}
    assert fc.fidelity_excluded("a.png", mask) is True
    assert fc.fidelity_excluded("b.png", mask) is False
    assert fc.fidelity_excluded("missing.png", mask) is False  # 未判定 → 不臆造剔除
    assert fc.fidelity_excluded("a.png", {}) is False


def test_load_fidelity_mask_missing_file(tmp_path):
    assert fc._load_fidelity_mask(str(tmp_path), "第1集") == {}


def test_load_fidelity_mask_reads_shot_canonical(tmp_path):
    import json
    import os
    d = tmp_path / "生产数据"
    d.mkdir()
    (d / "vlm_canonical_第1集.json").write_text(
        json.dumps({"shot_canonical": {"镜头01.png": {"canonical_pass": False}}}),
        encoding="utf-8")
    mask = fc._load_fidelity_mask(str(tmp_path), "第1集")
    assert mask["镜头01.png"]["canonical_pass"] is False


def test_face_unverifiable_threshold():
    # 远景人小：最大脸短边占比低于阈值 → 身份不可辨。
    assert fc.face_unverifiable(0.02) is True
    assert fc.face_unverifiable(0.044) is True
    # 脸够大（近景/中景）→ 可核验。
    assert fc.face_unverifiable(0.05) is False
    assert fc.face_unverifiable(0.20) is False
    # 显式阈值可调（与 env N2D_FAR_SHOT_FACE_MIN_RATIO 同义）。
    assert fc.face_unverifiable(0.08, min_ratio=0.10) is True
    assert fc.face_unverifiable(0.12, min_ratio=0.10) is False


def test_arbiter_resolve_breaks_warn_band():
    # 🟡 边界带：DreamSim sim≥地板 → 判同人(ok)
    assert fc.arbiter_resolve("warn", 0.90, 0.80) == "ok"
    # sim < 地板−margin → 判异人(block)
    assert fc.arbiter_resolve("warn", 0.50, 0.80, margin=0.06) == "block"
    # 带内（地板−margin ≤ sim < 地板）→ 维持 warn 交人判
    assert fc.arbiter_resolve("warn", 0.78, 0.80, margin=0.06) == "warn"


def test_arbiter_resolve_only_acts_on_warn_and_needs_data():
    assert fc.arbiter_resolve("block", 0.99, 0.80) == "block"   # 不动 block
    assert fc.arbiter_resolve("ok", 0.10, 0.80) == "ok"         # 不动 ok
    assert fc.arbiter_resolve("warn", None, 0.80) == "warn"     # 缺 sim → 原样
    assert fc.arbiter_resolve("warn", 0.9, None) == "warn"      # 缺地板 → 原样


def test_dreamsim_arbiter_off_by_default(monkeypatch):
    monkeypatch.delenv("N2D_DREAMSIM_ARBITER", raising=False)
    assert fc._load_dreamsim() is None


# ── faceless 像素核验器 verify_faceless（无 insightface 时优雅降级） ──
def test_verify_faceless_unavailable_or_structure(tmp_path):
    import face_consistency as fc
    # 不存在的图：available 取决于是否装 insightface；verdict 必为 unavailable（读不到/无检测器），绝不臆造 ok/block
    res = fc.verify_faceless(str(tmp_path / "nope.png"))
    assert res["verdict"] in ("unavailable",)
    assert set(("available", "clear_faces", "max_ratio", "verdict")) <= set(res)
