# -*- coding: utf-8 -*-
"""cd skills/novel/_lib && python3 -m pytest test_source_language.py"""
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
MODERN_WITH_IDIOM = ("总之，他这个人虽然有点之乎者也的酸气，但其实人挺好的，"
                     "我们都知道他了，现在没什么可说的。") * 6


def test_classify_modern():
    assert sl.classify_register(MODERN)["register"] == "modern_zh"


def test_classify_classical():
    r = sl.classify_register(CLASSICAL)
    assert r["register"] == "classical_zh" and r["scores"]["de_density"] < sl.DE_DENSITY_MAX


def test_classify_english():
    r = sl.classify_register(ENGLISH)
    assert r["register"] == "non_chinese" and "latin" in r["lang_guess"]


def test_modern_idiom_not_misflagged():
    assert sl.classify_register(MODERN_WITH_IDIOM)["register"] == "modern_zh"


def _mk(tmp_path, text):
    (tmp_path / "原作.txt").write_text(text, encoding="utf-8")
    return str(tmp_path)


def test_check_modern_passes(tmp_path):
    assert sl.check(_mk(tmp_path, MODERN))["verdict"] == "pass"


def test_check_no_source_when_original(tmp_path):
    assert sl.check(str(tmp_path))["verdict"] == "no_source"


def test_check_classical_needs_then_confirmed(tmp_path):
    root = _mk(tmp_path, CLASSICAL)
    assert sl.check(root)["verdict"] == "needs_comprehension"
    sl.scaffold(root)
    assert os.path.exists(os.path.join(root, sl.COMPREHENSION_MD_REL))
    assert sl.check(root)["verdict"] == "needs_comprehension"   # draft 仍需补全
    jp = os.path.join(root, sl.COMPREHENSION_JSON_REL)
    rec = json.load(open(jp, encoding="utf-8")); rec["status"] = "confirmed"
    json.dump(rec, open(jp, "w", encoding="utf-8"), ensure_ascii=False)
    assert sl.check(root)["verdict"] == "pass"


def test_scaffold_foreign_template(tmp_path):
    root = _mk(tmp_path, ENGLISH)
    sl.scaffold(root)
    md = open(os.path.join(root, sl.COMPREHENSION_MD_REL), encoding="utf-8").read()
    assert "transcreation" in md and "本地化" in md


# ── qa_gate 集成：文言文原作未建理解层 → 阻断；确认后放行 ──
def test_qa_gate_blocks_classical_until_confirmed(tmp_path):
    import qa_gate
    root = _mk(tmp_path, CLASSICAL)
    status = qa_gate.collect_gate_status(root, require_state_closure=False)
    codes = {b.get("id") for b in status["blockers"]}
    assert "SOURCE-LANG-COMPREHENSION" in codes
    # 确认理解层后不再阻断
    sl.scaffold(root)
    jp = os.path.join(root, sl.COMPREHENSION_JSON_REL)
    rec = json.load(open(jp, encoding="utf-8")); rec["status"] = "confirmed"
    json.dump(rec, open(jp, "w", encoding="utf-8"), ensure_ascii=False)
    status2 = qa_gate.collect_gate_status(root, require_state_closure=False)
    assert "SOURCE-LANG-COMPREHENSION" not in {b.get("id") for b in status2["blockers"]}


def test_qa_gate_clean_for_modern_source(tmp_path):
    import qa_gate
    root = _mk(tmp_path, MODERN)
    status = qa_gate.collect_gate_status(root, require_state_closure=False)
    assert "SOURCE-LANG-COMPREHENSION" not in {b.get("id") for b in status["blockers"]}
