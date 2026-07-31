#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reference_planner 单测。从本目录跑：
    cd skills/ad/ad-image/scripts && python3 -m pytest test_reference_planner.py
覆盖：产品镜单参考 → block / 大变化量镜 → 参考不足告警 + 升档建议 / 未知后端保守回退 /
缺 storyboard·registry → available=false 降级不抛异常 / 参考预算封顶 /
--strict 退出码语义 / 输出 JSON schema 形状（findings 用 `msg`）/ --write 原子落盘。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_planner as rp  # noqa: E402


# ── 夹具：最小广告项目（拍广告不拆集，粒度是镜头） ──────────────────────────────

def _project(tmp_path, *, shots=None, registry=None, settings=None, name="广告项目"):
    root = tmp_path / name
    (root / "脚本").mkdir(parents=True)
    if shots is not None:
        (root / "脚本" / "storyboard.json").write_text(
            json.dumps({"aspect": "9:16", "shots": shots}, ensure_ascii=False), encoding="utf-8")
    if registry is not None:
        (root / "设定库").mkdir(parents=True, exist_ok=True)
        (root / "设定库" / "asset_registry.json").write_text(
            json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    # 后端必须显式声明，否则落到「未登记后端」保守档（见 test_unknown_backend_*）。
    lines = ["# 设置", ""] + [f"- {k}：{v}" for k, v in (settings or {}).items()]
    (root / "_设置.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _touch(root, *rels):
    for rel in rels:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG fake")


OPENAI = {"生图模型": "GPT Image 2", "生图渠道": "Codex CLI"}  # ad 线默认路线：多参考可用·无主体库


def _codes(report, severity=None):
    return {f["code"] for f in report["findings"] if severity is None or f["severity"] == severity}


def _find(report, code, shot=None):
    return [f for f in report["findings"]
            if f["code"] == code and (shot is None or f.get("shot") == shot)]


def _asset_plan(report, shot_label, asset_id):
    shot = next(s for s in report["shots"] if s["shot"] == shot_label)
    return next(p for p in shot["assets"] if p["asset_id"] == asset_id)


# ── 纯函数：变化量抽取 / 计分 / 阈值 ────────────────────────────────────────────

def test_variation_deltas_from_shot_text():
    shot = {"scene": "货架旁", "prompt": "产品瓶身特写，俯视角度，逆光，手持倾倒", "shot_size": "特写"}
    deltas = rp.variation_deltas(shot, rp.adapter.ASSET_KIND_PRODUCT, multi_asset=False)
    assert set(deltas) == {"closeup", "extreme_angle", "lighting_change", "action_motion"}


def test_strong_emotion_only_counts_for_characters():
    shot = {"prompt": "人物大笑"}
    assert "strong_emotion" in rp.variation_deltas(shot, rp.adapter.ASSET_KIND_CHARACTER, False)
    # 产品不会「大笑」——表情项对产品镜无意义，不得计入变化量。
    assert "strong_emotion" not in rp.variation_deltas(shot, rp.adapter.ASSET_KIND_PRODUCT, False)


def test_text_surface_only_counts_for_product_and_brand():
    shot = {"prompt": "包装文字与 logo 清晰露出"}
    for kind in (rp.adapter.ASSET_KIND_PRODUCT, rp.adapter.ASSET_KIND_BRAND):
        assert "text_surface" in rp.variation_deltas(shot, kind, False)
    assert "text_surface" not in rp.variation_deltas(shot, rp.adapter.ASSET_KIND_CHARACTER, False)


def test_multi_asset_frame_delta_is_driven_by_caller():
    assert rp.variation_deltas({"prompt": "空"}, rp.adapter.ASSET_KIND_PROP, True) == ["multi_asset_frame"]
    assert rp.variation_deltas({"prompt": "空"}, rp.adapter.ASSET_KIND_PROP, False) == []


def test_delta_score_amplifies_product_and_brand():
    deltas = ["closeup"]  # 权重 2.0
    assert rp.delta_score(deltas, rp.adapter.ASSET_KIND_CHARACTER) == 2.0
    # 广告特有加权：产品漂了整片报废 → 同样的变化量算得更重。
    assert rp.delta_score(deltas, rp.adapter.ASSET_KIND_PRODUCT) == 3.0
    assert rp.delta_score(deltas, rp.adapter.ASSET_KIND_BRAND) == 2.0 * rp.PRODUCT_DELTA_MULTIPLIER
    assert rp.delta_score(["nonexistent_delta"], rp.adapter.ASSET_KIND_CHARACTER) == 0.0


def test_is_big_delta_uses_lower_threshold_for_product():
    # 分数 2.0：产品已算大变化（阈 2.0），角色还不算（阈 3.0）。
    assert rp.is_big_delta(2.0, rp.adapter.ASSET_KIND_PRODUCT) is True
    assert rp.is_big_delta(2.0, rp.adapter.ASSET_KIND_CHARACTER) is False
    assert rp.is_big_delta(3.0, rp.adapter.ASSET_KIND_CHARACTER) is True


def test_min_references_product_floor_is_higher_than_character():
    assert rp.min_references_for(rp.adapter.ASSET_KIND_PRODUCT, False) == 2
    assert rp.min_references_for(rp.adapter.ASSET_KIND_PRODUCT, True) == 3
    assert rp.min_references_for(rp.adapter.ASSET_KIND_CHARACTER, False) == 1
    assert rp.min_references_for(rp.adapter.ASSET_KIND_CHARACTER, True) == 2


def test_recommended_tier_uses_real_adapter_ladder_ids():
    # 回归：处方档位必须是 adapter 梯子上真实存在的四档之一（不得引用不存在的档名常量）。
    for kind in (rp.adapter.ASSET_KIND_PRODUCT, rp.adapter.ASSET_KIND_BRAND,
                 rp.adapter.ASSET_KIND_CHARACTER, rp.adapter.ASSET_KIND_LOCATION,
                 rp.adapter.ASSET_KIND_UNKNOWN):
        for big in (False, True):
            assert rp.recommended_tier_for(kind, big) in rp.adapter.TIER_LADDER

    assert rp.recommended_tier_for(rp.adapter.ASSET_KIND_PRODUCT, True) == rp.adapter.TIER_SUBJECT_LIBRARY
    assert rp.recommended_tier_for(rp.adapter.ASSET_KIND_PRODUCT, False) == rp.adapter.TIER_DIRECTED_REFERENCE
    assert rp.recommended_tier_for(rp.adapter.ASSET_KIND_CHARACTER, True) == rp.adapter.TIER_DIRECTED_REFERENCE
    assert rp.recommended_tier_for(rp.adapter.ASSET_KIND_CHARACTER, False) == rp.adapter.TIER_SHARED_KIT
    # 产品比角色更激进：同样「不大变化」的镜，产品就已经要求逐镜精选多参考。
    assert (rp.adapter.tier_rank(rp.recommended_tier_for(rp.adapter.ASSET_KIND_PRODUCT, False))
            > rp.adapter.tier_rank(rp.recommended_tier_for(rp.adapter.ASSET_KIND_CHARACTER, False)))


def test_plan_controls_reports_backend_capability_state_honestly():
    openai = rp.adapter.profile_for("GPT Image 2", "Codex CLI")
    controls = rp.plan_controls(openai, ["closeup", "text_surface"], rp.adapter.ASSET_KIND_PRODUCT)
    by_type = {c["type"]: c for c in controls}
    assert set(by_type) == {"controlnet_structure", "logo_protect_mask"}
    assert by_type["controlnet_structure"]["state"] == rp.adapter.CAP_UNKNOWN   # 未确证 → 如实标未知
    assert by_type["logo_protect_mask"]["state"] == rp.adapter.CAP_AVAILABLE
    # 控制网/保护区只对产品/品牌开；角色镜不提。
    assert rp.plan_controls(openai, ["closeup", "text_surface"], rp.adapter.ASSET_KIND_CHARACTER) == []


def test_shot_asset_ids_orders_product_and_brand_first():
    shot = {"assets": {"CHAR_host": True, "LOC_kitchen": True,
                       "BRAND_QINGLU": True, "PROD_BOTTLE": True, "PROP_cup": True}}
    # 顺序即参考预算优先级：预算紧时先保产品/品牌。
    assert rp.shot_asset_ids(shot) == ["PROD_BOTTLE", "BRAND_QINGLU", "CHAR_host", "LOC_kitchen", "PROP_cup"]


def test_shot_asset_ids_ignores_falsy_assets_and_plain_words():
    assert rp.shot_asset_ids({"assets": {"PROD_BOTTLE": False}, "prompt": "product and brand words"}) == []


# ── 复现间隔（gap）因子：纯函数 ─────────────────────────────────────────────────

def test_reappearance_gaps_counts_shots_since_last_seen():
    gaps = rp.reappearance_gaps([
        ("镜头1", ["PROD_A", "CHAR_B"]),
        ("镜头2", []),
        ("镜头3", ["CHAR_B"]),
        ("镜头4", []),
        ("镜头5", ["PROD_A", "CHAR_B"]),
    ])
    # 首次出现 → None（不存在「复现」）；之后 = 距上次出现的镜数。
    assert gaps["镜头1"] == {"PROD_A": None, "CHAR_B": None}
    assert gaps["镜头3"] == {"CHAR_B": 2}
    assert gaps["镜头5"] == {"PROD_A": 4, "CHAR_B": 2}


def test_is_long_gap_product_threshold_is_stricter_and_first_seen_exempt():
    # 产品/品牌阈 3、一般资产阈 4；首次出现（None）永远豁免。
    assert rp.is_long_gap(3, rp.adapter.ASSET_KIND_PRODUCT) is True
    assert rp.is_long_gap(3, rp.adapter.ASSET_KIND_BRAND) is True
    assert rp.is_long_gap(3, rp.adapter.ASSET_KIND_CHARACTER) is False
    assert rp.is_long_gap(4, rp.adapter.ASSET_KIND_CHARACTER) is True
    assert rp.is_long_gap(2, rp.adapter.ASSET_KIND_PRODUCT) is False
    assert rp.is_long_gap(None, rp.adapter.ASSET_KIND_PRODUCT) is False


def test_tier_one_up_climbs_ladder_but_never_into_lora():
    assert rp.tier_one_up(rp.adapter.TIER_SHARED_KIT) == rp.adapter.TIER_DIRECTED_REFERENCE
    assert rp.tier_one_up(rp.adapter.TIER_DIRECTED_REFERENCE) == rp.adapter.TIER_SUBJECT_LIBRARY
    # +LoRA 是长线代言人训练决策，不因镜序间隔自动建议。
    assert rp.tier_one_up(rp.adapter.TIER_SUBJECT_LIBRARY) == rp.adapter.TIER_SUBJECT_LIBRARY
    assert rp.tier_one_up(rp.adapter.TIER_LORA) == rp.adapter.TIER_LORA
    assert rp.tier_one_up("no_such_tier") == "no_such_tier"


# ── 复现间隔（gap）因子：集成 ───────────────────────────────────────────────────

def _gap_project(tmp_path, *, gap_shots=2, refs_count=3):
    """产品在 镜头1 出现、隔 gap_shots 个空镜后再登场的项目。"""
    shots = [{"shot_id": "镜头1", "scene": "中景 产品摆在桌面", "assets": {"PROD_BOTTLE": True}}]
    for i in range(gap_shots):
        shots.append({"shot_id": f"镜头{i + 2}", "scene": "山谷晨雾空镜"})
    shots.append({"shot_id": f"镜头{gap_shots + 2}", "scene": "中景 产品再登场",
                  "assets": {"PROD_BOTTLE": True}})
    refs = [f"设定库/r{i}.png" for i in range(refs_count)]
    root = _project(tmp_path, settings=OPENAI, shots=shots,
                    registry={"products": [{"id": "PROD_BOTTLE", "reference_images": refs}]})
    _touch(root, *refs)
    return root, shots[-1]["shot_id"]


def test_long_gap_reappearance_lifts_floor_and_pins_earliest_anchor(tmp_path):
    root, last = _gap_project(tmp_path, gap_shots=2)  # gap=3 ≥ 产品阈 3
    report = rp.build_plan(root)

    hits = _find(report, "long_gap_reappearance", shot=last)
    assert len(hits) == 1 and hits[0]["severity"] == "warn"  # 产品/品牌 → warn（advisory）
    assert hits[0]["gap"] == 3
    assert "最早定妆锚" in hits[0]["msg"] and "设定库/r0.png" in hits[0]["msg"]

    plan = _asset_plan(report, last, "PROD_BOTTLE")
    # 参考下限 +1（产品地板 2 → 3）；建议档位提一档（指定参考图 → 后端主体库）。
    assert plan["min_references"] == 3
    assert plan["recommended_tier"] == rp.adapter.TIER_SUBJECT_LIBRARY
    assert plan["reappearance"] == {"gap": 3, "threshold": 3, "long_gap": True,
                                    "anchor_reference": "设定库/r0.png"}
    # 首次出现的 镜头1 豁免：无 gap finding，reappearance 如实记 None。
    assert _find(report, "long_gap_reappearance", shot="镜头1") == []
    first_plan = _asset_plan(report, "镜头1", "PROD_BOTTLE")
    assert first_plan["reappearance"]["gap"] is None
    assert first_plan["reappearance"]["long_gap"] is False
    # 全 advisory：gap 因子绝不产 block。
    assert all(f["severity"] != "block" for f in _find(report, "long_gap_reappearance"))


def test_short_gap_reappearance_is_exempt(tmp_path):
    root, last = _gap_project(tmp_path, gap_shots=1)  # gap=2 < 产品阈 3 → 豁免
    report = rp.build_plan(root)
    assert "long_gap_reappearance" not in _codes(report)
    plan = _asset_plan(report, last, "PROD_BOTTLE")
    assert plan["min_references"] == 2 and plan["reappearance"]["long_gap"] is False


def test_long_gap_on_character_is_info_and_uses_looser_threshold(tmp_path):
    shots = [{"shot_id": "镜头1", "scene": "代言人入场", "assets": {"CHAR_host": True}}]
    shots += [{"shot_id": f"镜头{i + 2}", "scene": "空镜"} for i in range(3)]
    shots.append({"shot_id": "镜头5", "scene": "代言人回归", "assets": {"CHAR_host": True}})
    root = _project(tmp_path, settings=OPENAI, shots=shots,
                    registry={"characters": [{"id": "CHAR_host",
                                              "reference_images": ["设定库/h1.png", "设定库/h2.png"]}]})
    _touch(root, "设定库/h1.png", "设定库/h2.png")
    report = rp.build_plan(root)
    hits = _find(report, "long_gap_reappearance", shot="镜头5")
    assert len(hits) == 1 and hits[0]["severity"] == "info"  # 非产品 → info
    assert hits[0]["gap"] == 4  # 一般资产阈 4，恰好触发


# ── 升档可达路由建议：清单来自适配层能力表 ──────────────────────────────────────

def test_route_suggestions_lists_backends_reaching_tier():
    reached, hint = rp.route_suggestions(rp.adapter.TIER_SUBJECT_LIBRARY, rp.adapter.ASSET_KIND_PRODUCT)
    assert {r["backend"] for r in reached} == {"seedream", "kling"}
    assert "Seedream 4.5" in hint and "Kling Image 3.0" in hint
    assert "签核" in hint and "不自动改设置" in hint  # advisory：建议切换，不代改


def test_route_suggestions_with_no_reachable_backend_says_so_honestly():
    # 现表无后端有 LoRA 挂载点 → 空清单 + 建议人工降低期望或补定妆参考。
    reached, hint = rp.route_suggestions(rp.adapter.TIER_LORA, rp.adapter.ASSET_KIND_CHARACTER)
    assert reached == []
    assert "无任何后端够得着" in hint and "降低期望" in hint


def test_tier_below_recommended_finding_carries_reachable_backends(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "产品包装特写，俯视，logo 露出",
                "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": [
            "设定库/a.png", "设定库/b.png", "设定库/c.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png", "设定库/c.png")
    report = rp.build_plan(root)

    hits = _find(report, "tier_below_recommended", shot="镜头1")
    assert len(hits) == 1
    # warn 里列出「哪些后端够得着建议档」（模型+渠道），并注明切换属建议。
    assert hits[0]["reachable_backends"] == ["seedream", "kling"]
    assert "Seedream 4.5" in hits[0]["msg"] and "Kling Image 3.0" in hits[0]["msg"]
    # plan JSON 同步落清单（供机器消费）。
    plan = _asset_plan(report, "镜头1", "PROD_BOTTLE")
    assert [r["backend"] for r in plan["tier_route_suggestions"]] == ["seedream", "kling"]
    assert all(r["label"] for r in plan["tier_route_suggestions"])


def test_no_tier_gap_means_no_route_suggestions(tmp_path):
    root = _project(
        tmp_path, settings={"生图模型": "Seedream 4.5", "生图渠道": "BytePlus ModelArk"},
        shots=[{"shot_id": "镜头1", "scene": "产品包装特写，俯视", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": [
            "设定库/a.png", "设定库/b.png", "设定库/c.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png", "设定库/c.png")
    report = rp.build_plan(root)
    plan = _asset_plan(report, "镜头1", "PROD_BOTTLE")
    assert plan["tier_gap"] is False and plan["tier_route_suggestions"] == []


# ── 参考预算分配 ────────────────────────────────────────────────────────────────

def test_allocate_references_gives_each_asset_one_first_then_round_robins():
    alloc = rp.allocate_references([("PROD_A", ["a1", "a2", "a3"]), ("CHAR_B", ["b1", "b2"])], 4)
    # 先每个资产保底一张（a1、b1），再轮转补足到上限。
    assert [r["path"] for r in alloc["selected"]] == ["a1", "b1", "a2", "b2"]
    assert alloc["dropped"] == [{"asset_id": "PROD_A", "path": "a3"}]
    assert alloc["requested"] == 5 and alloc["selected_count"] == 4


def test_allocate_references_protects_product_when_budget_is_tight():
    # 上限 1 且产品排最前 → 保底给产品，角色参考显式记进 dropped（不静默吞）。
    alloc = rp.allocate_references([("PROD_A", ["a1", "a2"]), ("CHAR_B", ["b1"])], 1)
    assert alloc["selected"] == [{"asset_id": "PROD_A", "path": "a1"}]
    assert alloc["dropped"] == [{"asset_id": "PROD_A", "path": "a2"}, {"asset_id": "CHAR_B", "path": "b1"}]
    assert alloc["requested"] == 3 and alloc["limit"] == 1


def test_allocate_references_dedupes_shared_paths_and_handles_zero_limit():
    alloc = rp.allocate_references([("PROD_A", ["same.png"]), ("BRAND_B", ["same.png"])], 5)
    assert alloc["selected_count"] == 1
    assert rp.allocate_references([("PROD_A", ["a1"])], 0)["selected"] == []


# ── 产品镜单参考 = 最危险 → block ────────────────────────────────────────────────

def test_product_shot_with_single_reference_blocks(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品摆在桌面", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": ["设定库/bottle_front.png"]}]},
    )
    _touch(root, "设定库/bottle_front.png")
    report = rp.build_plan(root)

    hits = _find(report, "product_shot_single_reference", shot="镜头1")
    assert len(hits) == 1
    assert hits[0]["severity"] == "block"       # 结构化登记的产品 ID = 确定性缺口
    assert hits[0]["asset_id"] == "PROD_BOTTLE"
    assert "单张定妆照" in hits[0]["msg"]
    assert report["summary"]["block"] == 1

    plan = _asset_plan(report, "镜头1", "PROD_BOTTLE")
    assert plan["kind"] == "product"
    assert plan["reference_count"] == 1 and plan["min_references"] == 2


def test_product_shot_with_enough_references_has_no_reference_findings(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品摆在桌面", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": [
            "设定库/front.png", "设定库/side.png"]}]},
    )
    _touch(root, "设定库/front.png", "设定库/side.png")
    report = rp.build_plan(root)

    assert report["summary"]["block"] == 0
    assert "product_shot_single_reference" not in _codes(report)
    assert "reference_plan_underfed" not in _codes(report)
    plan = _asset_plan(report, "镜头1", "PROD_BOTTLE")
    assert plan["reference_count"] == 2 and plan["big_delta"] is False
    assert plan["achievable_tier"] == rp.adapter.TIER_DIRECTED_REFERENCE
    assert plan["tier_gap"] is False


