#!/usr/bin/env python3
"""Tests for story_integrity_audit.py."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import story_integrity_audit as SI  # noqa: E402


def _mk_ep(voiceover: str, ep: str = "第1集") -> str:
    root = tempfile.mkdtemp()
    d = Path(root) / "脚本" / ep
    d.mkdir(parents=True)
    (d / "voiceover.txt").write_text(voiceover, encoding="utf-8")
    return root


def codes(result):
    return {f["code"] for f in result["findings"]}


def test_choice_without_consequence_warned():
    root = _mk_ep(
        "[镜头1·沈念·紧张·快] 我决定留下来救她。\n"
        "[镜头2·沈念·紧张·快] 你们都别过来。\n"
        "[镜头3·沈念·平静·慢] 夜色越来越深。\n"
        "[镜头4·沈念·平静·慢] 她握紧衣角。\n"
    )

    result = SI.audit_episode(root, "第1集")

    assert "choice_without_consequence" in codes(result)


def test_choice_and_consequence_do_not_warn_choice_chain():
    root = _mk_ep(
        "[镜头1·沈念·紧张·快] 我决定救她。\n"
        "[镜头2·沈念·痛苦·快] 因此我暴露身份，失去令牌。\n"
        "[镜头3·沈念·冷冽·快] 但我会继续查清真相。\n"
        "[镜头4·沈念·冷冽·慢] 这笔账还没完。\n"
    )

    result = SI.audit_episode(root, "第1集")

    assert "choice_without_consequence" not in codes(result)
    assert "no_choice_consequence_chain" not in codes(result)


def test_write_scaffolds_creates_story_ledgers():
    root = _mk_ep(
        "[镜头1·沈念·紧张·快] 我决定救她。\n"
        "[镜头2·沈念·痛苦·快] 因此我暴露身份。\n"
        "[镜头3·旁白·悬疑·快] 门外突然传来脚步。 🪝集尾\n"
    )

    outputs = SI.write_scaffolds(root, ["第1集"])

    for path in outputs.values():
        assert Path(path).exists()
    ledger = json.loads(Path(outputs["story_integrity_ledger"]).read_text(encoding="utf-8"))
    scheduler = json.loads(Path(outputs["thread_scheduler"]).read_text(encoding="utf-8"))
    pilot = json.loads(Path(outputs["pilot_arc_contract"]).read_text(encoding="utf-8"))
    assert ledger["kind"] == "n2d_story_integrity_ledger"
    assert scheduler["kind"] == "n2d_thread_scheduler"
    assert pilot["kind"] == "n2d_pilot_arc_contract"


def test_write_scaffolds_updates_same_episode_thread_after_tail_rewrite():
    root = _mk_ep(
        "[镜头1·沈念·紧张·快] 我决定救她。\n"
        "[镜头2·沈念·痛苦·快] 因此我暴露身份。\n"
        "[镜头3·旁白·悬疑·快] 门外突然传来脚步。 🪝集尾\n"
    )
    SI.write_scaffolds(root, ["第1集"])
    voice_path = Path(root) / "脚本" / "第1集" / "voiceover.txt"
    voice_path.write_text(
        "[镜头1·沈念·紧张·快] 我决定救她。\n"
        "[镜头2·沈念·痛苦·快] 因此我暴露身份。\n"
        "[镜头3·旁白·悬疑·快] 门外突然响起陌生脚步。 🪝集尾\n",
        encoding="utf-8",
    )

    outputs = SI.write_scaffolds(root, ["第1集"])

    scheduler = json.loads(Path(outputs["thread_scheduler"]).read_text(encoding="utf-8"))
    assert len(scheduler["threads"]) == 1
    assert "陌生脚步" in scheduler["threads"][0]["open_question"]


def test_dialogue_not_advancing_warned():
    root = _mk_ep(
        "[镜头1·沈念·平静·慢] 从前这里有一座旧城。\n"
        "[镜头2·沈念·平静·慢] 所谓旧城，就是大家住过的地方。\n"
        "[镜头3·沈念·平静·慢] 因为年代久远，所以墙上长满青苔。\n"
    )

    result = SI.audit_episode(root, "第1集")

    assert "dialogue_not_advancing" in codes(result)


def test_detective_evidence_beats_count_as_advancing():
    root = _mk_ep(
        "[镜头1·旁白·阴冷·快] 那端着茶的人，到底是谁？\n"
        "[镜头2·坊正·赔笑·快] 记一笔，画个押，咱们好交差。\n"
        "[镜头3·沈砚·克制·慢] 这笔，我不画押。先把血和脚印查清。\n"
        "[镜头4·沈砚·压迫·快] 看鞋。看血。再看那碗茶，茶面一丝都没晃。\n"
        "[镜头5·沈砚·冷冽·快] 回来的，是剥了他脸、披着他皮的东西。 💥爽点\n"
    )

    result = SI.audit_episode(root, "第1集")

    assert "dialogue_not_advancing" not in codes(result)


def test_short_drama_pressure_phrases_count_as_advancing_and_motivated():
    root = _mk_ep(
        "[镜头1·张老大·粗声逼问·快] 站直。我问你，叫什么？多大了？\n"
        "[镜头2·贺平生·谨慎低头·快] 回张老大，我今年十四岁。\n"
        "[镜头3·张老大·威胁逼问·快] 什么灵根？说错一句，就滚出外门。\n"
        "[镜头4·贺平生·压低·快] 五行灵根。\n"
        "[镜头5·张老大·压迫·快] 水不满，我要拿你顶罪。\n"
    )

    result = SI.audit_episode(root, "第1集")

    assert "dialogue_not_advancing" not in codes(result)
    assert "motivation_vector_missing" not in codes(result)


def test_fake_cliffhanger_warned():
    root = _mk_ep(
        "[镜头1·旁白·平静·慢] 风吹过院子。\n"
        "[镜头2·旁白·平静·慢] 烛火晃了一下。\n"
        "[镜头3·旁白·惊恐·快] 门外突然传来脚步。 🪝集尾\n"
    )

    result = SI.audit_episode(root, "第1集")

    assert "fake_cliffhanger_risk" in codes(result)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
