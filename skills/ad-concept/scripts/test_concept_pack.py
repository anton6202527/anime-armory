# -*- coding: utf-8 -*-
"""创意包机检（concept_pack）单测。

盯的是三条最容易被写坏的纪律：
  ① 占位（待补/TBD）必须被抓——`producer_pack` 会把占位原样抄进制片包；
  ② objective 与 brief.campaign_objective 不一致必须报（策略跑偏的第一现场）；
  ③ SMP 稀释判据落在 **supports_key_message=false 的条目数**上，不是 len(usps) 上。
"""
import json

import concept_pack


def _write(root, rel, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _pack(**over):
    pack = {
        "kind": "ad_concept_pack",
        "big_idea": "把一天的元气装进一个盒子",
        "key_message": "0 糖也能有元气",
        "creative_route": "生活方式片",
        "objective": "拉新",
        "hypothesis": "年轻白领愿为 0 糖多付 2 元",
        "kv_direction": "晨光里的星盒特写",
        "usps": [{"id": "USP_01", "text": "0 糖 0 卡", "supports_key_message": True}],
        "storyline": [{"section": "钩子", "desc": "闹钟响", "planned_seconds": 30}],
    }
    pack.update(over)
    return pack


def _codes(report):
    return [f["code"] for f in report["findings"]]


def _by_code(report, code):
    return [f for f in report["findings"] if f["code"] == code]


# ── 占位检出 ──────────────────────────────────────────────────────────────────

def test_placeholder_fields_block(tmp_path):
    """待补/TBD 占位 = 结构性缺口，确定性 → block。"""
    _write(tmp_path, "创意/concept.json", _pack(big_idea="待补", hypothesis="TBD"))

    report = concept_pack.build(tmp_path)

    pending = _by_code(report, "concept_field_pending")
    assert len(pending) == 2
    assert all(f["severity"] == "block" for f in pending)
    assert any("big_idea" in f["msg"] for f in pending)
    assert any("hypothesis" in f["msg"] for f in pending)


def test_missing_required_field_blocks(tmp_path):
    pack = _pack()
    del pack["kv_direction"]
    _write(tmp_path, "创意/concept.json", pack)

    report = concept_pack.build(tmp_path)

    missing = _by_code(report, "concept_field_missing")
    assert len(missing) == 1
    assert missing[0]["severity"] == "block"
    assert "kv_direction" in missing[0]["msg"]


# ── objective ↔ brief 一致性 ──────────────────────────────────────────────────

def test_objective_mismatch_with_brief_warns(tmp_path):
    _write(tmp_path, "创意/concept.json", _pack(objective="拉新"))
    _write(tmp_path, "需求/brief.json", {"campaign_objective": "品牌认知"})

    report = concept_pack.build(tmp_path)

    hits = _by_code(report, "objective_brief_mismatch")
    assert len(hits) == 1
    assert hits[0]["severity"] == "warn"  # 机器分不出是 brief 后改还是创意跑偏 → 交人判
    assert "拉新" in hits[0]["msg"] and "品牌认知" in hits[0]["msg"]


def test_objective_matches_brief_modulo_whitespace(tmp_path):
    """归一化只做去空白+小写——『拉 新』与『拉新』是同一目标，不该报。"""
    _write(tmp_path, "创意/concept.json", _pack(objective="拉 新"))
    _write(tmp_path, "需求/brief.json", {"campaign_objective": "拉新"})

    assert "objective_brief_mismatch" not in _codes(concept_pack.build(tmp_path))


def test_missing_brief_is_info_not_pass(tmp_path):
    """缺 brief 不臆造通过：记 insufficient_data 的 info。"""
    _write(tmp_path, "创意/concept.json", _pack())

    hits = _by_code(concept_pack.build(tmp_path), "objective_brief_unavailable")
    assert len(hits) == 1
    assert hits[0]["severity"] == "info"


# ── SMP：不相关卖点稀释 ───────────────────────────────────────────────────────

def test_unrelated_usp_dilution_warns(tmp_path):
    """判据是 supports_key_message=false 的**条目数**，不是卖点总数。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[
        {"id": "USP_01", "text": "0 糖 0 卡", "supports_key_message": True},
        {"id": "USP_02", "text": "包装可回收", "supports_key_message": False},
        {"id": "USP_03", "text": "赠联名贴纸", "supports_key_message": False},
    ]))

    report = concept_pack.build(tmp_path)

    hits = _by_code(report, "usp_unrelated_dilution")
    assert len(hits) == 1
    assert hits[0]["severity"] == "warn"  # 创意判断，机器无权 block
    assert "USP_02" in hits[0]["msg"] and "USP_03" in hits[0]["msg"]
    assert report["summary"]["block"] == 0


def test_many_but_all_related_usps_do_not_dilute(tmp_path):
    """卖点多≠稀释：全部相关时不报稀释（多个**相关**卖点是加分项）。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[
        {"id": f"USP_{i:02d}", "text": f"卖点{i}", "supports_key_message": True}
        for i in range(1, 7)
    ]))

    codes = _codes(concept_pack.build(tmp_path))

    assert "usp_unrelated_dilution" not in codes
    assert "usp_overload_with_unrelated" not in codes