def test_semantic_only_product_shot_downgrades_single_reference_to_warn(tmp_path):
    # 语义纳管（storyboard 忘写 PROD_*）属启发式判定 → 只 warn，不 block。
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "手机屏幕显示 App 界面", "assets": {"CHAR_user": True}}],
        registry={"characters": [{"id": "CHAR_user", "reference_images": ["设定库/user.png"]}]},
    )
    _touch(root, "设定库/user.png")
    report = rp.build_plan(root)

    shot = report["shots"][0]
    assert shot["is_product_shot"] is True and shot["product_semantic_only"] is True
    hits = _find(report, "product_shot_missing_asset_id", shot="镜头1")
    assert len(hits) == 1 and hits[0]["severity"] == "warn"
    assert report["summary"]["block"] == 0


def test_unregistered_product_asset_blocks_but_character_only_warns(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品与人",
                "assets": {"PROD_GHOST": True, "CHAR_GHOST": True}}],
        registry={"products": [{"id": "PROD_OTHER", "reference_images": ["设定库/o.png"]}]},
    )
    report = rp.build_plan(root)
    hits = {f["asset_id"]: f for f in _find(report, "registry_asset_missing")}
    assert hits["PROD_GHOST"]["severity"] == "block"
    assert hits["CHAR_GHOST"]["severity"] == "warn"


