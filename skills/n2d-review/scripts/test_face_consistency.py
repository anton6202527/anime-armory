"""face_consistency 纯数学单测（无需 insightface/GPU）。
cd skills/n2d-review/scripts && python -m pytest test_face_consistency.py
"""
import math
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
    assert not fc.is_character_asset("灵药谷山洞")   # 场景
    assert not fc.is_character_asset("淡青系统符纹光幕")  # 特效
    assert not fc.is_character_asset("豆油灯")        # 道具(灯)
    assert not fc.is_character_asset("未来神界主桌剪影")  # 剪影


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
    assert image_mod is not None, "本仓约定 Pillow 可用"

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
