#!/usr/bin/env python3
"""series_balance 单测（剧级虎头蛇尾曲线）。
cd skills/n2d/n2d-script/scripts && python -m pytest test_series_balance.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import series_balance as S  # noqa: E402


def _ep(hooks, shots, reversal=True):
    """造一集 voiceover：前 `hooks` 镜带钩子标记，其余无；最后一镜按需带反转词。"""
    lines = []
    for i in range(1, shots + 1):
        mark = "⚡钩子" if i <= hooks else ""
        txt = "原来竟是她" if (reversal and i == shots) else f"第{i}句台词"
        lines.append(f"[镜头{i}·沈念·惊恐·快] {txt} {mark}")
    return "\n".join(lines) + "\n"


def _mk(eps):
    d = tempfile.mkdtemp()
    for ep, vo in eps.items():
        epd = Path(d) / "脚本" / ep
        epd.mkdir(parents=True)
        (epd / "voiceover.txt").write_text(vo, encoding="utf-8")
    return d


def codes(res):
    return {f["code"] for f in res["findings"]}


def test_thirds_split():
    rows = [{"i": i} for i in range(9)]
    f, m, b = S.thirds(rows)
    assert len(f) == 3 and len(m) == 3 and len(b) == 3


def test_too_few_episodes_info_only():
    d = _mk({f"第{i}集": _ep(2, 5) for i in range(1, 4)})
    res = S.analyze(d)
    assert "too_few_episodes" in codes(res)


def test_placeholder_voiceovers_are_skipped():
    d = _mk({
        "第1集": _ep(3, 6),
        "第2集": "# 占位\n# 待精修：按镜头顺序填写旁白/台词，标注角色与情绪。\n",
        "第3集": "# 占位\n# 待精修：按镜头顺序填写旁白/台词，标注角色与情绪。\n",
    })
    res = S.analyze(d)
    assert res["summary"]["episodes"] == 1
    assert res["summary"]["discovered_episodes"] == 3
    assert "placeholder_episodes_skipped" in codes(res)
    assert "too_few_episodes" in codes(res)


def test_balanced_series_no_warn():
    d = _mk({f"第{i}集": _ep(3, 6) for i in range(1, 10)})
    res = S.analyze(d)
    assert "balanced" in codes(res)
    assert not any(f["severity"] == "warn" for f in res["findings"])


def test_front_loaded_decline_flagged():
    # 前 3 集钩子多，后 3 集钩子骤减 → back_loaded_decline(_severe)
    eps = {}
    for i in range(1, 4):
        eps[f"第{i}集"] = _ep(5, 6)      # 前段密
    for i in range(4, 7):
        eps[f"第{i}集"] = _ep(2, 6)      # 中段
    for i in range(7, 10):
        eps[f"第{i}集"] = _ep(0, 6, reversal=False)   # 后段稀 + 无反转
    res = S.analyze(eps_dir := _mk(eps))
    c = codes(res)
    assert "back_loaded_decline_severe" in c or "back_loaded_decline" in c
    assert "reversal_drought_late" in c


def test_curve_compares_density_not_raw_hook_count():
    eps = {}
    for i in range(1, 4):
        eps[f"第{i}集"] = _ep(4, 8)   # density .5
    for i in range(4, 7):
        eps[f"第{i}集"] = _ep(3, 6)   # density .5
    for i in range(7, 10):
        eps[f"第{i}集"] = _ep(2, 4)   # density .5, raw count lower
    res = S.analyze(_mk(eps))
    assert "back_loaded_decline" not in codes(res)
    assert "back_loaded_decline_severe" not in codes(res)
    assert res["summary"]["front"]["avg_hook_density"] == res["summary"]["back"]["avg_hook_density"]


def test_strict_exit_on_severe():
    eps = {}
    for i in range(1, 4):
        eps[f"第{i}集"] = _ep(6, 6)
    for i in range(4, 7):
        eps[f"第{i}集"] = _ep(3, 6)
    for i in range(7, 10):
        eps[f"第{i}集"] = _ep(0, 6, reversal=False)
    d = _mk(eps)
    assert S.main([d, "--strict", "--json"]) == 1
    assert S.main([d, "--json"]) == 0   # 非 strict 不阻断


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