def test_registered_product_without_reference_images_blocks(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "name": "气泡水"}]},
    )
    report = rp.build_plan(root)
    hits = _find(report, "asset_reference_unregistered", shot="镜头1")
    assert len(hits) == 1 and hits[0]["severity"] == "block"
    assert "纯文生图" in hits[0]["msg"]


def test_registered_reference_file_missing_on_disk_warns(tmp_path):
    # 登记 ≠ 有图：磁盘上没落文件必须显性报，别以为能喂进去。
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": [
            "设定库/front.png", "设定库/side.png"]}]},
    )
    _touch(root, "设定库/front.png")  # side.png 故意不落盘
    report = rp.build_plan(root)

    hits = _find(report, "reference_file_missing", shot="镜头1")
    assert len(hits) == 1 and hits[0]["severity"] == "warn"
    assert "设定库/side.png" in hits[0]["msg"]
    refs = {r["path"]: r["exists"] for r in _asset_plan(report, "镜头1", "PROD_BOTTLE")["references"]}
    assert refs == {"设定库/front.png": True, "设定库/side.png": False}


# ── 大变化量镜 → 参考不足 / 升档建议 ────────────────────────────────────────────

def test_big_delta_character_shot_is_underfed_warn(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "代言人特写，仰视，换装出场",
                "assets": {"CHAR_host": True}}],
        registry={"characters": [{"id": "CHAR_host", "reference_images": ["设定库/host.png"]}]},
    )
    _touch(root, "设定库/host.png")
    report = rp.build_plan(root)

    plan = _asset_plan(report, "镜头1", "CHAR_host")
    assert set(plan["variation_delta"]) >= {"closeup", "extreme_angle", "outfit_or_packaging_change"}
    assert plan["delta_score"] == 6.0 and plan["big_delta"] is True
    assert plan["min_references"] == 2 and plan["reference_count"] == 1
    hits = _find(report, "reference_plan_underfed", shot="镜头1")
    assert len(hits) == 1 and hits[0]["severity"] == "warn"
    assert "confidence=low" in hits[0]["msg"]   # 启发式判定必须自陈脆弱
    assert report["summary"]["block"] == 0


