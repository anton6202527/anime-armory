#!/usr/bin/env python3
"""Tests for beat_audit.py (Gap4/5 intra-episode retention + 同质化).

Run from this script's own directory:
    cd skills/n2d-script/scripts && python -m pytest test_beat_audit.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import beat_audit as B  # noqa: E402


def _mk_ep(voiceover, secs=None, ep="第1集"):
    d = tempfile.mkdtemp()
    epd = Path(d) / "脚本" / ep
    epd.mkdir(parents=True)
    (epd / "voiceover.txt").write_text(voiceover, encoding="utf-8")
    if secs:
        (epd / "镜头时长.json").write_text(json.dumps(secs, ensure_ascii=False), encoding="utf-8")
    return d


GOOD = """[镜头1·沈念·惊恐·快] 门被推开了！  ⚡钩子
[镜头2·旁白·低沉] 原来害她的是亲妹妹。
[镜头3·沈念·冷冽·快] 我要让真相大白。  💥爽点
[镜头4·沈念·阴狠·慢] 这局，才刚开始。  🪝集尾
"""


def codes(findings):
    return {c for _, c, _ in findings}


def test_good_episode_passes_core_checks():
    root = _mk_ep(GOOD, {"镜头1": 3, "镜头2": 4, "镜头3": 4, "镜头4": 5})
    findings, stats = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "no_reversal" not in c
    assert "no_ending_hook" not in c
    assert "no_info_payoff" not in c          # 镜2 给了信息回报
    assert stats["has_reversal"] and stats["has_ending_hook"]


def test_pure_emotion_flags_no_info_payoff():
    vo = """[镜头1·沈念·愤怒·快] 打回去！  ⚡钩子
[镜头2·沈念·痛快·快] 反击赢了！  💥爽点
[镜头3·沈念·阴狠·慢] 报仇雪恨。  🪝集尾
"""
    root = _mk_ep(vo)
    findings, _ = B.audit_episode(root, "第1集")
    assert "no_info_payoff" in codes(findings)


def test_missing_ending_and_reversal_flagged():
    vo = """[镜头1·沈念·平静·慢] 今天天气不错。
[镜头2·沈念·平静·慢] 我们去散步吧。
"""
    root = _mk_ep(vo)
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "no_ending_hook" in c and "no_reversal" in c


def test_hook_gap_uses_real_seconds():
    vo = """[镜头1·沈念·惊恐·快] 危机来了！  ⚡钩子
[镜头2·旁白·低沉] 漫长的回忆与铺垫。
[镜头3·沈念·冷冽·快] 真相揭开。  💥爽点
[镜头4·沈念·阴狠·慢] 结束了？  🪝集尾
"""
    # 镜2 给 30s → 钩子间隔超 20s
    root = _mk_ep(vo, {"镜头1": 3, "镜头2": 30, "镜头3": 4, "镜头4": 5})
    findings, _ = B.audit_episode(root, "第1集")
    assert "hook_gap" in codes(findings)


def test_unmarked_ending_cliffhanger_downgraded_not_false_warn():
    # 集尾有 cliffhanger 内容但漏标 🪝 → ending_hook_unmarked(info)，不误报 no_ending_hook(warn)
    vo = """[镜头1·沈念·惊恐·快] 危机来了！
