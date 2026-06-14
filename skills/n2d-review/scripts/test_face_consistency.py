"""face_consistency 纯数学单测（无需 insightface/GPU）。
cd skills/n2d-review/scripts && python -m pytest test_face_consistency.py
"""
import math
import os

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


def test_calibrate_floor_takes_min():
    assert fc.calibrate_floor([0.9, 0.7, 0.82]) == 0.7


def test_calibrate_floor_fallback_when_single():
    # 单张定妆（无内部对）→ 回退保守同人下限
    assert fc.calibrate_floor([]) == 0.50
    assert fc.calibrate_floor([], fallback=0.55) == 0.55


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
    assert sorted(sets["沈念_常态"]) == ["主", "侧"]


def test_severity_order():
    assert fc._sev("block") > fc._sev("warn") > fc._sev("ok") > fc._sev("noface")


def test_anchor_verdict():
    assert fc.anchor_verdict(0, 0.0) == "block"                  # 锚点没脸
    assert fc.anchor_verdict(2, 0.3) == "block"                  # 多张脸
    assert fc.anchor_verdict(1, 0.02, min_ratio=0.06) == "warn"  # 脸太小
    assert fc.anchor_verdict(1, 0.20, min_ratio=0.06) == "ok"    # 单张够大正脸
    assert fc.anchor_verdict(1, 0.06, min_ratio=0.06) == "ok"    # 等于下限放行


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
    assert missing["verdict"] == "block"
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


def test_detect_face_swaps_empty_or_no_chars():
    import face_consistency as fc
    assert fc.detect_face_swaps([], {"沈念": [1.0, 0.0]})["assignments"] == []
    assert fc.detect_face_swaps([[1.0, 0.0]], {})["assignments"] == []
