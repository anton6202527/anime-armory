"""从本目录跑：cd skills/n2d-image/scripts && python -m pytest test_asset_impact.py"""
from asset_impact import (normalize, core, ref_tokens, parse_shots,
                          shot_references, shot_key)


def test_normalize_strips_dir_ext_prefix():
    assert normalize("出图/共享/图片/定妆_沈念_侧.png") == "沈念_侧"
    assert normalize("定妆_沈念") == "沈念"
    assert normalize("沈念") == "沈念"


def test_core_drops_view_suffix_keeps_state():
    assert core("定妆_沈念_侧.png") == "沈念"
    assert core("沈念_半身") == "沈念"
    assert core("沈念_觉醒_半身") == "沈念_觉醒"   # 状态保留，仅去视图后缀
    assert core("冷宫寝殿") == "冷宫寝殿"


def test_ref_tokens_splits_fullwidth():
    assert ref_tokens("参考图：沈念、柳娘子、冷宫寝殿") == ["沈念", "柳娘子", "冷宫寝殿"]


SAMPLE = """## 镜头 1（冷开场）🔑关键镜
目标：`出图/第1集/图片/镜头1_赐死冷开场.png`
参考图：沈念、柳娘子、冷宫寝殿、赐死托盘
- [ ] 脸未漂移（对照 定妆_沈念.png）

## 镜头 2（沈念惊醒）
目标：`出图/第1集/图片/镜头2_沈念惊醒.png`
参考图：沈念、冷宫寝殿
"""


def test_parse_shots_extracts_target_and_refline():
    shots = parse_shots(SAMPLE)
    assert len(shots) == 2
    assert shots[0]["target"] == "出图/第1集/图片/镜头1_赐死冷开场.png"
    assert "柳娘子" in ref_tokens(shots[0]["refline"])


def test_shot_references_matches_via_refline():
    shots = parse_shots(SAMPLE)
    assert shot_references(shots[0], {"柳娘子"}) is True       # 镜头1 引用柳娘子
    assert shot_references(shots[1], {"柳娘子"}) is False      # 镜头2 不引用
    assert shot_references(shots[1], {"沈念"}) is True


def test_shot_references_view_suffix_normalized():
    shots = parse_shots(SAMPLE)
    # 用户传 定妆_沈念_侧 → 核心键沈念 → 仍命中（参考图里只写"沈念"）
    assert shot_references(shots[0], {core("定妆_沈念_侧.png")}) is True


# ② 看花胖子式 schema：## Clip N · 镜N，**参考图**：`定妆_x.png`，无目标行
SAMPLE2 = """## Clip 1 · 镜1（ECU / 3.872s）系统主观·冷开场 🔑
**正向 prompt**
```text
极特写主观镜头…
```
**参考图**：`定妆_淡青系统符纹光幕.png`（VFX锚，强度 ~0.8）。**清空人物参考。**

## Clip 11 · 镜9A（LS / 5.0s）回忆·卑微开局
**参考图**：`定妆_王敦.png`、`定妆_山洞.png`
"""


def test_shot_key_derives_clip_and_shot():
    assert shot_key("Clip 1 · 镜1（ECU）") == "Clip_01"
    assert shot_key("Clip 11 · 镜9A") == "Clip_11"
    assert shot_key("镜头 3（铜镜）") == "镜头3"
    assert shot_key("统一参数与锚点句速查") is None


def test_kanhua_schema_prefixed_refs_match():
    shots = parse_shots(SAMPLE2)
    assert shot_references(shots[0], {"淡青系统符纹光幕"}) is True   # 带前缀写法命中
    assert shot_references(shots[1], {"王敦"}) is True
    assert shot_references(shots[0], {"王敦"}) is False             # 不串台


# M8：`定妆_<键>` 前缀匹配必须有边界，短键不得误伤长名
def test_prefixed_match_requires_boundary_no_false_positive():
    shots = parse_shots(SAMPLE)   # 含 `定妆_沈念.png`
    # `沈` 是 `沈念` 的前缀，但 `定妆_沈` 不该命中 `定妆_沈念.png`
    assert shot_references(shots[0], {"沈"}) is False
    # 完整核心键仍命中
    assert shot_references(shots[0], {"沈念"}) is True


def test_prefixed_match_scene_prefix_no_false_positive():
    s = parse_shots("## Clip 2 · 镜2\n**参考图**：`定妆_冷宫寝殿.png`\n")
    assert shot_references(s[0], {"冷宫"}) is False        # 不误伤 冷宫寝殿
    assert shot_references(s[0], {"冷宫寝殿"}) is True


def test_prefixed_match_view_suffix_still_matches():
    s = parse_shots("## Clip 3 · 镜3\n正文出现 定妆_沈念_侧.png 引用\n")
    assert shot_references(s[0], {"沈念"}) is True         # 视图后缀仍算同一资产


def _impact_project(tmp_path):
    import os
    root = tmp_path / "制漫剧" / "剧"
    pd = root / "出图" / "第1集" / "prompt"
    pd.mkdir(parents=True)
    (root / "出图" / "第1集" / "图片").mkdir(parents=True)
    (pd / "01_分镜出图.md").write_text(
        "## 镜头 1（冷开场）\n目标：出图/第1集/图片/镜头1.png\n参考图：沈念、冷宫寝殿\n正文\n"
        "## 镜头 2（反打）\n目标：出图/第1集/图片/镜头2.png\n参考图：沈念\n正文\n",
        encoding="utf-8",
    )
    (root / "出图" / "第1集" / "图片" / "镜头1.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # 镜头1 已出图
    return root


def test_build_rerun_plan_chains_and_minimal_scope(tmp_path):
    from asset_impact import scan, build_rerun_plan
    root = _impact_project(tmp_path)
    keys, hits = scan(str(root), ["沈念"])
    plan = build_rerun_plan(str(root), keys, hits)

    assert plan["kind"] == "n2d_asset_rerun_plan"
    assert plan["affected_episodes"] == ["第1集"]
    assert plan["rerun_count"] == 1 and plan["pending_count"] == 1
    skills = [s["skill"] for s in plan["steps"]]
    assert skills == ["n2d-image", "n2d-identity", "n2d-video", "n2d-compose", "n2d-batch"]
    batch_cmd = plan["steps"][-1]["commands"][0]
    assert "--rerun-from image" in batch_cmd
    assert "镜头1.png" in batch_cmd          # 只含已出图镜头（最小范围）
    assert "镜头2" not in batch_cmd          # 未出图镜头不进重跑


def test_rerun_plan_empty_when_nothing_generated(tmp_path):
    import os
    from asset_impact import scan, build_rerun_plan
    root = tmp_path / "制漫剧" / "剧"
    pd = root / "出图" / "第1集" / "prompt"
    pd.mkdir(parents=True)
    (pd / "01_分镜出图.md").write_text(
        "## 镜头 1\n目标：出图/第1集/图片/镜头1.png\n参考图：沈念\n", encoding="utf-8")
    keys, hits = scan(str(root), ["沈念"])  # 无 PNG → 全 pending
    plan = build_rerun_plan(str(root), keys, hits)
    assert plan["rerun_count"] == 0
    assert plan["steps"] == []
    assert plan["warnings"]