[镜头2·旁白·低沉] 原来害她的是亲妹妹。
[镜头3·沈念·决绝·快] 真相揭开。
[镜头4·沈念·阴狠·慢] 到底是谁在背后？
"""
    root = _mk_ep(vo)
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "no_ending_hook" not in c
    assert "ending_hook_unmarked" in c


def test_flat_emotion_arc_flagged():
    # ≥6 拍情绪全是单一/平缓 → flat_emotion_arc warn
    vo = "".join(f"[镜头{i}·沈念·平静·慢] 日常对话第{i}句。\n" for i in range(1, 8))
    root = _mk_ep(vo)
    findings, _ = B.audit_episode(root, "第1集")
    assert "flat_emotion_arc" in codes(findings)


def test_varied_emotion_arc_not_flagged():
    # ≥6 拍情绪有起伏 + 有峰值 → 不报 flat_emotion_arc
    emos = ["惊恐", "低沉", "冷冽", "痛快", "阴狠", "决绝"]
    vo = "".join(f"[镜头{i+1}·沈念·{e}·快] 第{i+1}拍台词，原来竟是真相。\n" for i, e in enumerate(emos))
    root = _mk_ep(vo)
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "flat_emotion_arc" not in c
    assert "no_emotion_peak" not in c


def _mk_series(eps_text):
    d = tempfile.mkdtemp()
    for ep, vo in eps_text.items():
        epd = Path(d) / "脚本" / ep
        epd.mkdir(parents=True)
        (epd / "voiceover.txt").write_text(vo, encoding="utf-8")
    return d


def test_p2_resolved_ending_flagged():
    # 第1集结尾收得太干净（无 cliffhanger）→ p2_resolved_ending
    d = _mk_series({
        "第1集": "[镜头1·沈念·平静·慢] 开始了。\n[镜头2·沈念·平静·慢] 今天一切都平静收场。\n",
        "第2集": "[镜头1·沈念·惊恐·快] 危机来了！\n[镜头2·沈念·冷冽·快] 我必须反击。\n",
    })
    _eps, _states, findings, _rate = B.cold_open_chain(d)
    assert any(c == "p2_resolved_ending" for _s, c, _m in findings)


def test_p2_good_chain_no_finding():
    d = _mk_series({
        "第1集": "[镜头1·沈念·平静·慢] 开始了。\n[镜头2·沈念·惊恐·快] 门突然被推开，到底是谁？！\n",
        "第2集": "[镜头1·沈念·惊恐·快] 危机来了！\n[镜头2·沈念·冷冽·快] 我必须逃。\n",
    })
    _eps, _states, findings, rate = B.cold_open_chain(d)
    assert findings == []
    assert rate == 1.0


def test_hook_link_entity_overlap():
    # 上集集尾出现「沈念/王爷」，下集冷开场也有「沈念」→ linked
    pa = [{"role": "沈念", "text": "王爷救我！", "emotion": "惊恐", "hooks": set()}]
    cur = [{"role": "沈念", "text": "我醒了。", "emotion": "茫然", "hooks": set()}]
    link = B.hook_link(pa, cur)
    assert link["linked"] and link["has_signal"]


def test_hook_link_thread_switch_breaks():
    pa = [{"role": "沈念", "text": "门后是谁？！", "emotion": "惊恐", "hooks": set()}]
    cur = [{"role": "陆沉", "text": "朝堂之上风云变。", "emotion": "平静", "hooks": set()}]
    link = B.hook_link(pa, cur)
    assert link["has_signal"] and not link["linked"]


def test_cross_ep_hook_break_flagged_in_episode():
    # 第1集集尾钩抛出「沈念」，第2集冷开场切到完全无关的「陆沉/朝堂」→ cross_ep_hook_break
    d = _mk_series({
        "第1集": "[镜头1·沈念·惊恐·快] 门突然被推开！\n[镜头2·沈念·阴狠·慢] 到底是谁要害我？！\n",
        "第2集": "[镜头1·陆沉·惊恐·快] 朝堂之上杀机骤起！\n[镜头2·陆沉·冷冽·快] 我必须逃。\n",
    })
    findings, _ = B.audit_episode(d, "第2集")
    assert "cross_ep_hook_break" in codes(findings)


def test_cross_ep_hook_bridge_allows_delayed_payoff():
    d = _mk_series({
        "第1集": "[镜头1·沈念·惊恐·快] 门突然被推开！\n[镜头2·沈念·阴狠·慢] 到底是谁要害我？！\n",
        "第2集": "[镜头1·陆沉·惊恐·快] 朝堂之上杀机骤起！\n[镜头2·陆沉·冷冽·快] 我必须逃。\n",
    })
    sb = Path(d) / "脚本" / "第2集" / "storyboard.json"
    sb.write_text(json.dumps({
        "hook_bridge": {
            "from_episode": "第1集",
            "thread_id": "assassin_reveal",
            "delayed_payoff_ep": "第3集",
            "bridge_text": "第2集先切朝堂 B 线，结尾回到门后刺客线索。",
        }
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(d, "第2集")
    assert "cross_ep_hook_break" not in codes(findings)


def test_cross_ep_hook_linked_no_break():
    # 第2集冷开场接住第1集集尾的「沈念」→ 不报 cross_ep_hook_break
    d = _mk_series({
        "第1集": "[镜头1·沈念·惊恐·快] 门突然被推开！\n[镜头2·沈念·阴狠·慢] 到底是谁要害我？！\n",
        "第2集": "[镜头1·沈念·惊恐·快] 我被困住了，危机来了！\n[镜头2·沈念·冷冽·快] 必须反击。\n",
    })
    findings, _ = B.audit_episode(d, "第2集")
    assert "cross_ep_hook_break" not in codes(findings)


def test_cold_open_chain_accepts_hook_bridge():
    d = _mk_series({
        "第1集": "[镜头1·沈念·平静·慢] 开始了。\n[镜头2·沈念·惊恐·快] 门后是谁？！\n",
        "第2集": "[镜头1·陆沉·惊恐·快] 朝堂危机来了！\n[镜头2·陆沉·冷冽·快] 我必须反击。\n",
    })
    (Path(d) / "脚本" / "第2集" / "storyboard.json").write_text(json.dumps({
        "clips": [{
            "id": "C01",
            "continuity": {
                "hook_bridge": {
                    "from_episode": "第1集",
                    "answers_prev_hook": True,
                    "bridge_text": "朝堂线揭示门后主使的政治来源。",
                }
            }
        }]
    }, ensure_ascii=False), encoding="utf-8")
    _eps, _states, findings, rate = B.cold_open_chain(d)
    assert all(c != "cross_ep_hook_break" for _s, c, _m in findings)
    assert rate == 1.0


def test_first_episode_no_incoming_link_check():
    # 第1集没有上一集 → 不产生 cross_ep_hook_break
    root = _mk_ep(GOOD)
    findings, _ = B.audit_episode(root, "第1集")
    assert "cross_ep_hook_break" not in codes(findings)


def test_series_homogenization_detects_dupes():
    d = tempfile.mkdtemp()
    same = """[镜头1·沈念·愤怒·快] 反击打脸！  ⚡钩子
