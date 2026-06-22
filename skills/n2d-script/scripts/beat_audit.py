#!/usr/bin/env python3
"""beat_audit.py — 集内留存节拍机检（Gap4/5）。

为什么存在：`导演节奏.md` 要求"先列节拍点表(开场钩/钩子/爽点/集尾钩)再写词"，voiceover 也有
⚡/💥/🪝 标记，但**没有任何机检**——没人量"是否每 15-20s 一个钩子、是否 ≥1 反转、集尾是否硬断、
爽点是否只有情绪没有信息增量"。2026 爆款关键是"信息回报+情绪回报叠加"，且要反同质化。

本脚本读 voiceover.txt（钩子标记 + 情绪）+ 可选 镜头时长.json（真实秒）→ 出：
  ① 集内节拍体检：开场冷启 / 钩子间隔 / ≥1 反转 / 集尾 cliffhanger / 镜头时长曲线。
  ② 情绪回报 vs 信息回报（Gap4）：爽点是否只有情绪宣泄、缺信息增量。
  ③ --series：跨集套路同质化（桥段指纹 Jaccard），治"AI 模板复印、观众疲劳"。

report-only（默认 exit 0）；--strict 时 must 级问题 exit 1。**不替代 validate_timings 闸门**，是其旁路的留存建议。

用法:
    python3 beat_audit.py <作品根> 第N集 [--strict] [--json]
    python3 beat_audit.py <作品根> --series [--json]
"""
import json
import os
import re
import sys
from pathlib import Path

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
HOOK_NORMAL = "⚡"
HOOK_PAYOFF = "💥"
HOOK_ENDING = "🪝"

# 信息回报：揭示信息增量（真相/身世/系统/线索/数值/命名）。
INFO_RE = re.compile(r"(原来|竟是|竟然|其实|真相|身世|来历|名字|是.{0,6}的人|系统|面板|提示|【|"
                     r"等级|经验|线索|证据|因为|原来是|揭|暴露|发现|秘密|内幕)")
# 情绪回报：情绪宣泄/解气（反击/打脸/解气/胜负/生死/护宠）。
EMO_RE = re.compile(r"(反击|还手|打脸|解气|爽|痛快|怒|恨|哭|跪|斩|杀|赢|胜|夺回|护|宠|碾压|"
                    r"震住|压住|逆袭|翻盘|报仇|雪恨)")
# 反转信号（≥1 反转要求）。
REVERSAL_RE = re.compile(r"(原来|竟|反转|没想到|不料|岂料|居然|反而|却|逆转|翻盘)")
CALM_EMO = ("低沉", "平静", "茫然", "悲伤", "淡漠", "疲惫")

HOOK_GAP_SEC = 20.0   # 中段钩子间隔上限（导演节奏 §二：每 15-20s 一个钩子）
HOOK_GAP_SHOTS = 4    # 无真实时长时：相邻钩子最多隔几镜


def parse_voiceover(path):
    beats = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        shot, role, emo, speed, text = m.groups()
        hooks = set(h for h in (HOOK_NORMAL, HOOK_PAYOFF, HOOK_ENDING) if h in line)
        beats.append({
            "shot": int(shot), "role": role.strip(), "emotion": emo.strip(),
            "speed": (speed or "").strip(), "text": text.strip(), "hooks": hooks,
        })
    return beats


def load_shot_seconds(root, ep):
    p = Path(root) / "脚本" / ep / "镜头时长.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for k, v in data.items():
        m = re.search(r"(\d+)", str(k))
        if m:
            out[int(m.group(1))] = float(v)
    return out or None


def cumulative_starts(shot_secs):
    """镜号→该镜起始累计秒。"""
    starts, t = {}, 0.0
    for sn in sorted(shot_secs):
        starts[sn] = t
        t += shot_secs[sn]
    return starts, t


