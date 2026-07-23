#!/usr/bin/env python3
"""Tests for source_adaptation_audit.py."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import source_adaptation_audit as SA  # noqa: E402


def _mk_ep(raw, voiceover="", storyboard=None, triage=None):
    d = tempfile.mkdtemp()
    ep = Path(d) / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "raw.txt").write_text(raw, encoding="utf-8")
    if voiceover:
        (ep / "voiceover.txt").write_text(voiceover, encoding="utf-8")
    if storyboard is not None:
        (ep / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    if triage is not None:
        (ep / "adaptation_triage.json").write_text(json.dumps(triage, ensure_ascii=False), encoding="utf-8")
    return d


RAW = "沈念被逼到宫墙下。门外突然传来系统提示【妖血觉醒】。她发现真相，反击柳娘子！"


def codes(result):
    return {f["code"] for f in result["findings"]}


def test_passes_when_system_term_and_event_are_adapted():
    root = _mk_ep(
        RAW,
        "[镜头1·沈念·惊恐·快] 系统提示【妖血觉醒】。\n"
        "[镜头2·沈念·冷冽·快] 原来柳娘子害我，我要反击！  💥爽点\n"
        "[镜头3·沈念·阴狠·慢] 这局才刚开始。  🪝集尾\n",
    )

    result = SA.audit(root, "第1集")

    assert result["ok"]
    assert codes(result) == set()


def test_missing_bracketed_source_term_is_warned():
    root = _mk_ep(
        RAW,
        "[镜头1·沈念·惊恐·快] 门外传来怪声。\n"
        "[镜头2·沈念·冷冽·快] 我要反击柳娘子！  💥爽点\n",
    )

    result = SA.audit(root, "第1集")

    assert not result["ok"]
    assert "source_term_missing" in codes(result)


def test_title_terms_keep_character_titles_but_drop_clause_fragments():
    assert "林小姐" in SA.important_terms("林小姐逼她认罪。")
    assert "画要是叫长老" not in SA.important_terms("回头那画要是叫长老看见了，还以为咱们藏了逃犯。")


def test_clause_fragment_before_title_does_not_force_source_term_warning():
    root = _mk_ep(
        "回头那画要是叫长老看见了，还以为咱们藏了逃犯。",
        "[镜头1·王敦·痞笑·常速] 这张画像别让长老看见，免得惹麻烦。\n",
    )

    result = SA.audit(root, "第1集")

    assert "source_term_missing" not in codes(result)


def test_missing_adaptation_is_must():
    root = _mk_ep(RAW)

    result = SA.audit(root, "第1集")

    assert not result["ok"]
    assert "missing_adaptation" in codes(result)


def test_key_event_omission_is_warned():
    root = _mk_ep(
        "沈念发现真相：柳娘子下毒害死了她的兄长！她拔剑反击。",
        "[镜头1·旁白·平静·慢] 天色渐晚，院中很安静。\n",
    )

    result = SA.audit(root, "第1集")

    assert not result["ok"]
    assert "source_event_maybe_omitted" in codes(result)


def test_scene_function_loss_is_warned():
    root = _mk_ep(
        "沈念为了保护妹妹决定公开证据，因此暴露身份，被全城通缉。",
        "[镜头1·旁白·平静·慢] 天色渐晚，院中很安静。\n",
    )

    result = SA.audit(root, "第1集")

    assert not result["ok"]
    assert "scene_function_maybe_lost" in codes(result)


def test_logged_detail_rewrite_downgrades_source_term_warning():
    root = _mk_ep(
        RAW,
        "[镜头1·沈念·惊恐·快] 门外血光炸开，她的血脉突然暴走。\n"
        "[镜头2·沈念·冷冽·快] 柳娘子害我，我当场反杀！  💥爽点\n",
        triage={
            "kind": "n2d_adaptation_triage",
            "items": [{
                "id": "AT_001",
                "source_span": "raw.txt:门外突然传来系统提示【妖血觉醒】",
                "decision": "dramatize",
                "change_type": "rewrite_detail",
                "reason": "系统提示改成更强视觉化的血光觉醒，保留觉醒功能并提高短剧开场冲击。",
                "delivery": "voiceover 镜头1 + storyboard Clip_01 用血光暴走替代【妖血觉醒】字面系统音。",
                "adaptation_delta": {
                    "changed_from": "系统提示【妖血觉醒】",
                    "changed_to": "血光炸开，血脉暴走",
                    "preserved_function": ["觉醒", "危机升级", "开场钩子"],
                },
            }],
        },
    )

    result = SA.audit(root, "第1集")

    assert "source_term_missing" not in codes(result)
    assert "source_term_reworked_by_triage" in codes(result)
    assert result["ok"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))


def _write_spine(root, threads, status="confirmed"):
    pack = Path(root) / "开发包"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "story_spine.json").write_text(json.dumps({
        "kind": "n2d_story_spine", "version": 1, "status": status,
        "spine": [{"id": "SPINE_01", "beat": "主线", "source_span": "第1章"}],
        "threads": threads,
    }, ensure_ascii=False), encoding="utf-8")


def test_spine_cut_thread_authorizes_omission():
    # 源文里有"柳娘子"这条支线；改编稿不覆盖它。若 story_spine 已 cut 该支线并给关键词，
    # 审计按"全书级有账剪枝"处理（info），不再 warn 逼逐句登记。
    raw = "沈念被逼到宫墙下。系统提示【妖血觉醒】。柳娘子在暗处布局多年，另有隐情。她反击柳娘子。"
    root = _mk_ep(
        raw,
        "[镜头1·沈念·惊恐·快] 系统提示【妖血觉醒】。\n"
        "[镜头2·沈念·冷冽·快] 这局才刚开始。  🪝集尾\n",
    )
    _write_spine(root, [{
        "id": "THREAD_LIU", "name": "柳娘子宫斗旁枝", "class": "tangent", "decision": "cut",
        "cut_keywords": ["柳娘子"],
        "connectivity": {"payoff_reroute": "该宫斗线与主线无关，随线程退役。",
                          "no_orphan_proof": "无下游主线依赖。"},
    }])

    result = SA.audit(root, "第1集")
    c = codes(result)
    # 被 spine 授权的支线内容记为 *_cut_by_spine（info），而非 warn 级缺失。
    assert any(code.endswith("_cut_by_spine") for code in c)
    liu_warn = [f for f in result["findings"]
                if f["severity"] == "warn" and "柳娘子" in json.dumps(f.get("evidence") or {}, ensure_ascii=False)]
    assert not liu_warn  # 柳娘子这条被 cut 的支线不再产生 warn
    assert result["stats"]["spine_cut_threads"] == 1
    assert result["stats"]["spine_authorized_omissions"] >= 1


def test_spine_draft_does_not_authorize():
    # story_spine 未 confirmed 时不授权免账。
    raw = "沈念被逼到宫墙下。柳娘子在暗处布局多年。她反击柳娘子。"
    root = _mk_ep(root=None, raw=raw, voiceover="[镜头1·沈念·惊恐·快] 门外传来怪声。\n") if False else _mk_ep(
        raw, "[镜头1·沈念·惊恐·快] 门外传来怪声。\n")
    _write_spine(root, [{
        "id": "THREAD_LIU", "name": "柳娘子旁枝", "class": "tangent", "decision": "cut",
        "cut_keywords": ["柳娘子"], "connectivity": {"payoff_reroute": "x", "no_orphan_proof": "y"},
    }], status="draft")
    result = SA.audit(root, "第1集")
    assert "source_term_cut_by_spine" not in codes(result)


# ── 反向防瞎编（P2·--check-fabrication）──

FAB_RAW = "沈念被逼到宫墙下。系统提示【妖血觉醒】。她反击柳娘子。"


def test_fabrication_flags_invented_title():
    # 改编稿凭空多出源文没有的"玄冥长老"称谓，且无 adaptation_triage 有账 → warn 候选。
    root = _mk_ep(
        FAB_RAW,
        "[镜头1·沈念·惊恐] 系统提示【妖血觉醒】。\n"
        "[镜头2·沈念·冷冽] 是玄冥长老在背后操盘，我要反击！\n",
    )
    result = SA.audit(root, "第1集", check_fabrication=True)
    assert "fabricated_entity_candidate" in codes(result)
    assert result["stats"]["fabrication_candidates"] >= 1


def test_fabrication_silent_when_default():
    # 不传 check_fabrication → 反向层不跑，不引入新 warn（老 gate 不受影响）。
    root = _mk_ep(
        FAB_RAW,
        "[镜头2·沈念·冷冽] 是玄冥长老在背后操盘，我要反击！\n",
    )
    result = SA.audit(root, "第1集")
    assert "fabricated_entity_candidate" not in codes(result)
    assert result["stats"]["fabrication_candidates"] == 0


def test_fabrication_not_flagged_when_in_source():
    # 称谓源文就有 → 不算瞎编。
    root = _mk_ep(
        "沈念被逼到宫墙下。玄冥长老在背后操盘。系统提示【妖血觉醒】。",
        "[镜头1·沈念·冷冽] 是玄冥长老在背后操盘，我反击！\n",
    )
    result = SA.audit(root, "第1集", check_fabrication=True)
    assert "fabricated_entity_candidate" not in codes(result)


def test_fabrication_accounted_by_triage():
    # 改编稿新增"玄冥长老"，但 adaptation_triage 登记了 combine_minor_role 改写账 → info，不 warn。
    root = _mk_ep(
        FAB_RAW,
        "[镜头1·沈念·冷冽] 是玄冥长老在背后操盘，我要反击！\n",
        triage={"items": [{
            "id": "T1", "source_span": "第1章", "decision": "rewrite",
            "change_type": "combine_minor_role",
            "reason": "把源文两名模糊反派合并成玄冥长老，收束反派线。",
            "adaptation_delta": "changed_from 两名散兵→changed_to 玄冥长老一人",
            "preserved_function": "反派施压", "short_drama_reason": "反派聚焦",
            "delivery": "台词点名玄冥长老",
        }]},
    )
    result = SA.audit(root, "第1集", check_fabrication=True)
    c = codes(result)
    assert "fabricated_entity_candidate" not in c
    assert "adaptation_new_term_accounted" in c
