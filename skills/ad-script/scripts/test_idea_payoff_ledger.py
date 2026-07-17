# -*- coding: utf-8 -*-
"""创意承诺→分镜兑现 账本（idea_payoff_ledger）单测。

盯四条纪律：
  ① 显式 usp_ids 绑定 = 高置信直接对账（且缺绑定时才敢升 block）；
  ② 无结构化字段时**只产 candidate 不宣判**——弱文本匹配无权说「已兑现」；
  ③ 增量合并**绝不覆盖已填的 payoff_shots**（编剧手填的是真值）；
  ④ usp_offledger（分镜冒出未登记卖点 = 创意漂移）是纯结构比对 → 有资格 block。
"""
import json

import idea_payoff_ledger as ipl


def _write(root, rel, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _pack(**over):
    pack = {
        "kind": "ad_concept_pack",
        "key_message": "0 糖也能有元气",
        "kv_direction": "晨光里的星盒特写",
        "usps": [{"id": "USP_01", "text": "0 糖 0 卡", "supports_key_message": True}],
        "storyline": [{"section": "钩子", "desc": "闹钟响"}],
    }
    pack.update(over)
    return pack


def _codes(report):
    return [f["code"] for f in report["findings"]]


def _by_code(report, code):
    return [f for f in report["findings"] if f["code"] == code]


def _entry(report, eid):
    for e in report["ledger"]["entries"]:
        if e["id"] == eid:
            return e
    raise AssertionError(f"账本里没有 {eid}：{[e['id'] for e in report['ledger']['entries']]}")


# ── ① 显式绑定 = 高置信对账 ──────────────────────────────────────────────────

def test_explicit_usp_ids_reconcile_with_high_confidence(tmp_path):
    _write(tmp_path, "创意/concept.json", _pack())
    _write(tmp_path, "脚本/storyboard.json", {"shots": [
        {"shot_id": "S1", "section": "钩子", "frame": "闹钟响", "delivers_key_message": True},
        {"shot_id": "S2", "usp_ids": ["USP_01"], "frame": "产品特写", "is_kv": True},
    ]})

    report = ipl.build(tmp_path)

    usp = _entry(report, "USP_01")
    assert usp["status"] == "done"
    assert usp["confidence"] == "explicit"
    assert usp["payoff_shots"] == ["S2"]
    assert _entry(report, "KM_01")["payoff_shots"] == ["S1"]   # delivers_key_message
    assert _entry(report, "KV_01")["payoff_shots"] == ["S2"]   # is_kv
    assert _entry(report, "BEAT_01")["payoff_shots"] == ["S1"]  # section 相等
    assert report["summary"]["block"] == 0
    assert "usp_unrealized" not in _codes(report)


def test_structured_project_blocks_unrealized_usp(tmp_path):
    """项目**在用** usp_ids 绑定 → 某卖点没绑定即确定性漏洞 → block。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[
        {"id": "USP_01", "text": "0 糖 0 卡"},
        {"id": "USP_02", "text": "一天一盒"},
    ]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [
        {"shot_id": "S1", "usp_ids": ["USP_01"], "frame": "产品特写"},
    ]})

    hits = _by_code(ipl.build(tmp_path), "usp_unrealized")

    assert len(hits) == 1
    assert hits[0]["severity"] == "block"
    assert "USP_02" in hits[0]["msg"]


def test_unstructured_project_only_warns_on_unrealized_usp(tmp_path):
    """项目没在用绑定 → 结论只能靠弱文本匹配 → 无权硬拦，退 warn。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[{"id": "USP_01", "text": "0 糖 0 卡"}]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [{"shot_id": "S1", "frame": "城市清晨"}]})

    hits = _by_code(ipl.build(tmp_path), "usp_unrealized")

    assert len(hits) == 1
    assert hits[0]["severity"] == "warn"
    assert ipl.build(tmp_path)["summary"]["block"] == 0


def test_key_message_and_kv_never_block(tmp_path):
    """『这一镜算不算承载了主张』没有确定性判据 → 永远 warn，哪怕项目在用结构化绑定。"""
    _write(tmp_path, "创意/concept.json", _pack())
    _write(tmp_path, "脚本/storyboard.json", {"shots": [
        {"shot_id": "S1", "section": "钩子", "usp_ids": ["USP_01"], "frame": "闹钟响"},
    ]})

    report = ipl.build(tmp_path)

    assert [f["severity"] for f in _by_code(report, "key_message_unrealized")] == ["warn"]
    assert [f["severity"] for f in _by_code(report, "kv_unrealized")] == ["warn"]


# ── ② 无结构化字段 → 只产 candidate，不宣判 ─────────────────────────────────

