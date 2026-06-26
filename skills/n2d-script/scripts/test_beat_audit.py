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


def test_storyboard_missing_first_screen_contract_flags():
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({"clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}]}, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "missing_first_3s_visual_hook" in c
    assert "missing_retention_promise_ledger" in c


def test_storyboard_first_screen_and_promise_ledger_pass():
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_conflict": "沈念脸部大特写，门外刀影压进画面",
            "content_proposition": "门外杀机逼近，观众要知道谁来害她",
            "onscreen_text": "谁在门外？",
            "muted_safe_proof": "刀影、惊恐特写和烧屏字幕同屏，关声也能读懂危机",
            "expected_metric": {"primary": "retention_3s", "target": 0.80},
            "muted_safe": True,
        },
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头1", "promise": "门外是谁", "payoff_due": "镜头3", "payoff_status": "paid", "payoff_clip": "镜头3", "payoff_evidence": "镜头3揭示亲妹妹"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "这局才刚开始", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "missing_first_3s_visual_hook" not in c
    assert "first_3s_not_muted_safe" not in c
    assert "missing_retention_promise_ledger" not in c
    assert "incomplete_retention_promise" not in c
    assert "missing_tail_promise" not in c


def test_incomplete_retention_promise_flags():
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_conflict": "冷开场大特写",
            "content_proposition": "门外危机",
            "onscreen_text": "门外是谁？",
            "muted_safe_proof": "大特写+字卡",
            "expected_metric": "retention_3s",
            "muted_safe": True,
        },
        "retention_promise_ledger": [{"hook_id": "OPEN_01"}],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "incomplete_retention_promise" in c
    assert "missing_tail_promise" in c


def test_emotion_visual_hook_without_conflict_passes():
    # GAP-2：悬念/情绪型冷开场用 visual_hook 描述，不含"冲突"，且 hook_type 在表内——不应报缺失/未知类型。
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_hook": "沈念含泪望向空荡的房间，一封未拆的信在桌上特写",
            "hook_type": "悬念",
            "content_proposition": "这封信会揭开她的身世",
            "onscreen_text": "这封信，藏着她不敢看的真相",
            "muted_safe_proof": "含泪表情+信件特写+标题卡，关声也读得懂悬念",
            "expected_metric": {"primary": "retention_3s", "target": 0.82},
            "muted_safe": True,
        },
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头1", "promise": "信里是什么", "payoff_due": "镜头3", "payoff_status": "paid", "payoff_clip": "镜头3", "payoff_evidence": "镜头3拆信揭身世"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "寄信人未露面", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "missing_first_3s_visual_hook" not in c
    assert "incomplete_first_3s_visual_hook" not in c
    assert "first_3s_not_muted_safe" not in c
    assert "first_3s_unknown_hook_type" not in c


def test_unknown_hook_type_warns():
    # GAP-2：hook_type 写了但不在分类表 → advisory warn（不阻断）。
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_hook": "沈念脸部大特写，门外刀影压进画面",
            "hook_type": "随便乱填的类型",
            "content_proposition": "门外杀机逼近",
            "onscreen_text": "谁在门外？",
            "muted_safe_proof": "刀影+惊恐特写+字幕，关声也读得懂",
            "expected_metric": {"primary": "retention_3s", "target": 0.80},
            "muted_safe": True,
        },
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头1", "promise": "门外是谁", "payoff_due": "镜头3", "payoff_status": "paid", "payoff_clip": "镜头3", "payoff_evidence": "镜头3揭示"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "主使未露", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert any(sev == "warn" and code == "first_3s_unknown_hook_type" for sev, code, _ in findings)


