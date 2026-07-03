# -*- coding: utf-8 -*-
"""cd skills/n2d-script/scripts && python3 -m pytest test_source_language.py"""
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


def test_empty_text_defaults_modern():
    assert sl.classify_register("")["register"] == "modern_zh"


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