def test_weak_match_yields_candidate_not_verdict(tmp_path):
    """VO 里出现了卖点原文，但没有任何结构化绑定 → candidate + info，绝不标 done。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[{"id": "USP_01", "text": "0 糖 0 卡"}]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [{"shot_id": "S1", "frame": "产品特写"}]})
    _write(tmp_path, "脚本/voiceover.txt", "0 糖 0 卡，一天一盒。\n")

    report = ipl.build(tmp_path)
    usp = _entry(report, "USP_01")

    assert usp["status"] == "candidate"
    assert usp["confidence"] == "weak_text_match"
    assert usp["payoff_shots"] == []          # ← 关键：候选不算兑现
    assert usp["candidate_shots"] == ["S1"]

    hits = _by_code(report, "payoff_candidate_unconfirmed")
    assert len(hits) == 1
    assert hits[0]["severity"] == "info"      # 提示，不拦
    assert "usp_unrealized" not in _codes(report)
    assert report["summary"]["block"] == 0


def test_containment_is_asymmetric():
    """非对称是刻意的：问「这句卖点被这一镜提到了吗」，不是「两段文本像不像」。"""
    needle, haystack = "0糖0卡", "产品特写，桌上摆着 0糖0卡 的星盒，晨光从窗外洒进来，杯壁凝着水珠"

    assert ipl.containment(needle, haystack) == 1.0
    assert ipl.containment(haystack, needle) < 0.3  # 对称的 Jaccard 会被长度差压死


def test_uses_structured_binding_switch():
    assert ipl.uses_structured_binding([{"usp_ids": ["USP_01"]}]) is True
    assert ipl.uses_structured_binding([{"claim_ids": ["C1"]}]) is True
    assert ipl.uses_structured_binding([{"usp_ids": []}, {"frame": "空"}]) is False


# ── ③ 增量合并绝不覆盖已填的 payoff_shots ───────────────────────────────────

def test_merge_never_overwrites_human_filled_payoff_shots(tmp_path):
    """编剧手填 USP_01 → S9 且标 done；机器这轮只匹配到 S1，也不许改。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[{"id": "USP_01", "text": "0 糖 0 卡"}]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [{"shot_id": "S1", "usp_ids": ["USP_01"]}]})
    _write(tmp_path, ipl.LEDGER_REL, {
        "kind": ipl.LEDGER_KIND, "schema_version": 1,
        "entries": [{"id": "USP_01", "kind": "usp", "desc": "0 糖 0 卡",
                     "payoff_shots": ["S9"], "status": "done", "note": "人工确认"}],
    })

    usp = _entry(ipl.build(tmp_path), "USP_01")

    assert usp["payoff_shots"] == ["S9"]   # 不被机器的 ["S1"] 覆盖
    assert usp["status"] == "done"
    assert usp["note"] == "人工确认"        # 人写的字段不被抹掉


def test_merge_pure_function_semantics():
    existing = [{"id": "USP_01", "kind": "usp", "desc": "旧描述",
                 "payoff_shots": ["S9"], "status": "done"},
                {"id": "USP_02", "kind": "usp", "desc": "待对账", "payoff_shots": [], "status": "open"}]
    fresh = [{"id": "USP_01", "kind": "usp", "desc": "新描述（concept 改过）",
              "payoff_shots": ["S1"], "status": "done"},
             {"id": "USP_02", "kind": "usp", "desc": "待对账", "payoff_shots": ["S2"], "status": "done"},
             {"id": "USP_03", "kind": "usp", "desc": "concept 新增", "payoff_shots": [], "status": "open"}]

    merged = {e["id"]: e for e in ipl.merge_ledger(existing, fresh)}

    assert merged["USP_01"]["payoff_shots"] == ["S9"]        # 已填的不动
    assert merged["USP_01"]["desc"] == "新描述（concept 改过）"  # desc 跟随 concept 更新
    assert merged["USP_02"]["payoff_shots"] == ["S2"]        # 空的才补
    assert merged["USP_03"]["desc"] == "concept 新增"          # 新条目补登记


def test_write_ledger_roundtrip_preserves_human_edits(tmp_path, capsys):
    _write(tmp_path, "创意/concept.json", _pack(usps=[{"id": "USP_01", "text": "0 糖 0 卡"}]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [{"shot_id": "S1", "usp_ids": ["USP_01"]}]})

    ipl.main([str(tmp_path), "--write"])
    ledger_path = tmp_path / ipl.LEDGER_REL
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    data["entries"][0]["payoff_shots"] = ["S7"]  # 编剧改了
    ledger_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    ipl.main([str(tmp_path), "--write"])  # 复跑
    capsys.readouterr()

    again = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert again["entries"][0]["payoff_shots"] == ["S7"]


