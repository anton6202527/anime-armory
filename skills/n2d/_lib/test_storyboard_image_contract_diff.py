#!/usr/bin/env python3
"""Tests for diff_storyboard_image_contract — script(阶段2分镜)→出图 接缝契约继承 diff。"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import n2d_contract_diff as D  # noqa: E402


IMG_00 = """# 出图总览

## 本集视觉一致性契约
- 色调基线：冷灰、土褐、墨黑。
- 光位锚：{"LOC_01": "阴天冷色漫射光，主光从画面左上后方进入。"}
- 轴线：{"LOC_01": "巨岩虎妖为纵深轴；姜月初画左、裴长青画右。"}
- 状态演进：以 storyboard 的分段状态为上游契约；逐镜 prompt 只写本镜已发生状态锁。
- 景别阶梯：['85mm ECU', '35mm ELS']
"""


def _by_field(results):
    return {r["field"]: r for r in results}


def test_verbatim_inheritance_passes():
    vc = {
        "色调基线": "冷灰、土褐、墨黑。",
        "场景光位锚": {"LOC_01": "阴天冷色漫射光，主光从画面左上后方进入。"},
        "场景轴线视线": {"LOC_01": "巨岩虎妖为纵深轴；姜月初画左、裴长青画右。"},
        "角色状态演进": {"CHAR_01": "残损→沾血→暗红血迹。"},
        "景别阶梯": ["85mm ECU", "35mm ELS"],
    }
    res = _by_field(D.diff_storyboard_image_contract(vc, IMG_00))
    assert res["场景光位锚"]["status"] in {"pass", "pass_superset"}
    assert res["场景光位锚"]["seam_block"] is False
    assert res["场景轴线视线"]["status"] in {"pass", "pass_superset"}
    assert res["场景轴线视线"]["seam_block"] is False


def test_light_axis_rewrite_seam_blocks():
    vc = {
        "场景光位锚": {"LOC_01": "主光从画面右下前方进入（改写）"},
        "场景轴线视线": {"LOC_01": "姜月初画右、裴长青画左（越轴改写）"},
    }
    res = _by_field(D.diff_storyboard_image_contract(vc, IMG_00))
    assert res["场景光位锚"]["status"] == "block_drift"
    assert res["场景光位锚"]["seam_block"] is True
    assert res["场景轴线视线"]["seam_block"] is True


def test_non_light_axis_drift_not_seam_block():
    # 色调基线漂移只 warn，不 seam_block（不焊进首帧像素几何/光照的字段）。
    vc = {"色调基线": "暖金主调（与出图不一致）"}
    res = _by_field(D.diff_storyboard_image_contract(vc, IMG_00))
    assert res["色调基线"]["status"] in {"warn_drift", "block_drift"}
    assert res["色调基线"]["seam_block"] is False


def test_missing_storyboard_seed_is_upstream_warn_not_block():
    # storyboard 侧种子缺失=上游问题（check_storyboard_visual_contract 负责），不 seam_block。
    res = _by_field(D.diff_storyboard_image_contract({}, IMG_00))
    assert res["场景光位锚"]["status"] == "upstream_missing"
    assert res["场景光位锚"]["seam_block"] is False


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