def test_undeclared_support_is_not_counted_as_unrelated(tmp_path):
    """未声明 supports_key_message 只报「未声明」，不当成不相关（缺料不臆造）。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[
        {"id": "USP_01", "text": "0 糖 0 卡"},
        {"id": "USP_02", "text": "包装可回收"},
    ]))

    codes = _codes(concept_pack.build(tmp_path))

    assert "usp_support_undeclared" in codes
    assert "usp_unrelated_dilution" not in codes


def test_empty_usps_blocks(tmp_path):
    _write(tmp_path, "创意/concept.json", _pack(usps=[]))

    hits = _by_code(concept_pack.build(tmp_path), "usps_empty")
    assert len(hits) == 1 and hits[0]["severity"] == "block"


# ── 降级 & 契约形状 ───────────────────────────────────────────────────────────

def test_missing_concept_degrades_without_crash(tmp_path):
    report = concept_pack.build(tmp_path)

    assert report["available"] is False
    assert report["summary"]["block"] == 0  # 缺料不硬拦
    assert _codes(report) == ["concept_pack_missing"]
    assert report["findings"][0]["severity"] == "warn"


def test_nonexistent_root_is_rc0(tmp_path, capsys):
    assert concept_pack.main([str(tmp_path / "nope")]) == 0


def test_build_contract_shape(tmp_path):
    _write(tmp_path, "创意/concept.json", _pack())

    report = concept_pack.build(tmp_path)

    assert report["schema_version"] == 1
    assert report["kind"] == "ad_concept_pack_check"
    assert isinstance(report["available"], bool)
    assert set(report["summary"]) >= {"block", "warn", "info"}
    for f in report["findings"]:
        assert set(f) == {"severity", "code", "msg"}  # gate 消费 msg，不是 message
        assert f["severity"] in {"block", "warn", "info"}
    assert report["thresholds"]["provenance"] == "internal-heuristic·confidence=low"


def test_clean_pack_has_no_block(tmp_path):
    _write(tmp_path, "创意/concept.json", _pack())
    _write(tmp_path, "需求/brief.json", {"campaign_objective": "拉新"})

    report = concept_pack.build(tmp_path)

    assert report["summary"]["block"] == 0


# ── CLI / 退出码 ──────────────────────────────────────────────────────────────

def test_strict_exit_code_only_on_block(tmp_path, capsys):
    _write(tmp_path, "创意/concept.json", _pack(big_idea="待补"))

    assert concept_pack.main([str(tmp_path)]) == 0             # 默认是审不是门
    assert concept_pack.main([str(tmp_path), "--strict"]) == 1  # --strict 才拦
    capsys.readouterr()


def test_strict_passes_when_only_warns(tmp_path, capsys):
    """--strict 只看 block：warn（如 objective 不一致）不该拦住流程。"""
    _write(tmp_path, "创意/concept.json", _pack(objective="拉新"))
    _write(tmp_path, "需求/brief.json", {"campaign_objective": "品牌认知"})

    assert concept_pack.build(tmp_path)["summary"]["warn"] >= 1
    assert concept_pack.main([str(tmp_path), "--strict"]) == 0
    capsys.readouterr()


def test_write_emits_json_and_md(tmp_path, capsys):
    _write(tmp_path, "创意/concept.json", _pack())

    concept_pack.main([str(tmp_path), "--write"])
    capsys.readouterr()

    out = tmp_path / "生产数据" / "ad_concept_pack_check.json"
    assert json.loads(out.read_text(encoding="utf-8"))["kind"] == "ad_concept_pack_check"
    assert "创意包机检" in out.with_suffix(".md").read_text(encoding="utf-8")