def audit_episode(root, ep):
    vpath = Path(root) / "脚本" / ep / "voiceover.txt"
    findings = []  # (severity, code, msg)  severity: must|warn|info
    if not vpath.exists():
        return [("must", "no_voiceover", f"缺 {ep}/voiceover.txt，先做阶段1 剧本改编")], {}
    beats = parse_voiceover(vpath)
    if not beats:
        return [("warn", "empty", "voiceover.txt 无可解析台词行（格式 [镜头N·角色·情绪·(语速)] 台词）")], {}

    shot_secs = load_shot_seconds(root, ep)
    hooked = [b for b in beats if b["hooks"]]
    payoffs = [b for b in beats if HOOK_PAYOFF in b["hooks"]]

    # ① 开场冷启：前 2 镜应有钩或非慢旁白起
    head = beats[:2]
    head_hooked = any(b["hooks"] for b in head)
    if not head_hooked and head and head[0]["role"] == "旁白" and head[0]["emotion"] in CALM_EMO:
        findings.append(("warn", "cold_open",
                         "开场疑似慢旁白起（旁白+平缓情绪、前2镜无钩）：改 0-3s 冷开场/倒叙钩，最炸的画面/台词放最前"))
    elif not head_hooked:
        findings.append(("info", "cold_open", "前2镜无钩子标记，确认是否 0-3s 冷开场抓人"))

    # ② 钩子间隔（导演节奏 §二）
    if shot_secs:
        starts, total = cumulative_starts(shot_secs)
        hook_times = sorted(starts.get(b["shot"], 0.0) for b in hooked)
        prev = 0.0
        for t in hook_times:
            if t - prev > HOOK_GAP_SEC:
                findings.append(("warn", "hook_gap",
                                 f"{prev:.0f}s–{t:.0f}s 间隔 {t-prev:.0f}s 无钩子（>{HOOK_GAP_SEC:.0f}s）：中段易划走，补悬念/信息/反差/危机"))
            prev = t
        if total - prev > HOOK_GAP_SEC and hook_times:
            findings.append(("info", "hook_gap_tail", f"末钩到结尾 {total-prev:.0f}s 无新钩，确认集尾张力"))
    else:
        idxs = sorted(b["shot"] for b in hooked)
        for a, b in zip(idxs, idxs[1:]):
            if b - a > HOOK_GAP_SHOTS:
                findings.append(("info", "hook_gap_shots",
                                 f"镜{a}→镜{b} 隔 {b-a} 镜无钩（无镜头时长.json，按镜数估）：定稿后用真实秒复核"))

    # ③ ≥1 反转
    has_rev = bool(payoffs) or any(REVERSAL_RE.search(b["text"]) for b in beats)
    if not has_rev:
        findings.append(("warn", "no_reversal", "本集无 💥爽点 也无反转词：导演节奏要求每集 ≥1 次反转，补一个"))

    # ④ 集尾 cliffhanger
    if not any(HOOK_ENDING in b["hooks"] for b in beats):
        findings.append(("warn", "no_ending_hook", "缺集尾 🪝 标记：集尾须 cliffhanger 硬断（危机悬置/真相半露/反转预告），别把戏讲完"))
    elif HOOK_ENDING in beats[-1]["hooks"] or (hooked and HOOK_ENDING in hooked[-1]["hooks"]):
        pass

    # ⑤ 情绪回报 vs 信息回报（Gap4）
    info_hooks, emo_hooks = [], []
    for b in hooked:
        if INFO_RE.search(b["text"]):
            info_hooks.append(b["shot"])
        if EMO_RE.search(b["text"]):
            emo_hooks.append(b["shot"])
    if hooked and not info_hooks:
        findings.append(("warn", "no_info_payoff",
                         "本集钩子/爽点全为情绪宣泄、零信息增量：2026 爆款要『信息回报+情绪回报』叠加，"
                         "至少一个钩子给观众新信息（真相/身世/线索/系统数值）"))
    elif hooked and not emo_hooks:
        findings.append(("info", "no_emo_payoff", "钩子偏信息、缺情绪释放，确认爽感是否足够"))

    # ⑥ 镜头时长曲线（导演节奏 §四/§五）
    if shot_secs and len(shot_secs) >= 4:
        vals = list(shot_secs.values())
        mean = sum(vals) / len(vals)
        if mean > 0:
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            cov = (var ** 0.5) / mean
            if cov < 0.18:
                findings.append(("info", "flat_rhythm",
                                 f"镜头近等长（变异系数 {cov:.2f}<0.18）像 PPT：走曲线——铺垫长镜+临近爽点碎切+爽点后留白"))

    stats = {
        "shots": len(beats), "hooks": len(hooked), "payoffs": len(payoffs),
        "info_payoff_shots": info_hooks, "emo_payoff_shots": emo_hooks,
        "has_reversal": has_rev, "has_ending_hook": any(HOOK_ENDING in b["hooks"] for b in beats),
        "has_timings": bool(shot_secs),
    }
    return findings, stats


