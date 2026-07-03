#!/usr/bin/env python3
"""antecedent_audit 单测（前因依赖 / 删集跳章）。
cd skills/n2d-script/scripts && python -m pytest test_antecedent_audit.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import json

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import antecedent_audit as A  # noqa: E402


def _mk(eps):
    d = Path(__import__("tempfile").mkdtemp())
    for ep, vo in eps.items():
        epd = d / "脚本" / ep
        epd.mkdir(parents=True)
        (epd / "voiceover.txt").write_text(vo, encoding="utf-8")
    return str(d)


def codes(res):
    return {f["code"] for f in res["findings"]}


def test_interior_gaps_pure():
    assert A.interior_gaps([1, 2, 3]) == []
    assert A.interior_gaps([1, 2, 4, 5]) == [3]
    assert A.interior_gaps([2, 5]) == [3, 4]
    assert A.interior_gaps([50, 51, 52]) == []   # 窗口起点不算缝隙
    assert A.interior_gaps([]) == []


def test_entities_extraction():
    text = "[镜头1·沈念·惊恐·快] 王爷救我！\n[镜头2·旁白·低沉] 那枚【玉佩】发着光。"
    ents = A.entities_in_text(text)
    assert "沈念" in ents and "王爷" in ents and "玉佩" in ents
    assert "旁白" not in ents


def test_sequential_no_gap_passes():
    d = _mk({
        "第1集": "[镜头1·沈念·惊恐·快] 危机来了！\n",
        "第2集": "[镜头1·沈念·冷冽·快] 我要反击。\n",
        "第3集": "[镜头1·沈念·决绝·快] 真相揭开。\n",
    })
    res = A.audit(d, "第3集")
    assert res["ok"] and not res["findings"]


def test_deleted_interior_episode_flagged():
    # 第3集被删（1,2,4,5）→ 第4集是缝隙后第一集 → antecedent_gap warn
    d = _mk({
        "第1集": "[镜头1·沈念·惊恐·快] 危机来了！\n",
        "第2集": "[镜头1·沈念·冷冽·快] 我要反击。\n",
        "第4集": "[镜头1·陆沉·决绝·快] 朝堂之上风云变。\n",
        "第5集": "[镜头1·陆沉·阴狠·快] 大局已定。\n",
    })
    res4 = A.audit(d, "第4集")
    assert not res4["ok"] and "antecedent_gap" in codes(res4)
    assert res4["findings"][0]["missing_episodes"] == [3]
    # 第4集首现「陆沉」断档前没出现过 → entity_first_seen_after_gap (info)
    assert "entity_first_seen_after_gap" in codes(res4)
    # 第5集不再为同一缝隙重复刷 antecedent_gap
    res5 = A.audit(d, "第5集")
    assert "antecedent_gap" not in codes(res5)


def test_window_start_not_flagged():
    # 中段开工：从第50集起，前面没有留存集 → 不报断档
    d = _mk({
        "第50集": "[镜头1·沈念·惊恐·快] 危机来了！\n",
        "第51集": "[镜头1·沈念·冷冽·快] 反击。\n",
    })
    res = A.audit(d, "第50集")
    assert res["ok"] and not res["findings"]


def test_consecutive_gap_run():
    # 第3、4集都删（1,2,5）→ 第5集报缺 3/4
    d = _mk({
        "第1集": "[镜头1·沈念·惊恐·快] 危机！\n",
        "第2集": "[镜头1·沈念·冷冽·快] 反击。\n",
        "第5集": "[镜头1·沈念·决绝·快] 结局。\n",
    })
    res = A.audit(d, "第5集")
    assert res["findings"][0]["missing_episodes"] == [3, 4]


def test_episode_scope_intentional_gaps_do_not_block_window():
    # 保留早期样例集，但正式窗口从第5集开始；第3/4集缺失是有意窗口，不应 strict 阻断。
    d = _mk({
        "第1集": "[镜头1·沈念·惊恐·快] 危机！\n",
        "第2集": "[镜头1·沈念·冷冽·快] 反击。\n",
        "第5集": "[镜头1·陆沉·决绝·快] 朝堂之上风云变。\n",
    })
    scope = Path(d) / "脚本" / "episode_scope.json"
    scope.write_text(json.dumps({"window_start": "第5集"}, ensure_ascii=False), encoding="utf-8")
    res = A.audit(d, "第5集")
    assert res["ok"]
    assert "antecedent_gap" not in codes(res)
    assert res["stats"]["intentional_gaps"] == [3, 4]


def test_episode_scope_explicit_gap_do_not_block():
    d = _mk({
        "第1集": "[镜头1·沈念·惊恐·快] 危机！\n",
        "第3集": "[镜头1·沈念·决绝·快] 结局。\n",
    })
    (Path(d) / "脚本" / "episode_scope.json").write_text(
        json.dumps({"intentional_gaps": ["第2集"]}, ensure_ascii=False), encoding="utf-8"
    )
    res = A.audit(d, "第3集")
    assert res["ok"]
    assert res["stats"]["active_gaps"] == []


def test_series_report():
    d = _mk({
        "第1集": "[镜头1·沈念·惊恐·快] 危机！\n",
        "第3集": "[镜头1·陆沉·冷冽·快] 王爷登场。\n",
    })
    res = A.audit_series(d)
    assert res["interior_gaps"] == [2]
    assert "interior_gaps" in {f["code"] for f in res["findings"]}


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
