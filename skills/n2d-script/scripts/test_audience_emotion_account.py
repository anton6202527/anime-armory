#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import audience_emotion_account as aea  # noqa: E402


def test_audience_emotion_account_counts_debts_and_hook(tmp_path: Path) -> None:
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text(
        "她必须查清秘密，众人开始怀疑她。\n"
        "门外突然传来脚步。🪝\n",
        encoding="utf-8",
    )

    report = aea.build_account(tmp_path, "第1集")

    assert report["kind"] == aea.KIND
    assert report["account"]["curiosity_debt"] >= 1
    assert report["account"]["trust_debt"] >= 1
    assert report["account"]["ending_hook"] is True


def test_audience_emotion_account_warns_curiosity_without_payoff(tmp_path: Path) -> None:
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text("她听说一个秘密，但无人回应。\n夜色很静。\n", encoding="utf-8")

    report = aea.build_account(tmp_path, "第1集")

    assert any(f["code"] == "curiosity_without_hook_or_payoff" for f in report["findings"])
    jp, mp = aea.write_outputs(tmp_path, "第1集", report)
    assert json.loads(jp.read_text(encoding="utf-8"))["kind"] == aea.KIND
    assert "观众情绪账本" in mp.read_text(encoding="utf-8")
