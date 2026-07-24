#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
knowledge_sentry.py — 角色知情账：谁在第几章知道了什么秘密（确定性骨架 + LLM 补语义）

补剧情衔接侧最后一块无人看守的台账：掉马/身份文/悬疑/宫斗的头号穿帮不是"死人复活"，
而是**知情错乱**——角色 A 对着还不该知道秘密的角色 B 说破、已当众揭示的马甲下一卷又"瞒着所有人"、
读者早知道的底牌被当成终章大反转再揭一次。`reveal-scenes.md` 要求把"知情人范围"写进 state_delta、
`dialogue.md` 要求写前理清"信息地图"，但此前**没有结构化台账、没有机检、写章包也看不见知情面**，
全靠每次现场重推。业界 story bible 的标准做法正是一张 Secrets 表（secret / who knows / who suspects /
who is wrong / reader knowledge / reveal timing），本脚本把它落成账 + 哨兵。

机检 vs LLM 的诚实边界（对标 foreshadow_ledger / logic_sentry）：
  - **确定性（脚本算）**：台账结构自洽（得知章 vs 公开章的序）、计划揭示超期、死人"得知"秘密
    （与动态百科交叉）、以及**泄密候选**（tell_keywords 在任何人知道之前的章节出现——正文关键词扫描，
    脆弱启发式 → 恒建议级，B10）。另有**信息释放策略三查**（希区柯克炸弹论，恒建议级）：
    irony_window_untouched（读者先知的反讽窗口内正文零触碰=悬念资产闲置）、reveal_burst
    （同章公开 ≥N 条秘密=揭示拥堵）、surprise_heavy（几乎全是读者角色同时知的 surprise 型，
    无读者先知的 suspense 型）。
  - **LLM/人工（脚本不臆测）**："这段对话有没有说破秘密"的语义识别、误信内容是否仍成立。
    得知(learn)/公开(reveal)由 agent/人在交互节点判断后用子命令登记；脚本把账记准、把矛盾揪出来。

台账：`设定/knowledge_ledger.json`（schema 见 references/entity-schema.md §8）。

子命令：
  add     登记一条秘密（含初始知情人）
  learn   记某角色于某章得知秘密
  suspect 记某角色开始怀疑
  reveal  记秘密公开（public_since）
  scan    巡检：结构对账 + 揭示超期 + 泄密候选 → 审稿/knowledge_report.json

  python3 knowledge_sentry.py <作品根> add --fact "沈念是前朝公主" --importance critical \
      --holder 沈念:1 [--holder 王敦:12] [--reader-since 1] [--planned-reveal 40] \
      [--keywords 前朝公主,皇室血脉] [--id SECRET_001] [--linked-seed SEED_003]
  python3 knowledge_sentry.py <作品根> learn --id SECRET_001 --name 李嬷嬷 --at 18 [--how 偷听]
  python3 knowledge_sentry.py <作品根> suspect --id SECRET_001 --name 皇帝 --at 22
  python3 knowledge_sentry.py <作品根> reveal --id SECRET_001 --at 40
  python3 knowledge_sentry.py <作品根> scan [--through 60] [--grace 5]