def test_big_delta_product_shot_recommends_tier_upgrade_beyond_openai(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "产品包装特写，俯视，logo 露出",
                "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": [
            "设定库/a.png", "设定库/b.png", "设定库/c.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png", "设定库/c.png")
    report = rp.build_plan(root)

    plan = _asset_plan(report, "镜头1", "PROD_BOTTLE")
    assert plan["big_delta"] is True and plan["min_references"] == 3
    assert plan["recommended_tier"] == rp.adapter.TIER_SUBJECT_LIBRARY
    # GPT Image 2 无持久主体库 → 够不着建议档 → 产品镜升为 warn。
    assert plan["achievable_tier"] == rp.adapter.TIER_DIRECTED_REFERENCE
    assert plan["tier_gap"] is True
    hits = _find(report, "tier_below_recommended", shot="镜头1")
    assert len(hits) == 1 and hits[0]["severity"] == "warn"
    # 近景 + logo 露出 → 结构控制网 + logo 保护区两条处方。
    assert {c["type"] for c in plan["controls"]} == {"controlnet_structure", "logo_protect_mask"}


def test_tier_gap_on_non_product_is_only_info(tmp_path):
    root = _project(
        tmp_path, settings={"生图模型": "MyCustomDiffusion v9"},
        shots=[{"shot_id": "镜头1", "scene": "代言人特写，仰视，换装", "assets": {"CHAR_host": True}}],
        registry={"characters": [{"id": "CHAR_host", "reference_images": ["设定库/host.png"]}]},
    )
    _touch(root, "设定库/host.png")
    report = rp.build_plan(root)
    hits = _find(report, "tier_below_recommended", shot="镜头1")
    assert len(hits) == 1 and hits[0]["severity"] == "info"


def test_subject_library_backend_closes_the_tier_gap_for_product(tmp_path):
    root = _project(
        tmp_path, settings={"生图模型": "Seedream 4.5", "生图渠道": "BytePlus ModelArk"},
        shots=[{"shot_id": "镜头1", "scene": "产品包装特写，俯视", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": [
            "设定库/a.png", "设定库/b.png", "设定库/c.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png", "设定库/c.png")
    report = rp.build_plan(root)

    plan = _asset_plan(report, "镜头1", "PROD_BOTTLE")
    assert plan["achievable_tier"] == rp.adapter.TIER_SUBJECT_LIBRARY
    assert plan["tier_gap"] is False
    assert "tier_below_recommended" not in _codes(report)


# ── 未知后端：保守回退，不崩、不假装支持 ────────────────────────────────────────

def test_unknown_backend_degrades_conservatively(tmp_path):
    root = _project(
        tmp_path, settings={"生图模型": "MyCustomDiffusion v9", "生图渠道": "自建 runner"},
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": [
            "设定库/a.png", "设定库/b.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png")
    report = rp.build_plan(root)

    assert report["backend"]["known"] is False
    assert report["backend"]["reference_limit"] == 1
    hits = _find(report, "backend_unknown_capability")
    assert any(h["severity"] == "warn" and "未假装支持" in h["msg"] for h in hits)
    # 保守预算 1 → 第二张参考被显式丢弃并记账，不静默吞。
    assert report["shots"][0]["reference_budget"] == {
        "limit": 1, "requested": 2, "selected": 1,
        "dropped": [{"asset_id": "PROD_BOTTLE", "path": "设定库/b.png"}]}
    assert _find(report, "reference_budget_overflow", shot="镜头1")[0]["severity"] == "warn"
    # 预算封顶导致产品只剩单参考 → 仍然照实报 block（后端能力不是漂移的借口）。
    assert _find(report, "product_shot_single_reference", shot="镜头1")[0]["severity"] == "block"


def test_undeclared_backend_is_unknown_not_silently_openai(tmp_path):
    root = _project(tmp_path, settings={}, shots=[], registry={})
    report = rp.build_plan(root)
    assert report["backend"]["known"] is False
    assert report["inputs"]["settings"]["生图模型"] == ""


def test_consistency_setting_requiring_subject_library_warns_when_unsupported(tmp_path):
    root = _project(
        tmp_path, settings={"生图模型": "GPT Image 2", "一致性增强": "后端主体库"},
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": ["设定库/a.png", "设定库/b.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png")
    report = rp.build_plan(root)

    hits = _find(report, "consistency_setting_unsupported")
    assert len(hits) == 1 and hits[0]["severity"] == "warn"
    assert "别把设置当成已经锁住了产品身份" in hits[0]["msg"]


def test_consistency_setting_satisfied_by_backend_does_not_warn(tmp_path):
    root = _project(
        tmp_path, settings={"生图模型": "Kling Image 3.0", "一致性增强": "后端主体库"},
        shots=[], registry={"products": [{"id": "PROD_BOTTLE"}]},
    )
    assert "consistency_setting_unsupported" not in _codes(rp.build_plan(root))


# ── 缺料降级：available=false，不抛异常 ─────────────────────────────────────────

def test_missing_storyboard_and_registry_degrade_without_raising(tmp_path):
    root = _project(tmp_path, settings=OPENAI)  # 既无 storyboard 也无 registry
    report = rp.build_plan(root)

    assert report["inputs"]["storyboard"]["available"] is False
    assert report["inputs"]["asset_registry"]["available"] is False
    assert report["inputs"]["asset_registry"]["fallback_order"] == [
        "设定库/asset_registry.json", "出图/共享/asset_registry.json"]
    assert {"storyboard_unavailable", "registry_unavailable"} <= _codes(report, "warn")
    assert report["shots"] == [] and report["summary"]["block"] == 0


def test_nonexistent_project_root_does_not_raise_and_exits_zero(tmp_path, capsys):
    missing = tmp_path / "根本没有这个项目"
    report = rp.build_plan(missing)
    assert report["kind"] == "ad_reference_plan"
    assert report["summary"]["shots"] == 0
    # 已验证过的现状：不存在的根 → rc=0（advisory，不许回归成崩溃）。
    assert rp.main([str(missing)]) == 0
    capsys.readouterr()


def test_unparsable_storyboard_degrades_instead_of_raising(tmp_path):
    root = _project(tmp_path, settings=OPENAI, shots=[])
    (root / "脚本" / "storyboard.json").write_text("{ 这不是 JSON", encoding="utf-8")
    report = rp.build_plan(root)
    assert report["inputs"]["storyboard"]["available"] is False
    assert "storyboard_unavailable" in _codes(report, "warn")


def test_missing_registry_does_not_spam_per_asset_findings(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品",
                "assets": {"PROD_A": True, "PROD_B": True, "CHAR_C": True}}],
    )
    report = rp.build_plan(root)
    # 缺 registry 已在顶层降级一次，不逐资产刷屏，也不误报「登记了却没图」。
    assert "registry_unavailable" in _codes(report, "warn")
    assert "asset_reference_unregistered" not in _codes(report)
    assert "registry_asset_missing" not in _codes(report)
    assert report["summary"]["block"] == 0


def test_registry_fallback_prefers_设定库_over_出图共享(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": ["设定库/a.png", "设定库/b.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png")
    shared = root / "出图" / "共享" / "asset_registry.json"
    shared.parent.mkdir(parents=True)
    shared.write_text(json.dumps({"products": [{"id": "PROD_BOTTLE", "reference_images": ["出图/共享/stale.png"]}]},
                                 ensure_ascii=False), encoding="utf-8")
    report = rp.build_plan(root)
    assert report["inputs"]["asset_registry"]["path"] == "设定库/asset_registry.json"
    assert report["shots"][0]["references"] == ["设定库/a.png", "设定库/b.png"]


def test_registry_falls_back_to_出图共享_when_设定库_absent(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
    )
    shared = root / "出图" / "共享" / "asset_registry.json"
    shared.parent.mkdir(parents=True)
    shared.write_text(json.dumps({"products": [{"id": "PROD_BOTTLE", "reference_images": ["出图/共享/a.png"]}]},
                                 ensure_ascii=False), encoding="utf-8")
    report = rp.build_plan(root)
    assert report["inputs"]["asset_registry"]["available"] is True
    assert report["inputs"]["asset_registry"]["path"] == "出图/共享/asset_registry.json"


def test_shot_without_any_asset_id_yields_empty_plan_not_crash(tmp_path):
    root = _project(tmp_path, settings=OPENAI,
                    shots=[{"shot_id": "镜头1", "scene": "空镜 山谷晨雾"}], registry={"brand": {"id": "BRAND_X"}})
    report = rp.build_plan(root)
    shot = report["shots"][0]
    assert shot["assets"] == [] and shot["needs_action"] is False
    assert shot["recommended_tier"] == rp.adapter.TIER_SHARED_KIT
    assert report["summary"]["shots_needing_action"] == 0


# ── 参考预算封顶 ────────────────────────────────────────────────────────────────

def test_reference_budget_capped_at_backend_limit(tmp_path):
    refs = [f"设定库/r{i}.png" for i in range(7)]
    root = _project(
        tmp_path, settings=OPENAI,  # GPT Image 2 上限 5
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": refs}]},
    )
    _touch(root, *refs)
    report = rp.build_plan(root)

    budget = report["shots"][0]["reference_budget"]
    assert budget["limit"] == 5 and budget["requested"] == 7 and budget["selected"] == 5
    assert [d["path"] for d in budget["dropped"]] == refs[5:]
    assert len(report["shots"][0]["references"]) == 5
    hits = _find(report, "reference_budget_overflow", shot="镜头1")
    assert len(hits) == 1 and hits[0]["severity"] == "warn"
    assert "不要以为它们被喂进去了" in hits[0]["msg"]


def test_budget_prioritises_product_over_character_within_a_shot(tmp_path):
    root = _project(
        tmp_path, settings={"生图模型": "MyCustomDiffusion"},  # 未知后端 → 上限 1
        shots=[{"shot_id": "镜头1", "scene": "中景 产品与代言人",
                "assets": {"CHAR_host": True, "PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": ["设定库/p.png"]}],
                  "characters": [{"id": "CHAR_host", "reference_images": ["设定库/c.png"]}]},
    )
    _touch(root, "设定库/p.png", "设定库/c.png")
    report = rp.build_plan(root)
    # 预算只有 1 张时先保产品——产品漂了整片报废。
    assert report["shots"][0]["references"] == ["设定库/p.png"]
    assert _asset_plan(report, "镜头1", "CHAR_host")["reference_count"] == 0


# ── 输出 schema 形状 ────────────────────────────────────────────────────────────

def test_report_schema_shape_and_findings_use_msg_key(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": ["设定库/a.png"]}]},
    )
    _touch(root, "设定库/a.png")
    report = rp.build_plan(root)

    assert report["schema_version"] == 1
    assert report["kind"] == "ad_reference_plan"
    assert {"schema_version", "kind", "summary", "findings"} <= set(report)
    assert {"block", "warn", "info"} <= set(report["summary"])
    assert report["thresholds"]["provenance"] == "internal-heuristic·confidence=low"
    assert report["findings"], "本夹具应至少有一条 finding"
    for f in report["findings"]:
        # 对齐 ad-craft/scripts/gate.py 的 finding schema：键是 `msg`，不是 `message`。
        assert {"severity", "code", "msg"} <= set(f)
        assert "message" not in f
        assert f["severity"] in ("block", "warn", "info")
        assert isinstance(f["msg"], str) and f["msg"]
    counts = {sev: sum(1 for f in report["findings"] if f["severity"] == sev)
              for sev in ("block", "warn", "info")}
    assert {k: report["summary"][k] for k in counts} == counts
    json.dumps(report, ensure_ascii=False)  # 报告必须可序列化


def test_report_summary_counts_shots_and_product_shots(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}},
               {"shot_id": "镜头2", "scene": "山谷晨雾空镜"}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": ["设定库/a.png", "设定库/b.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png")
    report = rp.build_plan(root)
    assert report["summary"]["shots"] == 2
    assert report["summary"]["product_shots"] == 1
    assert [s["shot"] for s in report["shots"]] == ["镜头1", "镜头2"]


def test_advisory_note_states_default_non_blocking(tmp_path):
    report = rp.build_plan(_project(tmp_path, settings=OPENAI))
    assert "advisory" in report["advisory"] and "--strict" in report["advisory"]


# ── CLI：--strict 退出码 / --json / --write ─────────────────────────────────────

def _blocking_project(tmp_path):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": ["设定库/a.png"]}]},
    )
    _touch(root, "设定库/a.png")
    return root


def test_default_exit_is_zero_even_with_blocks(tmp_path, capsys):
    root = _blocking_project(tmp_path)
    rc = rp.main([str(root)])
    capsys.readouterr()
    assert rp.build_plan(root)["summary"]["block"] > 0
    assert rc == 0  # advisory：这是「审」不是「闸」


def test_strict_exits_one_when_block_present(tmp_path, capsys):
    rc = rp.main([str(_blocking_project(tmp_path)), "--strict"])
    capsys.readouterr()
    assert rc == 1


def test_strict_exits_zero_when_no_block(tmp_path, capsys):
    root = _project(
        tmp_path, settings=OPENAI,
        shots=[{"shot_id": "镜头1", "scene": "中景 产品", "assets": {"PROD_BOTTLE": True}}],
        registry={"products": [{"id": "PROD_BOTTLE", "reference_images": ["设定库/a.png", "设定库/b.png"]}]},
    )
    _touch(root, "设定库/a.png", "设定库/b.png")
    rc = rp.main([str(root), "--strict"])
    capsys.readouterr()
    assert rc == 0


def test_strict_on_degraded_inputs_still_exits_zero(tmp_path, capsys):
    # 缺料只降级为 warn，不得把 --strict 变成「缺文件就红」。
    rc = rp.main([str(_project(tmp_path, settings=OPENAI)), "--strict"])
    capsys.readouterr()
    assert rc == 0


def test_json_flag_prints_parsable_report(tmp_path, capsys):
    rp.main([str(_blocking_project(tmp_path)), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "ad_reference_plan"
    assert payload["findings"][0]["msg"]


def test_default_stdout_is_markdown(tmp_path, capsys):
    rp.main([str(_blocking_project(tmp_path))])
    out = capsys.readouterr().out
    assert out.startswith("# 出图前·逐镜参考处方")
    assert "`product_shot_single_reference`" in out and "[镜头1]" in out


def test_write_lands_json_and_md_atomically(tmp_path, capsys):
    root = _blocking_project(tmp_path)
    rc = rp.main([str(root), "--write"])
    capsys.readouterr()
    assert rc == 0

    out_dir = root / "生产数据"
    json_path, md_path = out_dir / "ad_reference_plan.json", out_dir / "ad_reference_plan.md"
    assert json_path.is_file() and md_path.is_file()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "ad_reference_plan"
    assert payload["summary"]["block"] == 1
    md = md_path.read_text(encoding="utf-8")
    assert "GPT Image 2" in md and "⛔" in md
    # 原子写：不留半个报告 / 临时文件。
    assert [p.name for p in sorted(out_dir.iterdir())] == ["ad_reference_plan.json", "ad_reference_plan.md"]


def test_write_is_idempotent_and_overwrites_in_place(tmp_path, capsys):
    root = _blocking_project(tmp_path)
    rp.main([str(root), "--write"])
    rp.main([str(root), "--write"])
    capsys.readouterr()
    out_dir = root / "生产数据"
    assert len(list(out_dir.iterdir())) == 2
    assert json.loads((out_dir / "ad_reference_plan.json").read_text(encoding="utf-8"))["summary"]["block"] == 1


def test_no_write_flag_leaves_no_artifacts(tmp_path, capsys):
    root = _blocking_project(tmp_path)
    rp.main([str(root)])
    capsys.readouterr()
    assert not (root / "生产数据").exists()


def test_render_markdown_of_empty_plan_says_no_gap():
    md = rp.render_markdown({"summary": {"block": 0, "warn": 0, "info": 0, "shots": 0},
                             "backend": rp.adapter.profile_for("GPT Image 2"),
                             "inputs": {}, "thresholds": {"provenance": rp.PROVENANCE},
                             "findings": [], "shots": []})
    assert "✅ 逐镜参考处方无缺口" in md


def test_cli_requires_root_argument():
    with pytest.raises(SystemExit):
        rp.main([])
