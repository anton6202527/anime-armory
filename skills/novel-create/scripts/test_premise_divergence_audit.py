# -*- coding: utf-8 -*-
"""test_premise_divergence_audit — 蓝图三方案差异化机检。

Run: cd skills/novel-create/scripts && python3 -m pytest test_premise_divergence_audit.py
"""
import json
import os

import premise_divergence_audit as pda


def _cand(cid, logline, memory=""):
    return {"id": cid, "logline": logline, "memory_point": memory}


def test_too_few_candidates():
    alerts = pda.audit_candidates([_cand("A", "少年获得系统逆袭")])
    assert any(a["type"] == "too_few_candidates" for a in alerts)


def test_paraphrase_pair_flagged():
    # B 是 A 的换句话说：大量共享 2-gram → 建议级
    a = _cand("A", "落魄少年绑定签到系统，在宗门杂役堆里每日签到变强打脸")
    b = _cand("B", "落魄少年绑定了签到系统，在宗门杂役堆中靠每日签到变强与打脸")
    c = _cand("C", "亡国公主假扮说书人，用故事操纵各国权臣复国")
    alerts = pda.audit_candidates([a, b, c])
    pairs = [x for x in alerts if x["type"] == "paraphrase_pair"]
    assert len(pairs) == 1 and set(pairs[0]["pair"]) == {"A", "B"}
    assert pairs[0]["severity"] == "建议级"


def test_divergent_candidates_clean():
    alerts = pda.audit_candidates([
        _cand("A", "亡国公主假扮说书人，用故事操纵各国权臣复国"),
        _cand("B", "殡仪馆化妆师能听见遗体最后一句遗言，卷入连环案"),
        _cand("C", "废柴炼丹师给妖怪开餐馆，菜谱就是丹方"),
    ])
    assert alerts == []


def test_shared_trope_anchor_info():
    # 措辞不同但都压在"系统+重生"套路锚上 → info
    alerts = pda.audit_candidates([
        _cand("A", "程序员重生获得点评系统，靠毒舌点评天下武学"),
        _cand("B", "厨娘重生绑定美食系统，一路开店到御膳房"),
        _cand("C", "亡国公主假扮说书人复国"),
    ])
    shared = [x for x in alerts if x["type"] == "shared_trope_anchor"]
    assert len(shared) == 1 and set(shared[0]["pair"]) == {"A", "B"}
    assert "系统" in shared[0]["tropes"] and "重生" in shared[0]["tropes"]


def test_analyze_missing_file_skips_with_guidance(tmp_path):
    res = pda.analyze(str(tmp_path))
    assert res["ran"] is False and "premise_candidates.json" in res["skipped"]


def test_analyze_roundtrip_and_advisory(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "设定"), exist_ok=True)
    payload = {"schema_version": 1, "kind": "novel_premise_candidates",
               "candidates": [
                   {"id": "A", "logline": "落魄少年绑定签到系统，在宗门杂役堆里每日签到变强打脸"},
                   {"id": "B", "logline": "落魄少年绑定了签到系统，在宗门杂役堆中靠每日签到变强与打脸"},
                   {"id": "C", "logline": "亡国公主假扮说书人复国"},
               ], "chosen": None}
    with open(os.path.join(str(tmp_path), "设定", "premise_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    res = pda.analyze(str(tmp_path))
    assert res["ran"] is True and res["blocking"] == 0
    assert any(a["type"] == "paraphrase_pair" for a in res["alerts"])
    assert os.path.exists(os.path.join(str(tmp_path), "审稿")) is False  # analyze 不落盘，main 才落盘
