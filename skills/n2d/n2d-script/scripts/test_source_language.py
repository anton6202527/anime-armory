# -*- coding: utf-8 -*-
"""cd skills/n2d/n2d-script/scripts && python3 -m pytest test_source_language.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import source_language as sl

MODERN = ("他说他已经知道了这件事。我们现在就去那个地方，可以吗？"
          "她笑着摇了摇头，说不是这样的。这个故事的开头其实很简单。") * 6
CLASSICAL = ("子曰：学而时习之，不亦说乎？有朋自远方来，不亦乐乎？人不知而不愠，不亦君子乎？"
             "曾子曰：吾日三省吾身：为人谋而不忠乎？与朋友交而不信乎？传不习乎？") * 6
ENGLISH = ("He said he already knew about this matter. Let us go there now, shall we? "
           "She smiled and shook her head, saying it was not so.") * 6
# 现代白话里夹古语成语，绝不能误判为文言文
MODERN_WITH_IDIOM = ("总之，他这个人虽然有点之乎者也的酸气，但其实人挺好的，"
                     "我们都知道他了，现在没什么可说的。") * 6
LATE_IMPERIAL = (
    "第一囬 詞曰：春色如何。話說清河縣中有一官人，看官聽說，且說那娘子回到房中。"
    "那廝問道怎生是好，小人答曰不妨。他的兄弟已经回来了，众人便在这个时候商量起来。"
    "正是人情冷暖，有詩為證。按下此事不題。"
) * 12


def test_classify_modern():
    r = sl.classify_register(MODERN)
    assert r["register"] == "modern_zh"


def test_classify_classical():
    r = sl.classify_register(CLASSICAL)
    assert r["register"] == "classical_zh"
    assert r["scores"]["de_density"] < sl.DE_DENSITY_MAX


def test_classify_english_non_chinese():
    r = sl.classify_register(ENGLISH)
    assert r["register"] == "non_chinese"
    assert "latin" in r["lang_guess"]


def test_modern_with_classical_idiom_not_misflagged():
    # 防误判：现代白话夹"之乎者也"成语仍是 modern_zh（「的」密度高）
    assert sl.classify_register(MODERN_WITH_IDIOM)["register"] == "modern_zh"


def test_late_imperial_vernacular_gets_profile_without_breaking_register():
    r = sl.classify_register(LATE_IMPERIAL)
    assert r["register"] == "modern_zh"
    assert r["register_profile"] == "late_imperial_vernacular"
    assert r["lang_guess"] == "late_imperial_vernacular"


def test_empty_text_defaults_modern():
    assert sl.classify_register("")["register"] == "modern_zh"


def test_source_traits_fold_only_adjacent_identical_chapter_headings():
    text = (
        "第1章 起\n"
        "第1章 起\n"
        "正文。\n"
        "第2章 承\n"
        "作者: 两个标题之间的元数据\n"
        "第2章 承\n"
        "第3章 转\n"
        "第3章 另一个标题\n"
        + MODERN
    )
    traits = sl.detect_source_traits(text)

    # Adjacent exact duplicate => one marker. A metadata-separated repeat and a
    # same-number/different-title heading remain separate markers.
    assert traits["chapter_markers"] == 5


def test_source_traits_recognize_variant_hui_and_avoid_incidental_power_false_positive():
    text = "第一囬 風起\n正文談人生境界。\n第二囘 波生\n又談一重境界。\n" + LATE_IMPERIAL
    traits = sl.detect_source_traits(text)
    assert traits["chapter_markers"] >= 2
    assert traits["power_system_likely"] is False


def test_source_unit_inventory_prefers_real_hui_over_volume_wrappers():
    text = (
        "第1章 卷之一 第一回\n"
        "[编辑]第一囬 起勢\n正文。\n"
        "第二囬 承接\n正文。\n"
        "第三囘 轉折\n正文。\n"
    )
    rows = sl.extract_source_unit_inventory(text)
    assert [row["source_span"] for row in rows] == ["第一囬", "第二囬", "第三囘"]
    assert rows[0]["unit_id"] == "SRC_UNIT_0001"


def _mk(tmp_path, text):
    novel = tmp_path / "小说"
    novel.mkdir()
    (novel / "测试剧.txt").write_text(text, encoding="utf-8")
    return str(tmp_path)


def _confirm_contract(root):
    jp = os.path.join(root, sl.COMPREHENSION_JSON_REL)
    rec = json.load(open(jp, encoding="utf-8"))
    rec["status"] = "confirmed"
    rec[sl.CONTRACT_KEY] = {
        "modern_understanding": "主角被逼选择，决定反击并留下追更悬念。",
        "episode_promise_basis": [{
            "promise": "主角如何翻盘",
            "opened_at": "第1章",
            "payoff_or_progress": "第1集推进到拿到关键线索",
            "risk_if_cut": "删掉会失去追看理由",
        }],
        "character_motives": [{
            "character": "主角",
            "want": "保住身份并查清真相",
            "obstacle": "对手阻拦",
            "choice_pressure": "暴露身份或暂时忍耐",
            "arc_delta": "从被动转主动",
        }],
        "causality_chain": [{
            "cause": "对手陷害",
            "effect": "主角必须反击",
            "must_keep": "冲突起因",
            "adaptation_note": "可压缩旁白但不能删除",
        }],
        "foreshadowing_ledger": [{
            "setup": "令牌异常",
            "payoff_plan": "第2集揭示来源",
            "status": "open",
            "do_not_drop_reason": "主线悬念",
        }],
        "adaptation_boundaries": {
            "preserve": ["主角欲望", "关键令牌"],
            "modernize_or_compress": ["重复心理描写"],
            "do_not_change": ["陷害因果"],
        },
        "power_system_rules": {
            "applicable": "no",
            "level_or_rank_rules": [],
            "growth_constraints": [],
            "combat_consistency_rules": [],
            "not_applicable_reason": "本测试文本无战力/等级/系统规则。",
        },
        "source_register_strategy": {
            "register": rec["register"],
            "dialogue_style": "现代白话",
            "terms_to_keep": [],
            "terms_to_translate": [],
        },
    }
    if rec.get("register_profile") == "late_imperial_vernacular":
        rec[sl.CONTRACT_KEY]["premodern_adapter"] = {
            "coverage_scope": "全书总览 + 首批第一至三回",
            "unit_glosses": [{
                "source_span": "第一回",
                "modern_summary": "人物相遇并作出选择。",
                "dramatic_function": "建立关系与冲突",
                "trace_ids": ["SRC_CAUSE_001"],
            }],
            "historical_terms": [{
                "source_term": "官人",
                "modern_meaning": "对男子的称呼",
                "screen_treatment": "保留称谓",
            }],
            "verse_and_commentary_policy": "保留承担预示或反讽功能的韵文，其余压缩或视觉化。",
            "narrator_formula_policy": "少量保留说书人旁白，不逐段照搬套语。",
            "historical_context_policy": "服制、货币、礼俗按时代语境建卡。",
            "sensitive_content_policy": "保留剧情因果，非露骨呈现，不猎奇化受害者。",
            "dialogue_style_target": "现代可懂白话为骨，保留关键古称谓与少量章回韵味。",
        }
    json.dump(rec, open(jp, "w", encoding="utf-8"), ensure_ascii=False)


def test_check_modern_requires_comprehension_contract_then_passes(tmp_path):
    root = _mk(tmp_path, MODERN)
    res = sl.check(root)
    assert res["verdict"] == "needs_comprehension"
    assert res["register"] == "modern_zh"
    sl.scaffold(root)
    assert sl.check(root)["verdict"] == "needs_comprehension"
    _confirm_contract(root)
    assert sl.check(root)["verdict"] == "pass"


def test_check_classical_needs_comprehension_then_passes_when_confirmed(tmp_path):
    root = _mk(tmp_path, CLASSICAL)
    res = sl.check(root)
    assert res["verdict"] == "needs_comprehension" and res["register"] == "classical_zh"
    # 建脚手架后仍 draft → 仍需补全
    sl.scaffold(root)
    assert sl.check(root)["verdict"] == "needs_comprehension"
    assert os.path.exists(os.path.join(root, sl.COMPREHENSION_MD_REL))
    # 只确认 status 但不补合同 → 仍阻断
    jp = os.path.join(root, sl.COMPREHENSION_JSON_REL)
    rec = json.load(open(jp, encoding="utf-8"))
    rec["status"] = "confirmed"
    json.dump(rec, open(jp, "w", encoding="utf-8"), ensure_ascii=False)
    assert sl.check(root)["verdict"] == "needs_comprehension"
    # 人工确认：status=confirmed + understanding_contract 补齐 → 放行
    _confirm_contract(root)
    assert sl.check(root)["verdict"] == "pass"


def test_late_imperial_scaffold_requires_adapter_contract(tmp_path):
    root = _mk(tmp_path, LATE_IMPERIAL)
    made = sl.scaffold(root)
    assert made["register"] == "modern_zh"
    md = open(os.path.join(root, sl.COMPREHENSION_MD_REL), encoding="utf-8").read()
    assert "近世白话" in md and "逐回释义" in md
    rec = json.load(open(os.path.join(root, sl.COMPREHENSION_JSON_REL), encoding="utf-8"))
    assert rec["register_profile"] == "late_imperial_vernacular"
    assert "premodern_adapter" in rec[sl.CONTRACT_KEY]
    _confirm_contract(root)
    assert sl.check(root)["verdict"] == "pass"


def test_check_no_source(tmp_path):
    assert sl.check(str(tmp_path))["verdict"] == "no_source"


def test_scaffold_foreign_uses_foreign_template(tmp_path):
    root = _mk(tmp_path, ENGLISH)
    sl.scaffold(root)
    md = open(os.path.join(root, sl.COMPREHENSION_MD_REL), encoding="utf-8").read()
    assert "transcreation" in md and "本地化" in md


def test_power_system_text_requires_power_rules(tmp_path):
    root = _mk(tmp_path, ("他打开系统面板，境界从炼气一层升到炼气二层，战力属性暴涨。") * 12)
    sl.scaffold(root)
    _confirm_contract(root)
    jp = os.path.join(root, sl.COMPREHENSION_JSON_REL)
    rec = json.load(open(jp, encoding="utf-8"))
    rec[sl.CONTRACT_KEY]["power_system_rules"] = {
        "applicable": "yes",
        "level_or_rank_rules": [],
        "growth_constraints": [],
        "combat_consistency_rules": [],
    }
    json.dump(rec, open(jp, "w", encoding="utf-8"), ensure_ascii=False)
    res = sl.check(root)
    assert res["verdict"] == "needs_comprehension"
    assert any("power_system_rules" in x for x in res["contract_issues"])