def test_monotone_hook_type_warns():
    # GAP-4：连续 ≥3 个同类型钩子（这里 hook_type 都为"危机"）→ advisory warn，不阻断。
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "retention_promise_ledger": [
            {"hook_id": "H1", "promise_type": "mid_hook", "hook_type": "危机", "opened_at": "镜头1", "promise": "p1", "payoff_due": "镜头2"},
            {"hook_id": "H2", "promise_type": "mid_hook", "hook_type": "危机", "opened_at": "镜头2", "promise": "p2", "payoff_due": "镜头3"},
            {"hook_id": "H3", "promise_type": "mid_hook", "hook_type": "危机", "opened_at": "镜头3", "promise": "p3", "payoff_due": "镜头4"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert any(sev == "warn" and code == "monotone_hook_type" for sev, code, _ in findings)


def test_rotated_hook_types_no_monotone_warn():
    # GAP-4：钩子类型轮换（危机→悬念→信息）不应报单调。
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "retention_promise_ledger": [
            {"hook_id": "H1", "promise_type": "mid_hook", "hook_type": "危机", "opened_at": "镜头1", "promise": "p1", "payoff_due": "镜头2"},
            {"hook_id": "H2", "promise_type": "mid_hook", "hook_type": "悬念", "opened_at": "镜头2", "promise": "p2", "payoff_due": "镜头3"},
            {"hook_id": "H3", "promise_type": "mid_hook", "hook_type": "信息", "opened_at": "镜头3", "promise": "p3", "payoff_due": "镜头4"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert not any(code == "monotone_hook_type" for _, code, _ in findings)


def test_weak_first_screen_schema_is_must():
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {"visual_hook": "旧字段冷开场大特写", "muted_safe": True},
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头1", "promise": "门外是谁", "payoff_due": "第2集"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "主使是谁", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert any(sev == "must" and code == "incomplete_first_3s_visual_hook" for sev, code, _ in findings)


def test_first_screen_expected_metric_target_is_hard_audited():
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_conflict": "沈念脸部大特写，门外刀影压进画面",
            "content_proposition": "门外杀机逼近，观众要知道谁来害她",
            "onscreen_text": "谁在门外？",
            "muted_safe_proof": "刀影、惊恐特写和烧屏字幕同屏，关声也能读懂危机",
            "expected_metric": {"primary": "retention_3s", "target": 0.60},
            "muted_safe": True,
        },
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头1", "promise": "门外是谁", "payoff_due": "第2集"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "主使是谁", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert "invalid_first_3s_expected_metric" in codes(findings)


def test_first_screen_caption_overload_is_must():
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_conflict": "沈念脸部大特写，门外刀影压进画面",
            "content_proposition": "门外杀机逼近，观众要知道谁来害她",
            "onscreen_text": "谁在门外谁在门外谁在门外谁在门外谁在门外谁在门外谁在门外谁在门外谁在门外谁在门外",
            "muted_safe_proof": "刀影、惊恐特写和烧屏字幕同屏，关声也能读懂危机",
            "expected_metric": {"primary": "retention_3s", "target": 0.80},
            "muted_safe": True,
        },
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头1", "promise": "门外是谁", "payoff_due": "第2集"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "主使是谁", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert "first_3s_caption_too_dense" in codes(findings)


def test_first_six_seconds_without_beat_hook_is_must():
    vo = """[镜头1·沈念·平静·慢] 她慢慢走进屋里。
[镜头2·旁白·低沉] 屋里很安静。
[镜头3·沈念·惊恐·快] 门外刀影压近，危机来了！  ⚡钩子
[镜头4·沈念·阴狠·慢] 这局，才刚开始。  🪝集尾
"""
    root = _mk_ep(vo)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_conflict": "沈念脸部大特写，门外刀影压进画面",
            "content_proposition": "门外杀机逼近，观众要知道谁来害她",
            "onscreen_text": "谁在门外？",
            "muted_safe_proof": "刀影、惊恐特写和烧屏字幕同屏，关声也能读懂危机",
            "expected_metric": {"primary": "retention_3s", "target": 0.80},
            "muted_safe": True,
        },
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头3", "promise": "门外是谁", "payoff_due": "第2集"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "主使是谁", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "慢开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert "missing_first_6s_beat_hook" in codes(findings)


def test_due_promise_requires_payoff_evidence():
    root = _mk_ep(GOOD)
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_conflict": "冷开场大特写",
            "content_proposition": "门外危机",
            "onscreen_text": "门外是谁？",
            "muted_safe_proof": "大特写+字卡",
            "expected_metric": "retention_3s",
            "muted_safe": True,
        },
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头1", "promise": "门外是谁", "payoff_due": "第1集"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "主使是谁", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert "due_promise_without_payoff_evidence" in codes(findings)