# ── ④ usp_offledger = 创意漂移 ──────────────────────────────────────────────

def test_usp_offledger_blocks(tmp_path):
    """分镜声明了 concept 没登记的卖点 = 临时加戏；纯结构比对 → block。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[{"id": "USP_01", "text": "0 糖 0 卡"}]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [
        {"shot_id": "S1", "usp_ids": ["USP_01"]},
        {"shot_id": "S2", "usp_ids": ["USP_99"], "frame": "临时加的联名贴纸镜"},
    ]})

    report = ipl.build(tmp_path)
    hits = _by_code(report, "usp_offledger")

    assert len(hits) == 1
    assert hits[0]["severity"] == "block"
    assert "USP_99" in hits[0]["msg"] and "S2" in hits[0]["msg"]
    assert report["summary"]["block"] == 1


def test_offledger_reported_once_per_usp(tmp_path):
    """同一个未登记卖点在多镜出现只报一次（报告是给人看的，不是刷屏）。"""
    _write(tmp_path, "创意/concept.json", _pack(usps=[{"id": "USP_01", "text": "0 糖 0 卡"}]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [
        {"shot_id": "S1", "usp_ids": ["USP_99"]},
        {"shot_id": "S2", "usp_ids": ["USP_99"]},
    ]})

    assert len(_by_code(ipl.build(tmp_path), "usp_offledger")) == 1


def test_offledger_pure_function():
    pack = {"usps": [{"id": "USP_01", "text": "x"}]}
    shots = [{"shot_id": "S1", "usp_ids": ["USP_01", "USP_42"]}]

    assert ipl.offledger_usp_ids(pack, shots) == [{"usp_id": "USP_42", "shot": "S1"}]


# ── 降级 & 契约形状 ───────────────────────────────────────────────────────────

def test_missing_concept_degrades_without_crash(tmp_path):
    report = ipl.build(tmp_path)

    assert report["available"] is False
    assert _codes(report) == ["concept_pack_missing"]
    assert report["findings"][0]["severity"] == "warn"
    assert report["summary"]["block"] == 0
    assert report["ledger"]["entries"] == []


def test_missing_storyboard_is_warn_not_pass(tmp_path):
    """没有分镜 ≠ 创意已兑现：记 insufficient_data 的 warn，且不逐条报未兑现。"""
    _write(tmp_path, "创意/concept.json", _pack())

    report = ipl.build(tmp_path)

    assert _codes(report) == ["storyboard_unavailable"]
    assert report["available"] is True
    assert report["summary"]["block"] == 0


def test_nonexistent_root_is_rc0(tmp_path, capsys):
    assert ipl.main([str(tmp_path / "nope")]) == 0
    capsys.readouterr()


def test_build_contract_shape(tmp_path):
    _write(tmp_path, "创意/concept.json", _pack())
    _write(tmp_path, "脚本/storyboard.json", {"shots": [{"shot_id": "S1", "usp_ids": ["USP_01"]}]})

    report = ipl.build(tmp_path)

    assert report["schema_version"] == 1
    assert report["kind"] == "ad_idea_payoff_audit"
    assert isinstance(report["available"], bool)
    assert set(report["summary"]) >= {"block", "warn", "info"}
    for f in report["findings"]:
        assert set(f) == {"severity", "code", "msg"}
        assert f["severity"] in {"block", "warn", "info"}
    assert report["thresholds"]["provenance"] == "internal-heuristic·confidence=low"


# ── CLI / 退出码 ──────────────────────────────────────────────────────────────

def test_strict_exit_code_only_on_block(tmp_path, capsys):
    _write(tmp_path, "创意/concept.json", _pack(usps=[{"id": "USP_01", "text": "0 糖 0 卡"}]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [{"shot_id": "S1", "usp_ids": ["USP_99"]}]})

    assert ipl.main([str(tmp_path)]) == 0
    assert ipl.main([str(tmp_path), "--strict"]) == 1
    capsys.readouterr()


def test_strict_passes_when_only_warns(tmp_path, capsys):
    _write(tmp_path, "创意/concept.json", _pack(usps=[{"id": "USP_01", "text": "0 糖 0 卡"}]))
    _write(tmp_path, "脚本/storyboard.json", {"shots": [{"shot_id": "S1", "frame": "城市清晨"}]})

    report = ipl.build(tmp_path)
    assert report["summary"]["warn"] >= 1 and report["summary"]["block"] == 0
    assert ipl.main([str(tmp_path), "--strict"]) == 0
    capsys.readouterr()