[镜头2·沈念·痛快·快] 逆袭翻盘碾压！  💥爽点
[镜头3·沈念·阴狠·慢] 原来竟是她。  🪝集尾
"""
    for i in (1, 2):
        epd = Path(d) / "脚本" / f"第{i}集"
        epd.mkdir(parents=True)
        (epd / "voiceover.txt").write_text(same, encoding="utf-8")
    eps, dups = B.audit_series(d)
    assert len(eps) == 2 and dups and dups[0][2] >= 0.8


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))


def test_mid_arc_weight_peaks_middle():
    assert B.mid_arc_weight(0, 5) == 0.0      # 首集
    assert B.mid_arc_weight(4, 5) == 0.0      # 末集
    assert B.mid_arc_weight(2, 5) == 1.0      # 正中
    assert B.mid_arc_weight(0, 1) == 0.0      # 单集无中段


def test_token_entropy_monotonic():
    assert B.token_entropy("") == 0.0
    assert B.token_entropy("aaaa") == 0.0     # 单字符=0 熵
    assert B.token_entropy("abcd") > B.token_entropy("aabb")  # 越均匀越高


def test_narrative_risk_score_geometric():
    # 两者都高才高分；任一为 0 → 0
    assert B.narrative_risk_score(0.0, 5.0, 5.0) == 0.0       # 端点(mid=0)
    assert B.narrative_risk_score(1.0, 0.0, 5.0) == 0.0       # 零熵
    assert B.narrative_risk_score(1.0, 5.0, 5.0) == 1.0       # 中段+最高熵
    mid = B.narrative_risk_score(1.0, 2.5, 5.0)
    assert 0.0 < mid < 1.0


def test_narrative_risk_profile_prioritizes_mid_high_entropy(tmp_path):
    # 6 集：中段集给高熵长文本，端点集给低熵短文本 → 中段集应进优先表
    import pathlib
    for i in range(1, 7):
        d = pathlib.Path(tmp_path) / "脚本" / f"第{i}集"
        d.mkdir(parents=True)
        if i in (3, 4):
            text = "".join(chr(0x4e00 + j) for j in range(60))  # 高熵：60 个不同字
            line = f"[镜头1·旁白·平静] {text}"
        else:
            line = "[镜头1·旁白·平静] 好好好好好好"               # 低熵：单字重复
        (d / "voiceover.txt").write_text(line + "\n", encoding="utf-8")
    eps, ranked, findings = B.narrative_risk_profile(str(tmp_path))
    assert len(eps) == 6
    flagged = {f[2].split("：")[0] for f in findings}
    assert "第3集" in flagged or "第4集" in flagged       # 中段高熵集被标优先
    assert all(f[0] == "info" for f in findings)          # report-only