def test_creative_priors_must_be_acknowledged():
    root = _mk_ep(GOOD)
    prod = Path(root) / "生产数据"
    prod.mkdir()
    (prod / "creative_priors.json").write_text(json.dumps({
        "kind": "n2d_creative_priors",
        "priors": {"opening_variant": {"winner": "cold_open_first", "paired_lift": 0.1}},
    }, ensure_ascii=False), encoding="utf-8")
    sb = Path(root) / "脚本" / "第1集" / "storyboard.json"
    sb.write_text(json.dumps({
        "first_3s_visual_hook": {
            "visual_conflict": "冷开场大特写",
            "content_proposition": "门外危机",
            "onscreen_text": "门外是谁？",
            "muted_safe_proof": "大特写+字卡",
            "expected_metric": "retention_3s",
            "muted_safe": True,
        },
        "retention_promise_ledger": [
            {"hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "镜头1", "promise": "门外是谁", "payoff_due": "第2集"},
            {"hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "镜头4", "promise": "主使是谁", "delayed_payoff_ep": "第2集"},
        ],
        "clips": [{"id": "C1", "rhythm": "冷开场", "duration": 3}],
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert "creative_prior_not_acknowledged" in codes(findings)

    (Path(root) / "脚本" / "第1集" / "applied_creative_priors.json").write_text(json.dumps({
        "applied_creative_priors": {"opening_variant": {"winner": "cold_open_first"}},
    }, ensure_ascii=False), encoding="utf-8")
    findings, _ = B.audit_episode(root, "第1集")
    assert "creative_prior_not_acknowledged" not in codes(findings)


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


# ── 看点高潮位复核（北极星看点④·阶段2·需真实镜头时长）──────────────
def test_highlight_silent_without_timings():
    # 拆集层无 镜头时长.json → 静默跳过，不产任何行/finding
    root = _mk_ep(GOOD)
    rows, findings = B.highlight_climax_profile(root)
    assert rows == [] and findings == []


def test_highlight_healthy_with_endhook_tail():
    # 💥在镜3(44%)、镜4 是 🪝集尾钩撑张力 → 不报 too_early
    root = _mk_ep(GOOD, {"镜头1": 3, "镜头2": 4, "镜头3": 4, "镜头4": 5})
    rows, findings = B.highlight_climax_profile(root)
    assert rows[0]["has_highlight"] is True
    assert "highlight_too_early" not in codes(findings)
    assert "no_highlight_beat" not in codes(findings)


def test_highlight_too_early_flagged():
    vo = """[镜头1·沈念·惊恐·快] 门开了！  ⚡钩子
[镜头2·沈念·痛快·快] 一拳打飞了他！  💥爽点
[镜头3·旁白·平静] 夜色渐深。
[镜头4·旁白·平静] 她坐在窗边。
[镜头5·旁白·平静] 茶水凉了。
[镜头6·旁白·平静] 风停了。
"""
    secs = {f"镜头{i}": 5 for i in range(1, 7)}
    root = _mk_ep(vo, secs)
    rows, findings = B.highlight_climax_profile(root)
    assert "highlight_too_early" in codes(findings)
    assert rows[0]["climax_pos"] < 0.45 and rows[0]["tail_has_hook"] is False


def test_highlight_no_beat_flagged():
    vo = """[镜头1·旁白·平静] 清晨到了。
[镜头2·旁白·平静] 她起床洗漱。
[镜头3·旁白·平静] 吃了早饭出门。
"""
    root = _mk_ep(vo, {"镜头1": 5, "镜头2": 5, "镜头3": 5})
    rows, findings = B.highlight_climax_profile(root)
    assert "no_highlight_beat" in codes(findings)
    assert rows[0]["has_highlight"] is False


# ── A1 多层节奏间距栅格（爆点≤30s / 情绪峰≤180s）─────────────────────────────
def test_worst_cadence_gap_pure():
    beats = [{"shot": 1, "hooks": {B.HOOK_PAYOFF}, "text": "赢了", "emotion": "痛快"},
             {"shot": 5, "hooks": {B.HOOK_PAYOFF}, "text": "翻盘", "emotion": "痛快"}]
    starts = {1: 0.0, 5: 36.0}
    w = B.worst_cadence_gap(beats, starts, B._is_blast, 30.0)
    assert w == (0.0, 36.0, 36.0)
    # <2 拍 → None（间距无意义）
    assert B.worst_cadence_gap(beats[:1], starts, B._is_blast, 30.0) is None
    # 间距未超阈 → None
    assert B.worst_cadence_gap(beats, {1: 0.0, 5: 20.0}, B._is_blast, 30.0) is None


def test_cadence_blast_flags_far_apart_detonations():
    # 钩子每<20s（hook 层过），但两次💥相隔 36s → cadence_blast warn
    vo = """[镜头1·沈念·痛快·快] 反击赢了！  💥爽点
[镜头2·沈念·惊恐·快] 危机又来了！  ⚡钩子
[镜头3·沈念·愤怒·快] 还有埋伏！  ⚡钩子
[镜头4·沈念·痛快·快] 终于翻盘！  💥爽点
[镜头5·沈念·阴狠·慢] 没完。  🪝集尾
"""
    root = _mk_ep(vo, {"镜头1": 6, "镜头2": 15, "镜头3": 15, "镜头4": 8, "镜头5": 5})
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "cadence_blast" in c       # 💥@0 → 💥@36，间距 36>30
    assert "hook_gap" not in c        # 钩子层（⚡∪💥）间距都 ≤20，不误报


def test_cadence_blast_not_flagged_when_dense():
    # GOOD：💥/反转拍密集（<30s）→ 不报 cadence_blast
    root = _mk_ep(GOOD, {"镜头1": 3, "镜头2": 4, "镜头3": 4, "镜头4": 5})
    findings, _ = B.audit_episode(root, "第1集")
    assert "cadence_blast" not in codes(findings)


def test_cadence_blast_silent_without_real_seconds():
    # 无 镜头时长.json → 多层栅格不激活（拆集层不臆造秒）
    vo = """[镜头1·沈念·痛快·快] 赢了！  💥爽点
[镜头2·沈念·痛快·快] 又赢！  💥爽点
"""
    root = _mk_ep(vo)
    findings, _ = B.audit_episode(root, "第1集")
    assert "cadence_blast" not in codes(findings)


def test_cadence_peak_flags_long_gap_between_peaks_longform():
    # 长剪：两个峰值情绪相隔 >180s → cadence_peak info（漫剧短集天然不触发）
    vo = """[镜头1·沈念·愤怒·快] 怒火中烧！  ⚡钩子
[镜头2·旁白·平静·慢] 漫长的平稳叙事。
[镜头3·沈念·震惊·快] 真相震撼！  💥爽点
"""
    root = _mk_ep(vo, {"镜头1": 5, "镜头2": 200, "镜头3": 5})
    findings, _ = B.audit_episode(root, "第1集")
    c = codes(findings)
    assert "cadence_peak" in c        # 愤怒@0 → 震惊@205，间距 205>180