测试：cd skills/novel-wiki/scripts && python3 -m pytest test_knowledge_sentry.py
"""
import os
import re
import json
import argparse

LEDGER_REL = os.path.join("设定", "knowledge_ledger.json")
KIND = "novel_knowledge_ledger"
IMPORTANCE = {"low", "medium", "high", "critical"}
DEFAULT_GRACE = 5  # 计划揭示章的宽容窗口（与伏笔台账 grace 同口径）

# ── 信息释放策略阈值（希区柯克炸弹论·env 可标定）────────────────────────────
# irony 窗口：读者已知(reader_knows_since) 与 剧内公开(public_since/planned_reveal) 之间
# 至少隔此章数才值得检查"炸弹旁有没有人说话"。
IRONY_WINDOW_MIN = int(os.environ.get("NOVEL_IRONY_WINDOW_MIN", "4"))
# 同一章公开揭示的秘密 ≥ 此数 → 女仆管家式倾泻（结尾揭示拥堵）。
REVEAL_BURST_MIN = int(os.environ.get("NOVEL_REVEAL_BURST_MIN", "3"))
# surprise 型占比检查的最小样本量与告警占比。
SURPRISE_SAMPLE_MIN = int(os.environ.get("NOVEL_SURPRISE_SAMPLE_MIN", "5"))
SURPRISE_HEAVY_RATIO = float(os.environ.get("NOVEL_SURPRISE_HEAVY_RATIO", "0.8"))

# 无台账时的"该建账没建账"提示信号：正文里反复出现揭示/隐瞒题材词（多章命中才提示，宁缺毋滥）。
REVEAL_TOPIC_KW = ("掉马", "马甲", "身份暴露", "身份曝光", "隐瞒身份", "假死", "瞒着", "隐情", "冒名", "替身")
LEDGER_HINT_MIN_CHAPTERS = 3


# ── 账本读写 ─────────────────────────────────────────────────────────────────
def ledger_path(project):
    return os.path.join(project, LEDGER_REL)


def load_ledger(project):
    path = ledger_path(project)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("kind", KIND)
        data.setdefault("secrets", [])
        return data
    return {"kind": KIND, "secrets": []}


def save_ledger(project, data):
    path = ledger_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _next_id(secrets):
    used = set()
    for s in secrets:
        m = re.match(r"SECRET_(\d+)$", str(s.get("id", "")))
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return f"SECRET_{n:03d}"


def find_secret(secrets, secret_id):
    for s in secrets:
        if s.get("id") == secret_id:
            return s
    return None


# ── 登记动作 ─────────────────────────────────────────────────────────────────
def add_secret(data, fact, holders=None, importance="medium", secret_id=None,
               reader_knows_since=None, planned_reveal_chapter=None,
               tell_keywords=None, linked_seed=None):
    secrets = data["secrets"]
    if not secret_id:
        secret_id = _next_id(secrets)
    if find_secret(secrets, secret_id):
        raise ValueError(f"秘密 id 已存在: {secret_id}")
    if importance not in IMPORTANCE:
        raise ValueError(f"importance 须为 {sorted(IMPORTANCE)}，得到 {importance}")
    secret = {
        "id": secret_id,
        "fact": fact,
        "importance": importance,
        "holders": list(holders or []),
        "suspects": [],
        "wrong_beliefs": [],
        "reader_knows_since": int(reader_knows_since) if reader_knows_since is not None else None,
        "planned_reveal_chapter": int(planned_reveal_chapter) if planned_reveal_chapter is not None else None,
        "public_since": None,
        "tell_keywords": list(tell_keywords or []),
        "linked_seed": linked_seed,
    }
    secrets.append(secret)
    return secret


def learn(data, secret_id, name, chapter, how=None):
    secret = find_secret(data["secrets"], secret_id)
    if not secret:
        raise KeyError(f"找不到秘密 id: {secret_id}")
    holders = secret.setdefault("holders", [])
    for h in holders:
        if h.get("name") == name:
            return h  # 已知情，幂等
    entry = {"name": name, "learned_chapter": int(chapter)}
    if how:
        entry["how"] = how
    holders.append(entry)
    # 得知即不再是"怀疑者"
    secret["suspects"] = [x for x in secret.get("suspects", []) if x.get("name") != name]
    return entry


def suspect(data, secret_id, name, chapter):
    secret = find_secret(data["secrets"], secret_id)
    if not secret:
        raise KeyError(f"找不到秘密 id: {secret_id}")
    if any(h.get("name") == name for h in secret.get("holders", [])):
        raise ValueError(f"{name} 已是知情人，无需登记怀疑")
    sus = secret.setdefault("suspects", [])
    for x in sus:
        if x.get("name") == name:
            return x
    entry = {"name": name, "since_chapter": int(chapter)}
    sus.append(entry)
    return entry


def reveal(data, secret_id, chapter):
    secret = find_secret(data["secrets"], secret_id)
    if not secret:
        raise KeyError(f"找不到秘密 id: {secret_id}")
    secret["public_since"] = int(chapter)
    return secret


# ── 章节工具 ─────────────────────────────────────────────────────────────────
def _chapter_files(project):
    """[(章号, 路径)]，按章号升序；无章节目录返回 []。"""
    cdir = os.path.join(project, "章节")
    if not os.path.isdir(cdir):
        return []
    out = []
    for name in sorted(os.listdir(cdir)):
        if not name.endswith(".md"):
            continue
        m = re.search(r"第0*(\d+)章", name)
        if m:
            out.append((int(m.group(1)), os.path.join(cdir, name)))
    out.sort(key=lambda t: t[0])
    return out


def _max_written_chapter(project):
    files = _chapter_files(project)
    return files[-1][0] if files else 0


def _wiki_death_chapters(project):
    """{角色名: death_chapter}——读动态百科的死亡记录（含 auto 候选，故只用于建议级交叉）。"""
    path = os.path.join(project, "设定", "动态百科.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            wiki = json.load(f)
    except Exception:
        return {}
    out = {}
    for name, ent in wiki.items():
        if not isinstance(ent, dict):
            continue
        dc = ent.get("death_chapter")
        if dc is not None and ent.get("status") in ("deceased", "dead"):
            try:
                out[name] = int(dc)
            except (TypeError, ValueError):
                continue
    return out


# ── 确定性巡检 ───────────────────────────────────────────────────────────────
def first_legit_chapter(secret):
    """这条秘密最早"合法出现在纸面上"的章号：读者知道 / 首个知情人得知 / 公开，三者最早。
    全空返回 None（无锚点，泄密候选扫描跳过该条）。"""
    cands = []
    if secret.get("reader_knows_since") is not None:
        cands.append(int(secret["reader_knows_since"]))
    for h in secret.get("holders", []):
        lc = h.get("learned_chapter")
        if lc is not None:
            cands.append(int(lc))
    if secret.get("public_since") is not None:
        cands.append(int(secret["public_since"]))
    return min(cands) if cands else None


def ledger_conflicts(secrets, death_chapters=None):
    """台账结构自洽检查（只比结构化整数，确定性）。"""
    death_chapters = death_chapters or {}
    alerts = []
    for s in secrets:
        pub = s.get("public_since")
        for h in s.get("holders", []):
            lc = h.get("learned_chapter")
            if pub is not None and lc is not None and int(lc) > int(pub):
                alerts.append({
                    "kind": "learned_after_public", "id": s["id"], "severity": "建议级",
                    "auto": True, "confidence": "ledger",
                    "note": (f"{h.get('name')} 记为第{lc}章才得知「{s.get('fact','')}」，"
                             f"但该秘密第{pub}章已公开——账目矛盾，核对是登记错还是剧情里确实晚知"),
                })
            dc = death_chapters.get(h.get("name"))
            if dc is not None and lc is not None and int(lc) > dc:
                alerts.append({
                    "kind": "holder_dead_before_learned", "id": s["id"], "severity": "建议级",
                    "auto": True, "confidence": "ledger",
                    "note": (f"{h.get('name')} 按动态百科第{dc}章已亡故，却记为第{lc}章得知"
                             f"「{s.get('fact','')}」——死人得知秘密，核对章号或复活/托梦语境"),
                })
        for x in s.get("suspects", []):
            sc = x.get("since_chapter")
            if pub is not None and sc is not None and int(sc) > int(pub):
                alerts.append({
                    "kind": "suspect_after_public", "id": s["id"], "severity": "建议级",
                    "auto": True, "confidence": "ledger",
                    "note": (f"{x.get('name')} 第{sc}章才开始怀疑「{s.get('fact','')}」，"
                             f"但秘密第{pub}章已公开——公开之后无所谓怀疑，核对登记"),
                })
    return alerts


def reveal_overdue(secrets, through_chapter, grace=DEFAULT_GRACE):
    """计划揭示章 + grace 已过仍未公开 = 掉马拖太久候选。
    结构化整数比较（与伏笔超期同口径）：high/critical=阻断级，其余=建议级。"""
    alerts = []
    for s in secrets:
        if s.get("public_since") is not None:
            continue
        planned = s.get("planned_reveal_chapter")
        if planned is None:
            continue
        if through_chapter > int(planned) + int(grace):
            sev = "阻断级" if s.get("importance") in ("high", "critical") else "建议级"
            alerts.append({
                "kind": "reveal_overdue", "id": s["id"], "severity": sev,
                "auto": True, "confidence": "ledger",
                "overdue_by": through_chapter - int(planned),
                "note": (f"秘密「{s.get('fact','')}」计划第{planned}章揭示，已拖过 grace 窗口——"
                         "掉马/真相拖太久是弃书高发点；按 reveal-scenes.md 排一场揭示，"
                         "或改 planned_reveal_chapter 并同步章纲"),
            })
    return alerts


def leak_candidates(secrets, chapter_texts):
    """泄密候选：tell_keywords 在**任何人（读者/角色）知道之前**的章节出现。
    正文关键词扫描 = 脆弱启发式（B10）→ 恒建议级，只出请人复核的候选。"""
    alerts = []
    for s in secrets:
        kws = [k for k in (s.get("tell_keywords") or []) if k]
        if not kws:
            continue
        legit = first_legit_chapter(s)
        if legit is None:
            continue
        for idx, text in chapter_texts.items():
            if idx >= legit:
                continue
            for kw in kws:
                pos = text.find(kw)
                if pos < 0:
                    continue
                excerpt = text[max(0, pos - 20):pos + len(kw) + 20].replace("\n", " ")
                alerts.append({
                    "kind": "secret_leak_candidate", "id": s["id"], "severity": "建议级",
                    "auto": True, "confidence": "heuristic", "chapter": idx,
                    "keyword": kw, "evidence": excerpt,
                    "note": (f"第{idx}章出现「{kw}」，早于该秘密任何知情锚点（第{legit}章）——"
                             "若是叙述/对白说破即泄密穿帮；若是无关同词或有意的读者视角铺垫，"
                             "复核后忽略或把 reader_knows_since 提前"),
                })
                break  # 每章每条秘密报一次即可
    return alerts


def irony_window_untouched(secrets, chapter_texts, window_min=None):
    """戏剧反讽窗口空转（希区柯克炸弹论）：读者已知、剧内未公开的窗口 ≥window_min 章，
    但窗口内正文对该秘密零触碰（tell_keywords 与知情人名都没出现）——"桌下放了炸弹，
    却没让任何人坐在桌边聊天"，最贵的张力资产被闲置。

    正文关键词扫描 = 脆弱启发式 → 恒建议级；无 keywords 且无 holders 的秘密无探针，跳过。"""
    window_min = IRONY_WINDOW_MIN if window_min is None else window_min
    alerts = []
    for s in secrets:
        rk = s.get("reader_knows_since")
        if rk is None:
            continue
        end = s.get("public_since") if s.get("public_since") is not None else s.get("planned_reveal_chapter")
        if end is None:
            continue
        rk, end = int(rk), int(end)
        if end - rk < window_min:
            continue
        probes = ([k for k in (s.get("tell_keywords") or []) if k]
                  + [h.get("name") for h in s.get("holders", []) if h.get("name")])
        if not probes:
            continue
        window = sorted(c for c in chapter_texts if rk < c < end)
        if len(window) < window_min - 1:
            continue  # 窗口章还没写够，判空转为时过早
        hits = sum(1 for c in window for p in probes if p in chapter_texts[c])
        if hits == 0:
            alerts.append({
                "kind": "irony_window_untouched", "id": s["id"], "severity": "建议级",
                "auto": True, "confidence": "heuristic",
                "window": [rk, end], "probes": probes[:6],
                "note": (f"秘密「{s.get('fact','')}」读者第{rk}章已知、剧内第{end}章才揭——"
                         f"这 {end - rk} 章的戏剧反讽窗口内正文对它零触碰（关键词/知情人名均未现）。"
                         "炸弹已放桌下却没人坐在桌边：安排不知情者在秘密附近走动/对话，"
                         "让读者替角色捏汗，否则这段悬念资产白白闲置"),
            })
    return alerts


def reveal_burst(secrets, burst_min=None):
    """揭示拥堵：同一章公开 ≥burst_min 条秘密 = 女仆管家式倾泻（真相挤在一章倒完，
    每条 reveal 的冲击力互相踩踏）。台账整数比较，确定性。"""
    burst_min = REVEAL_BURST_MIN if burst_min is None else burst_min
    by_ch = {}
    for s in secrets:
        if s.get("public_since") is not None:
            by_ch.setdefault(int(s["public_since"]), []).append(s.get("id"))
    alerts = []
    for ch, ids in sorted(by_ch.items()):
        if len(ids) >= burst_min:
            alerts.append({
                "kind": "reveal_burst", "severity": "建议级", "auto": True,
                "confidence": "ledger", "chapter": ch, "secret_ids": ids,
                "note": (f"第{ch}章同章公开 {len(ids)} 条秘密（{('、'.join(str(i) for i in ids))}）——"
                         "女仆管家式倾泻：真相拥堵互相稀释冲击力，考虑把部分揭示前移错峰"),
            })
    return alerts


def surprise_heavy(secrets, sample_min=None, ratio=None):
    """信息策略失衡：秘密样本 ≥sample_min 条时，surprise 型（读者与角色同时知道：
    reader_knows_since 空、或不早于 public_since）占比 ≥ratio → 全书几乎没有
    "读者先知"的 suspense 型。希区柯克口径：surprise 只值 15 秒惊讶，suspense 值 15 分钟
    悬念——建议把部分秘密改造成读者先知的戏剧反讽（提前 reader_knows_since）。"""
    sample_min = SURPRISE_SAMPLE_MIN if sample_min is None else sample_min
    ratio = SURPRISE_HEAVY_RATIO if ratio is None else ratio
    if len(secrets) < sample_min:
        return []
    surprise = [s for s in secrets
                if s.get("reader_knows_since") is None
                or (s.get("public_since") is not None
                    and int(s["reader_knows_since"]) >= int(s["public_since"]))]
    share = len(surprise) / len(secrets)
    if share < ratio:
        return []
    return [{
        "kind": "surprise_heavy", "severity": "建议级", "auto": True,
        "confidence": "ledger", "surprise_count": len(surprise), "total": len(secrets),
        "note": (f"{len(secrets)} 条秘密中 {len(surprise)} 条（{share:.0%}）是 surprise 型"
                 "（读者与角色同时才知道）——几乎没有读者先知的 suspense 型。"
                 "surprise 只值 15 秒惊讶、suspense 值 15 分钟悬念（希区柯克）：挑几条"
                 "把 reader_knows_since 提到揭示前，让读者先看见桌下的炸弹"),
    }]


def scan(data, through_chapter, chapter_texts=None, death_chapters=None, grace=DEFAULT_GRACE):
    """纯函数巡检：结构对账 + 揭示超期 + 泄密候选 + 信息释放策略（炸弹论三查）。"""
    secrets = data.get("secrets", [])
    alerts = (ledger_conflicts(secrets, death_chapters)
              + reveal_overdue(secrets, through_chapter, grace)
              + leak_candidates(secrets, chapter_texts or {})
              + irony_window_untouched(secrets, chapter_texts or {})
              + reveal_burst(secrets)
              + surprise_heavy(secrets))
    blocking = sum(1 for a in alerts if a.get("severity") == "阻断级")
    open_secrets = [s for s in secrets if s.get("public_since") is None]
    return {
        "kind": "knowledge_report",
        "through_chapter": through_chapter,
        "grace": grace,
        "total_secrets": len(secrets),
        "open_secrets": len(open_secrets),
        "blocking": blocking,
        "alerts": alerts,
    }


def _ledger_missing_hint(project):
    """无台账但正文反复出现揭示/隐瞒题材词 → 建议级"该建账没建账"（没数据≠没问题）。"""
    hit_chapters = []
    for idx, path in _chapter_files(project):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        if any(kw in text for kw in REVEAL_TOPIC_KW):
            hit_chapters.append(idx)
    if len(hit_chapters) < LEDGER_HINT_MIN_CHAPTERS:
        return None
    return {
        "kind": "knowledge_ledger_missing", "severity": "建议级", "auto": True,
        "confidence": "heuristic", "chapters": hit_chapters[:10],
        "note": (f"已有 {len(hit_chapters)} 章出现掉马/隐瞒/身份揭示类内容，但未建知情账——"
                 "谁知道什么全靠现场重推，知情错乱（提前说破/二次揭示/公开后还瞒）机检全部空转。"
                 "用 knowledge_sentry.py add/learn/reveal 把主要秘密登记成账"),
    }


def analyze(project, through_chapter=None, grace=DEFAULT_GRACE):
    """consistency_audit 子检测器契约：analyze(project) → {ran, alerts, blocking, ...}。"""
    data = load_ledger(project)
    secrets = data.get("secrets") or []
    if not secrets:
        hint = _ledger_missing_hint(project)
        if hint:
            return {"ran": True, "alerts": [hint], "total": 1, "blocking": 0, "skipped": ""}
        return {"ran": False,
                "skipped": "无知情账或账为空（掉马/悬疑/身份线项目先用 knowledge_sentry.py add 登记秘密）"}
    if through_chapter is None:
        through_chapter = _max_written_chapter(project)
    chapter_texts = {}
    for idx, path in _chapter_files(project):
        try:
            with open(path, encoding="utf-8") as f:
                chapter_texts[idx] = f.read()
        except OSError:
            continue
    report = scan(data, through_chapter, chapter_texts=chapter_texts,
                  death_chapters=_wiki_death_chapters(project), grace=grace)
    report["ran"] = True
    return report


# ── 写章包注入（draft_packets 消费；只读） ───────────────────────────────────
def packet_section(project, chapter, names_on_stage=None):
    """给第 chapter 章写作包生成"在场知情面"摘要：未公开秘密 × 谁知道/谁怀疑/谁误信。
    names_on_stage 提供时只列与在场角色相关的秘密；不提供则列全部未公开秘密（≤8 条）。"""
    data = load_ledger(project)
    secrets = [s for s in data.get("secrets") or [] if s.get("public_since") is None
               or int(s["public_since"]) >= int(chapter)]
    if not secrets:
        return ""
    if names_on_stage:
        stage = set(names_on_stage)

        def _relevant(s):
            people = ({h.get("name") for h in s.get("holders", [])}
                      | {x.get("name") for x in s.get("suspects", [])}
                      | {w.get("name") for w in s.get("wrong_beliefs", [])})
            return bool(people & stage)
        picked = [s for s in secrets if _relevant(s)] or secrets
    else:
        picked = secrets
    lines = ["\n## 知情面提醒（写前必读·台账权威源 knowledge_ledger.json）",
             "> 对白与视角只允许用角色**此刻已知**的信息；让不知情者说破 = 穿帮，让读者早知道的底牌再当大反转 = 泄气。"]
    for s in picked[:8]:
        knows = "、".join(
            f"{h.get('name')}(第{h.get('learned_chapter','?')}章知)" for h in s.get("holders", [])) or "无人"
        sus = "、".join(x.get("name", "") for x in s.get("suspects", []))
        wrong = "；".join(
            f"{w.get('name')}误信「{w.get('believes','')}」" for w in s.get("wrong_beliefs", []))
        reader = (f"读者第{s['reader_knows_since']}章已知" if s.get("reader_knows_since") is not None
                  else "读者未知（悬念型）")
        planned = (f"，计划第{s['planned_reveal_chapter']}章揭示" if s.get("planned_reveal_chapter") else "")
        extra = f"｜怀疑：{sus}" if sus else ""
        extra += f"｜{wrong}" if wrong else ""
        lines.append(f"- **{s['id']}**（{s.get('importance','medium')}）「{s.get('fact','')}」"
                     f"：知情 {knows}{extra}｜{reader}{planned}")
    lines.append("> 本章若有人**新得知/开始怀疑/当众揭示**，写完后用 knowledge_sentry.py learn/suspect/reveal 记账。")
    return "\n".join(lines) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────────────
def _parse_holder(spec):
    """'名字:章号' → holder dict。"""
    if ":" not in spec:
        raise ValueError(f"--holder 需为 名字:得知章号，得到 {spec}")
    name, ch = spec.rsplit(":", 1)
    return {"name": name.strip(), "learned_chapter": int(ch)}


def _split_keywords(s):
    if not s:
        return []
    return [x.strip() for x in re.split(r"[,，、]", s) if x.strip()]


def main():
    p = argparse.ArgumentParser(description="角色知情账：谁在第几章知道了什么秘密")
    p.add_argument("project_path")
    sub = p.add_subparsers(dest="cmd", required=True)

    sa = sub.add_parser("add", help="登记一条秘密")
    sa.add_argument("--fact", required=True, help="秘密内容（一句话）")
    sa.add_argument("--importance", default="medium", help="low|medium|high|critical")
    sa.add_argument("--holder", action="append", default=[], help="初始知情人 名字:得知章号，可多次")
    sa.add_argument("--reader-since", type=int, default=None, help="读者从第几章知道（悬念型留空）")
    sa.add_argument("--planned-reveal", type=int, default=None, help="计划公开揭示章")
    sa.add_argument("--keywords", default=None, help="高辨识度专属词（泄密扫描用），逗号分隔")
    sa.add_argument("--id", default=None)
    sa.add_argument("--linked-seed", default=None, help="关联伏笔台账 SEED id")

    sl = sub.add_parser("learn", help="记某角色得知秘密")
    sl.add_argument("--id", required=True)
    sl.add_argument("--name", required=True)
    sl.add_argument("--at", type=int, required=True, help="得知章号")
    sl.add_argument("--how", default=None, help="得知途径（偷听/告知/推理…）")

    ss = sub.add_parser("suspect", help="记某角色开始怀疑")
    ss.add_argument("--id", required=True)
    ss.add_argument("--name", required=True)
    ss.add_argument("--at", type=int, required=True)

    sr = sub.add_parser("reveal", help="记秘密公开揭示")
    sr.add_argument("--id", required=True)
    sr.add_argument("--at", type=int, required=True, help="公开章号")

    sc = sub.add_parser("scan", help="巡检：结构对账 + 揭示超期 + 泄密候选")
    sc.add_argument("--through", type=int, default=None, help="对账到第几章（默认已写最大章号）")
    sc.add_argument("--grace", type=int, default=DEFAULT_GRACE)

    args = p.parse_args()

    if args.cmd == "add":
        data = load_ledger(args.project_path)
        secret = add_secret(data, args.fact, holders=[_parse_holder(h) for h in args.holder],
                            importance=args.importance, secret_id=args.id,
                            reader_knows_since=args.reader_since,
                            planned_reveal_chapter=args.planned_reveal,
                            tell_keywords=_split_keywords(args.keywords),
                            linked_seed=args.linked_seed)
        save_ledger(args.project_path, data)
        print(f"🔒 登记秘密 {secret['id']}「{secret['fact']}」（知情 {len(secret['holders'])} 人）→ {ledger_path(args.project_path)}")

    elif args.cmd == "learn":
        data = load_ledger(args.project_path)
        entry = learn(data, args.id, args.name, args.at, how=args.how)
        save_ledger(args.project_path, data)
        print(f"👁  {entry['name']} 第{entry['learned_chapter']}章得知 {args.id}")

    elif args.cmd == "suspect":
        data = load_ledger(args.project_path)
        entry = suspect(data, args.id, args.name, args.at)
        save_ledger(args.project_path, data)
        print(f"🤨 {entry['name']} 第{entry['since_chapter']}章开始怀疑 {args.id}")

    elif args.cmd == "reveal":
        data = load_ledger(args.project_path)
        secret = reveal(data, args.id, args.at)
        save_ledger(args.project_path, data)
        print(f"📢 {secret['id']}「{secret['fact']}」第{secret['public_since']}章公开")

    elif args.cmd == "scan":
        report = analyze(args.project_path, through_chapter=args.through, grace=args.grace)
        out_dir = os.path.join(args.project_path, "审稿")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "knowledge_report.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        if not report.get("ran"):
            print(f"⏭️  跳过：{report.get('skipped')}")
            return
        print(f"知情账巡检（对账至第{report.get('through_chapter','?')}章）→ {out}")
        print(f"  秘密 {report.get('total_secrets', 0)} 条 · 未公开 {report.get('open_secrets', 0)} 条 · "
              f"告警 {len(report.get('alerts', []))} 条（阻断 {report.get('blocking', 0)}）")
        for a in report.get("alerts", []):
            loc = f" 第{a['chapter']}章" if a.get("chapter") else ""
            print(f"  [{a['severity']}] {a['kind']}{loc} · {a.get('note','')}")


if __name__ == "__main__":
    main()