def episode_signature(root, ep):
    """桥段指纹：本集 payoff/conflict 关键词集合 + 钩子类型序列（用于同质化对比）。"""
    vpath = Path(root) / "脚本" / ep / "voiceover.txt"
    if not vpath.exists():
        return None
    beats = parse_voiceover(vpath)
    kws = set()
    for b in beats:
        for rx in (EMO_RE, INFO_RE, REVERSAL_RE):
            kws.update(rx.findall(b["text"]))
    emos = tuple(b["emotion"] for b in beats)
    return {"keywords": kws, "emotions": emos}


def jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b) if (a | b) else 0.0


def audit_series(root):
    sdir = Path(root) / "脚本"
    eps = sorted([d.name for d in sdir.glob("第*集") if (d / "voiceover.txt").exists()],
                 key=lambda n: int(re.search(r"\d+", n).group()))
    sigs = {ep: episode_signature(root, ep) for ep in eps}
    dups = []
    for i, ea in enumerate(eps):
        for eb in eps[i + 1:]:
            sa, sb = sigs[ea], sigs[eb]
            if not sa or not sb:
                continue
            j = jaccard(sa["keywords"], sb["keywords"])
            if j >= 0.8 and len(sa["keywords"]) >= 4:
                dups.append((ea, eb, round(j, 2)))
    return eps, dups


def print_findings(title, findings):
    print(f"## {title}")
    order = {"must": 0, "warn": 1, "info": 2}
    icon = {"must": "⛔", "warn": "⚠️", "info": "ℹ️"}
    if not findings:
        print("- ✅ 集内节拍体检通过")
        return
    for sev, code, msg in sorted(findings, key=lambda f: order[f[0]]):
        print(f"- {icon[sev]} [{code}] {msg}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print("用法: beat_audit.py <作品根> 第N集 [--strict] [--json]  |  <作品根> --series")
        sys.exit(2)
    root = args[0]

    if "--series" in flags:
        eps, dups = audit_series(root)
        if "--json" in flags:
            print(json.dumps({"episodes": eps, "duplicates": dups}, ensure_ascii=False, indent=2))
            return
        print(f"## 跨集套路同质化（Gap4·{len(eps)} 集）")
        if not dups:
            print("- ✅ 未发现高度重复的桥段指纹")
        else:
            for ea, eb, j in dups:
                print(f"- ⚠️ {ea} ↔ {eb} 桥段指纹重合 {j}（套路雷同→观众疲劳，换爽点类型/信息角度/情绪曲线）")
        return

    if len(args) < 2:
        print("用法: beat_audit.py <作品根> 第N集 [--strict] [--json]")
        sys.exit(2)
    ep = args[1] if args[1].startswith("第") else f"第{args[1]}集"
    findings, stats = audit_episode(root, ep)
    if "--json" in flags:
        print(json.dumps({"episode": ep, "stats": stats,
                          "findings": [{"severity": s, "code": c, "msg": m} for s, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"# 集内留存节拍体检 — {ep}")
        print(f"镜数 {stats.get('shots', 0)}　钩子 {stats.get('hooks', 0)}　爽点 {stats.get('payoffs', 0)}　"
              f"反转 {'有' if stats.get('has_reversal') else '无'}　集尾钩 {'有' if stats.get('has_ending_hook') else '无'}　"
              f"真实时长 {'有' if stats.get('has_timings') else '无(按镜数估)'}")
        print()
        print_findings("节拍 findings（report-only·导演节奏建议）", findings)
        print("> 集间留存骨架见 references/追更骨架.md；时长一致性闸门仍是 validate_timings.py（本检不替代它）。")

    must_n = sum(1 for s, _, _ in findings if s == "must")
    warn_n = sum(1 for s, _, _ in findings if s == "warn")
    if "--strict" in flags and (must_n or warn_n):
        sys.exit(1)
    sys.exit(0 if not must_n else 1)


if __name__ == "__main__":
    main()
