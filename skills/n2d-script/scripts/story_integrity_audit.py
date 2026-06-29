#!/usr/bin/env python3
"""story_integrity_audit.py — 剧情好看度文本期体检。

覆盖拆集/每集剧本中最容易被“有钩子”掩盖的几条叙事问题：

  1. 选择→后果链：本集是否有角色做出选择，并产生代价/状态变化。
  2. 角色动机向量：核心出场角色有没有当前目标/恐惧/筹码/立场信号。
  3. A/B/C 线调度：集尾钩或疑问是否进入 thread_scheduler。
  4. 前几集追剧契约：前 3-5 集是否登记系列承诺、主角欲望、首个兑现等。
  5. 假 cliffhanger：集尾钩是否有前因/实体/兑现线程支撑。
  6. 对白推进功能：对白是否连续解释但不推动选择、揭示、施压或关系变化。

默认 report-only：warn/info 不阻断；--strict 才把 warn 当失败。没有任何时长硬门。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
BRACKET_RE = re.compile(r"【([^】]{1,24})】|《([^》]{1,24})》")
TITLE_RE = re.compile(
    r"[一-鿿]{0,4}(?:娘娘|王爷|师尊|陛下|公主|太子|小姐|少爷|夫人|长老|"
    r"师兄|师姐|宗主|皇后|贵妃|将军|侍卫|掌门|大人|阁下|城主|帝君|魔尊)"
)

HOOK_ENDING = "🪝"
HOOK_PAYOFF = "💥"
HOOK_NORMAL = "⚡"
HOOK_CONTENT_RE = re.compile(
    r"(危机|来了|出事|不好了|危险|追来|杀|逃|爆|突然|悬|未完|待续|下一[集章]|"
    r"怎么会|不可能|是谁|到底|为什么|揭|真相|秘密|发现|生死|绝境|反杀|打脸|逆袭)"
)
CHOICE_RE = re.compile(
    r"(决定|选择|选了|宁愿|必须|不能再|我来|我要|我会|我偏要|答应|拒绝|放弃|赌|"
    r"留下|离开|逃走|救|杀|反击|背叛|认下|承认|交出|隐瞒|公开|揭穿|出手)"
)
CONSEQUENCE_RE = re.compile(
    r"(因此|于是|从此|代价|后果|失去|得到|夺回|暴露|触发|开启|关闭|升级|突破|"
    r"受伤|重伤|中毒|被抓|被困|死亡|反噬|惹怒|关系破裂|决裂|信任|背叛|通缉|封锁)"
)
GOAL_RE = re.compile(
    r"(为了|想要|要去|必须|誓要|不能让|守住|查清|找到|夺回|保护|救出|证明|复仇|报仇|"
    r"活下去|逃出去|赢|成亲|退婚|升级|突破|隐瞒|揭穿)"
)
FEAR_RE = re.compile(r"(害怕|担心|恐惧|怕|不敢|不能暴露|一旦.*就|否则|来不及|会死|会输|会失去)")
LEVERAGE_RE = re.compile(r"(证据|令牌|玉佩|法宝|把柄|筹码|钥匙|线索|系统|面板|名单|账册|密信)")
STANCE_RE = re.compile(r"(信任|怀疑|恨|喜欢|心动|护|背叛|敌人|盟友|师徒|夫妻|主仆|宿敌|仇人)")
REVEAL_RE = re.compile(r"(原来|竟是|真相|身世|秘密|发现|揭穿|暴露|证据|线索|其实|来历|名字)")
PRESSURE_RE = re.compile(r"(威胁|逼|跪|交出|否则|休想|命令|敢|杀了|抓住|围住|质问|审问)")
CONCEAL_RE = re.compile(r"(隐瞒|瞒|骗|假装|装作|不能说|秘密|藏起|不让.*知道)")
RELATION_RE = re.compile(r"(喜欢|恨|爱|夫君|妻子|师父|师尊|背叛|信任|救你|护你|认作|仇|恩情)")
ACTION_RE = re.compile(r"(冲|拔剑|跪|推门|逃|追|打|斩|抓|挡|抱|吻|转身|出手|跪下|站起|砸|撕)")
EXPOSITION_RE = re.compile(r"(旁白|从前|当年|曾经|所谓|这就是|因为|所以|换句话说|也就是说|原本)")
QUESTION_RE = re.compile(r"(到底是谁|究竟是谁|是谁[？?]|为什么[？?]|为何[？?]|怎么办|怎么会|不对劲)")

STORY_LEDGER_REL = os.path.join("设定库", "story_integrity_ledger.json")
THREAD_REL = os.path.join("设定库", "thread_scheduler.json")
PILOT_REL = os.path.join("设定库", "pilot_arc_contract.json")


def ep_num(value: str) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def ep_label(value: str) -> str:
    return value if str(value).startswith("第") else f"第{value}集"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def discover_episodes(root: str) -> List[str]:
    script_root = Path(root) / "脚本"
    eps = [p.name for p in script_root.glob("第*集") if p.is_dir()]
    return sorted(eps, key=lambda e: ep_num(e) or 0)


def parse_voiceover_text(text: str) -> List[Dict[str, Any]]:
    beats: List[Dict[str, Any]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        shot, role, emo, speed, body = m.groups()
        hooks = sorted(h for h in (HOOK_NORMAL, HOOK_PAYOFF, HOOK_ENDING) if h in line)
        beats.append({
            "shot": int(shot),
            "role": role.strip(),
            "emotion": emo.strip(),
            "speed": (speed or "").strip(),
            "text": (body or "").strip(),
            "hooks": hooks,
            "raw": line,
        })
    return beats


def episode_paths(root: str, ep: str) -> Dict[str, Path]:
    base = Path(root) / "脚本" / ep
    return {
        "raw": base / "raw.txt",
        "voiceover": base / "voiceover.txt",
        "storyboard_json": base / "storyboard.json",
        "storyboard_md": base / "故事板.md",
        "script_md": base / "分镜剧本.md",
    }


def episode_text(root: str, ep: str) -> str:
    paths = episode_paths(root, ep)
    return "\n".join(read_text(paths[k]) for k in ("voiceover", "storyboard_json", "storyboard_md", "script_md"))


def entities_from_text(text: str) -> Set[str]:
    out: Set[str] = set()
    for grp in BRACKET_RE.findall(text or ""):
        for g in grp:
            if g.strip():
                out.add(g.strip())
    for t in TITLE_RE.findall(text or ""):
        out.add(t.strip())
    return out


def entities_from_beats(beats: Sequence[Dict[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for b in beats:
        role = str(b.get("role") or "").strip()
        if role and role != "旁白":
            out.add(role)
        out |= entities_from_text(str(b.get("text") or ""))
    return out


def finding(findings: List[Dict[str, Any]], severity: str, code: str, message: str, **extra: Any) -> None:
    row: Dict[str, Any] = {"severity": severity, "code": code, "message": message}
    row.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
    findings.append(row)


def detect_choices(beats: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {"shot": b["shot"], "character": b["role"], "text": b["text"]}
        for b in beats if CHOICE_RE.search(str(b.get("text") or ""))
    ]


def detect_consequences(beats: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {"shot": b["shot"], "character": b["role"], "text": b["text"]}
        for b in beats if CONSEQUENCE_RE.search(str(b.get("text") or ""))
    ]


def detect_motivations(beats: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for b in beats:
        role = str(b.get("role") or "").strip()
        if not role or role == "旁白":
            continue
        text = str(b.get("text") or "")
        signals = []
        if GOAL_RE.search(text):
            signals.append("goal")
        if FEAR_RE.search(text):
            signals.append("fear")
        if LEVERAGE_RE.search(text):
            signals.append("leverage")
        if STANCE_RE.search(text):
            signals.append("stance")
        if signals:
            out.append({"shot": b["shot"], "character": role, "signals": signals, "text": text})
    return out


def classify_dialogue(text: str) -> Set[str]:
    tags: Set[str] = set()
    if CHOICE_RE.search(text):
        tags.add("decide")
    if CONSEQUENCE_RE.search(text):
        tags.add("consequence")
    if REVEAL_RE.search(text):
        tags.add("reveal")
    if PRESSURE_RE.search(text):
        tags.add("pressure")
    if CONCEAL_RE.search(text):
        tags.add("conceal")
    if RELATION_RE.search(text):
        tags.add("relationship")
    if ACTION_RE.search(text):
        tags.add("action")
    if EXPOSITION_RE.search(text):
        tags.add("exposition")
    if not tags:
        tags.add("texture")
    return tags


def dialogue_rows(beats: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for b in beats:
        tags = sorted(classify_dialogue(str(b.get("text") or "")))
        rows.append({"shot": b["shot"], "role": b["role"], "tags": tags, "text": b["text"]})
    return rows


def hook_bridge_declared(root: str, ep: str) -> bool:
    p = episode_paths(root, ep)["storyboard_json"]
    try:
        data = json.loads(read_text(p))
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    keys = ("hook_bridge", "cross_episode_hook_bridge", "narrative_bridge", "thread_scheduler")
    if any(data.get(k) for k in keys):
        return True
    clips = data.get("clips")
    if isinstance(clips, list):
        for clip in clips[:2]:
            if not isinstance(clip, dict):
                continue
            if any(clip.get(k) for k in keys):
                return True
            cont = clip.get("continuity")
            if isinstance(cont, dict) and cont.get("hook_bridge"):
                return True
    return False


def has_ending_hook(beats: Sequence[Dict[str, Any]]) -> bool:
    if not beats:
        return False
    tail = beats[-2:]
    return any(HOOK_ENDING in b.get("hooks", []) or HOOK_CONTENT_RE.search(str(b.get("text") or "")) for b in tail)


def ending_hook_text(beats: Sequence[Dict[str, Any]]) -> str:
    return " ".join(str(b.get("text") or "") for b in beats[-2:])


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def thread_candidates(root: str, eps: Sequence[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ep in eps:
        beats = parse_voiceover_text(read_text(episode_paths(root, ep)["voiceover"]))
        if not beats:
            continue
        tail_text = ending_hook_text(beats)
        if not tail_text or not (has_ending_hook(beats) or QUESTION_RE.search(tail_text)):
            continue
        n = ep_num(ep) or len(out) + 1
        keywords = sorted(entities_from_beats(beats[-3:]))[:6]
        out.append({
            "id": f"THREAD_{len(out) + 1:03d}",
            "thread_id": f"T{len(out) + 1:03d}",
            "status": "candidate",
            "opened_ep": ep,
            "last_touched_ep": ep,
            "next_due_ep": f"第{n + 1}集",
            "payoff_ep": "",
            "open_question": tail_text[:80],
            "touch_keywords": keywords,
        })
    return out


def thread_merge_key(thread: Dict[str, Any]) -> Tuple[str, ...]:
    thread_id = str(thread.get("thread_id") or thread.get("id") or "").strip()
    if thread_id:
        return ("thread_id", thread_id)
    opened = str(thread.get("opened_ep") or "").strip()
    due = str(thread.get("next_due_ep") or "").strip()
    if opened and due:
        return ("episode_slot", opened, due)
    return ("open_question", str(thread.get("open_question") or "").strip())


def merge_thread_rows(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    preserved = {
        k: old.get(k)
        for k in ("status", "payoff_ep")
        if str(old.get(k) or "").strip()
    }
    return {**old, **new, **preserved}


def dedupe_threads(threads: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    positions: Dict[Tuple[str, ...], int] = {}
    for thread in threads:
        if not isinstance(thread, dict):
            continue
        row = dict(thread)
        key = thread_merge_key(row)
        if key in positions:
            idx = positions[key]
            merged[idx] = merge_thread_rows(merged[idx], row)
        else:
            positions[key] = len(merged)
            merged.append(row)
    return merged


def merge_threads(existing: Sequence[Dict[str, Any]], candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = dedupe_threads(existing)
    positions = {thread_merge_key(t): idx for idx, t in enumerate(merged)}
    have = {str(t.get("open_question") or t.get("thread_id") or t.get("id")) for t in merged}
    for cand in candidates:
        cand_key = thread_merge_key(cand)
        key = str(cand.get("open_question") or cand.get("thread_id"))
        if cand_key in positions:
            idx = positions[cand_key]
            merged[idx] = merge_thread_rows(merged[idx], cand)
            have.add(key)
            continue
        if key not in have:
            merged.append(dict(cand))
            positions[cand_key] = len(merged) - 1
            have.add(key)
    return merged


def scaffold_thread_scheduler(root: str, eps: Sequence[str]) -> Dict[str, Any]:
    path = Path(root) / THREAD_REL
    old = load_json(path)
    threads = old.get("threads") if isinstance(old.get("threads"), list) else []
    candidates = thread_candidates(root, eps)
    return {
        "kind": "n2d_thread_scheduler",
        "version": 1,
        "generated_at": date.today().isoformat(),
        "threads": merge_threads(threads, candidates),
    }


def pilot_contract_template(eps: Sequence[str]) -> Dict[str, Any]:
    window = [e for e in eps if (ep_num(e) or 999) <= 5] or [f"第{i}集" for i in range(1, 6)]
    return {
        "kind": "n2d_pilot_arc_contract",
        "version": 1,
        "episode_window": window,
        "series_promise": "",
        "protagonist_desire": "",
        "repeatable_pleasure_loop": "",
        "long_question": "",
        "first_payoff_ep": "",
        "first_complication_ep": "",
        "first_reversal_ep": "",
        "notes": "前3-5集追剧契约；空字段表示还没锁，不影响时长，只影响剧情承诺清晰度。",
    }


def story_episode_record(root: str, ep: str) -> Dict[str, Any]:
    beats = parse_voiceover_text(read_text(episode_paths(root, ep)["voiceover"]))
    return {
        "episode": ep,
        "choices": detect_choices(beats),
        "consequences": detect_consequences(beats),
        "motivations": detect_motivations(beats),
        "dialogue_functions": dialogue_rows(beats),
    }


def scaffold_story_ledger(root: str, eps: Sequence[str]) -> Dict[str, Any]:
    path = Path(root) / STORY_LEDGER_REL
    old = load_json(path)
    old_eps = old.get("episodes") if isinstance(old.get("episodes"), list) else []
    by_ep = {str(row.get("episode")): dict(row) for row in old_eps if isinstance(row, dict)}
    for ep in eps:
        fresh = story_episode_record(root, ep)
        old_row = by_ep.get(ep, {})
        old_row.update({k: v for k, v in fresh.items() if v})
        by_ep[ep] = old_row
    return {
        "kind": "n2d_story_integrity_ledger",
        "version": 1,
        "generated_at": date.today().isoformat(),
        "episodes": [by_ep[ep] for ep in sorted(by_ep, key=lambda e: ep_num(e) or 0)],
    }


def check_threads(root: str, ep: str, text: str, findings: List[Dict[str, Any]]) -> None:
    path = Path(root) / THREAD_REL
    data = load_json(path)
    threads = data.get("threads")
    if not isinstance(threads, list):
        if has_ending_hook(parse_voiceover_text(read_text(episode_paths(root, ep)["voiceover"]))):
            finding(findings, "info", "thread_scheduler_missing",
                    f"本集有集尾钩但缺 {THREAD_REL}；运行 story_integrity_audit.py --write 建 A/B/C 线调度草稿。")
        return
    cur = ep_num(ep)
    for t in threads:
        if not isinstance(t, dict):
            continue
        status = str(t.get("status") or "").lower()
        if status in {"done", "closed", "删除", "已完结"}:
            continue
        due = ep_num(str(t.get("next_due_ep") or ""))
        if cur is not None and due is not None and due <= cur:
            keywords = [str(k) for k in (t.get("touch_keywords") or []) if str(k).strip()]
            touched = bool(keywords and any(k in text for k in keywords))
            if not touched:
                finding(findings, "warn", "thread_due_not_touched",
                        f"线程 {t.get('thread_id') or t.get('id')} 已到 next_due_ep={t.get('next_due_ep')}，"
                        "但本集未命中 touch_keywords；确认是延迟回收还是忘线。",
                        thread=t.get("thread_id") or t.get("id"), keywords=keywords)


def check_pilot_contract(root: str, ep: str, findings: List[Dict[str, Any]]) -> None:
    n = ep_num(ep)
    if n is None or n > 5:
        return
    path = Path(root) / PILOT_REL
    data = load_json(path)
    if not data:
        finding(findings, "info", "pilot_arc_contract_missing",
                f"前5集建议维护 {PILOT_REL}：系列承诺、主角欲望、首个兑现、首个阻碍、首个反转。")
        return
    required = [
        "series_promise", "protagonist_desire", "repeatable_pleasure_loop",
        "long_question", "first_payoff_ep", "first_complication_ep", "first_reversal_ep",
    ]
    missing = [k for k in required if not str(data.get(k) or "").strip()]
    if missing:
        finding(findings, "warn", "pilot_arc_contract_incomplete",
                "前几集追剧契约字段未填全：%s；前3-5集应作为一个 onboarding 小弧设计。" % "、".join(missing),
                missing=missing)


def audit_episode(root: str, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    paths = episode_paths(root, ep)
    findings: List[Dict[str, Any]] = []
    voice = read_text(paths["voiceover"])
    if not paths["voiceover"].exists():
        finding(findings, "block", "missing_voiceover", f"缺 {paths['voiceover']}，无法做剧情完整性体检。")
        return {"episode": ep, "ok": False, "stats": {}, "findings": findings}
    beats = parse_voiceover_text(voice)
    if not beats:
        finding(findings, "block", "empty_voiceover", "voiceover.txt 无可解析台词行。")
        return {"episode": ep, "ok": False, "stats": {}, "findings": findings}

    choices = detect_choices(beats)
    consequences = detect_consequences(beats)
    motivations = detect_motivations(beats)
    drows = dialogue_rows(beats)

    if len(beats) >= 4 and not choices and not consequences:
        finding(findings, "warn", "no_choice_consequence_chain",
                "本集未检测到明确「选择→后果」链；确认这一集是否真的改变了人物目标、关系、资源或局势。")
    elif choices and not consequences:
        finding(findings, "warn", "choice_without_consequence",
                "本集有角色选择，但未检测到后果/代价/状态变化；补一个可见 consequence，避免选择像口号。")

    role_counts: Dict[str, int] = {}
    for b in beats:
        role = str(b.get("role") or "")
        if role and role != "旁白":
            role_counts[role] = role_counts.get(role, 0) + 1
    motivated = {m["character"] for m in motivations}
    missing_motive = [role for role, count in role_counts.items() if count >= 3 and role not in motivated]
    if missing_motive:
        finding(findings, "warn", "motivation_vector_missing",
                "高频出场角色缺当前目标/恐惧/筹码/立场信号：%s；补动机向量，避免人物突然行动。" % "、".join(missing_motive[:6]),
                characters=missing_motive[:6])

    passive_tags = {"exposition", "texture"}
    passive_run: List[int] = []
    for row in drows:
        tags = set(row["tags"])
        if tags <= passive_tags:
            passive_run.append(row["shot"])
        else:
            if len(passive_run) >= 3:
                finding(findings, "warn", "dialogue_not_advancing",
                        f"连续镜头 {passive_run[0]}-{passive_run[-1]} 偏解释/氛围，没有明显施压、揭示、决定、关系或动作推进。",
                        shots=passive_run)
            passive_run = []
    if len(passive_run) >= 3:
        finding(findings, "warn", "dialogue_not_advancing",
                f"连续镜头 {passive_run[0]}-{passive_run[-1]} 偏解释/氛围，没有明显施压、揭示、决定、关系或动作推进。",
                shots=passive_run)

    if has_ending_hook(beats):
        tail = beats[-2:]
        tail_text = ending_hook_text(beats)
        earlier_entities = entities_from_beats(beats[:-2])
        tail_entities = entities_from_beats(tail)
        has_seed = bool(earlier_entities & tail_entities) or bool(REVEAL_RE.search(tail_text)) or bool(CONSEQUENCE_RE.search(tail_text))
        if not has_seed and not hook_bridge_declared(root, ep):
            finding(findings, "warn", "fake_cliffhanger_risk",
                    "集尾像 cliffhanger，但未检测到前文实体/因果/揭示支撑，也未声明 hook_bridge/thread；确认不是随机惊吓式假钩子。",
                    tail=tail_text[:100])

    all_text = episode_text(root, ep)
    check_threads(root, ep, all_text, findings)
    check_pilot_contract(root, ep, findings)

    stats = {
        "shots": len(beats),
        "choices": len(choices),
        "consequences": len(consequences),
        "motivations": len(motivations),
        "dialogue_rows": len(drows),
        "ending_hook": has_ending_hook(beats),
    }
    ok = not any(f["severity"] in {"block", "must"} for f in findings)
    return {"episode": ep, "ok": ok, "stats": stats, "findings": findings}


def write_scaffolds(root: str, eps: Sequence[str]) -> Dict[str, str]:
    outputs: Dict[str, str] = {}
    story_path = Path(root) / STORY_LEDGER_REL
    thread_path = Path(root) / THREAD_REL
    pilot_path = Path(root) / PILOT_REL
    write_json(story_path, scaffold_story_ledger(root, eps))
    write_json(thread_path, scaffold_thread_scheduler(root, eps))
    outputs["story_integrity_ledger"] = str(story_path)
    outputs["thread_scheduler"] = str(thread_path)
    if not pilot_path.exists():
        write_json(pilot_path, pilot_contract_template(eps))
    outputs["pilot_arc_contract"] = str(pilot_path)
    return outputs


def print_human(result: Dict[str, Any]) -> None:
    ep = result.get("episode") or "series"
    stats = result.get("stats") or {}
    print(f"# 剧情完整性体检 — {ep}")
    if stats:
        print(
            f"镜数 {stats.get('shots', 0)}　选择 {stats.get('choices', 0)}　后果 {stats.get('consequences', 0)}　"
            f"动机信号 {stats.get('motivations', 0)}　集尾钩 {'有' if stats.get('ending_hook') else '无'}"
        )
    findings = result.get("findings") or []
    if not findings:
        print("- PASS：未发现选择-后果、动机、线程、假钩子或对白推进风险。")
        return
    marker = {"block": "BLOCK", "must": "BLOCK", "warn": "WARN", "info": "INFO"}
    for f in findings:
        print(f"- {marker.get(f.get('severity'), 'INFO')} [{f.get('code')}] {f.get('message')}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 剧情完整性文本期体检")
    ap.add_argument("root")
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--write", action="store_true", help="写 story_integrity_ledger/thread_scheduler/pilot_arc_contract 草稿")
    ap.add_argument("--strict", action="store_true", help="warn 也返回非 0；默认只有 block 才失败")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    eps = [ep_label(ns.episode)] if ns.episode else discover_episodes(root)
    outputs: Dict[str, str] = {}
    if ns.write:
        outputs = write_scaffolds(root, eps)

    if ns.episode:
        result = audit_episode(root, ep_label(ns.episode))
        if outputs:
            result["outputs"] = outputs
        if ns.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_human(result)
        has_block = any(f["severity"] in {"block", "must"} for f in result.get("findings") or [])
        has_warn = any(f["severity"] == "warn" for f in result.get("findings") or [])
        return 1 if (has_block or (ns.strict and has_warn)) else 0

    results = [audit_episode(root, ep) for ep in eps]
    findings = [f for r in results for f in (r.get("findings") or [])]
    payload = {"episodes": len(results), "results": results, "outputs": outputs, "findings": findings}
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"# 剧情完整性体检 — {len(results)} 集")
        for r in results:
            print_human(r)
    has_block = any(f["severity"] in {"block", "must"} for f in findings)
    has_warn = any(f["severity"] == "warn" for f in findings)
    return 1 if (has_block or (ns.strict and has_warn)) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
