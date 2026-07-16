#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build per-chapter drafting packets for novel-* projects.

This script does not call an AI model. It makes the draft stage repeatable by
materializing the context packet an agent/sub-agent should use before writing a
chapter, plus a state-delta template to fill after the chapter is written.

Usage:
    python3 skills/novel-craft/scripts/draft_packets.py <作品根> --chapter 4
    python3 skills/novel-craft/scripts/draft_packets.py <作品根> --range 4-8
    python3 skills/novel-craft/scripts/draft_packets.py <作品根> --next
"""
import argparse
import json
import os
import re
import sys
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.join(_SKILLS, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from io_utils import load_json  # noqa: E402  本线 _lib 单一真值源
import sweep_schedule  # noqa: E402  小批回扫 due 点单一真值源（含中段防守加密）
from project_io import load_project_settings  # noqa: E402
try:
    from retrieval import relevant_chapters  # noqa: E402  跨窗口语义检索（检索增强长程一致性）
except Exception:  # pragma: no cover
    relevant_chapters = None

from novel_contract import normalize_novel_purpose, resolve_novel_draft_mode, scale_profile
from store import atomic_write_json, atomic_write_text, file_lock
from waivers import append_waiver, make_waiver


CHAPTER_RE = re.compile(r"第\s*0*(\d+)\s*章\s*(?:[《<]([^》>]+)[》>])?\s*(?:[—-]\s*(.*))?")
TRIO_STEPS = ("architect", "ghostwriter", "editor")
# ── 事件类型冷却（P2-⑦：防止模式化流水账） ────────────────────────────────
# 每种事件类型有冷却期（刚用过的类型在冷却期内不得作为主 Beat）和最低出现频次（每 N 章至少一次）。
# 检测基于章纲关键词（与场景检测共用同一 outline beat 文本）。
EVENT_COOLDOWN_PATH = os.path.join("设定", "event_cooldown.json")
EVENT_TYPE_KEYWORDS = {
    "conflict_payoff": ("打脸", "碾压", "秒杀", "虐菜", "打斗", "战斗", "决斗", "反杀", "复仇", "清算", "算账", "爆锤", "横扫"),
    "character_bond": ("羁绊", "交心", "共情", "互诉", "并肩", "守护", "牺牲", "托付", "约定", "和解", "原谅", "心疼", "默契"),
    "faction_management": ("势力", "门派", "联盟", "收编", "整合", "立威", "夺权", "谈判", "博弈", "布局", "暗棋", "站队"),
    "world_flavor": ("风土", "市井", "坊间", "茶楼", "酒楼", "集市", "秘境", "遗迹", "奇观", "古地", "异象", "传说", "歌谣"),
    "crisis_escalation": ("危机", "死局", "绝境", "坑杀", "围杀", "陷阱", "计中计", "反转", "惊变", "曝出", "风暴", "天灾", "兽潮"),
}
EVENT_TYPE_LABELS = {
    "conflict_payoff": "冲突爽点",
    "character_bond": "人物羁绊",
    "faction_management": "势力经营",
    "world_flavor": "风土人情",
    "crisis_escalation": "危机升级",
}
# 冷却规则：(冷却章数, 最低出现间隔章数)。冷却章数=同类事件再次作为主 Beat 的间隔；
# 最低间隔=超此章数未出现则触发提醒（羁绊/风土在爽文里容易被长期跳过）。
EVENT_RULES = {
    "conflict_payoff": {"cooldown": 2, "remind_every": 99},   # 爽文核心无限刷，不需提醒
    "character_bond": {"cooldown": 1, "remind_every": 5},     # 每 5 章至少一次羁绊
    "faction_management": {"cooldown": 1, "remind_every": 99},
    "world_flavor": {"cooldown": 1, "remind_every": 5},       # 每 5 章至少一次风土
    "crisis_escalation": {"cooldown": 3, "remind_every": 99}, # 危级冷却最严
}


def detect_event_types(outline_text):
    """从章纲/beat 文本中检测事件类型。返回 {event_key: bool}。"""
    if not outline_text:
        return {}
    hits = {}
    for ekey, keywords in EVENT_TYPE_KEYWORDS.items():
        if any(kw in outline_text for kw in keywords):
            hits[ekey] = True
    return hits


def event_cooldown_section(root, chapter, outline_text):
    """事件冷却检查：读 event_cooldown.json，检测本章事件类型，输出冷却违规/提醒。

    返回 (section_text, updated_tracker) — 调用方把 updated_tracker 写回 JSON。"""
    tracker_path = os.path.join(root, EVENT_COOLDOWN_PATH)
    tracker = load_json(tracker_path) if os.path.exists(tracker_path) else None
    if not isinstance(tracker, dict) or tracker.get("kind") != "novel_event_cooldown":
        tracker = {"kind": "novel_event_cooldown", "events": [], "last_seen": {}}

    events = tracker.setdefault("events", [])
    last_seen = tracker.setdefault("last_seen", {})

    hit_types = detect_event_types(outline_text)
    warnings = []
    reminders = []

    # 冷却违规检测
    for ekey, active in hit_types.items():
        if not active:
            continue
        last = last_seen.get(ekey)
        if last is not None:
            gap = chapter - last
            cd = EVENT_RULES[ekey]["cooldown"]
            if gap <= cd:
                warnings.append(
                    f"⚠️ {EVENT_TYPE_LABELS[ekey]} 距上次仅 {gap} 章（冷却 {cd} 章）——"
                    f"若本章以此为副 Beat 可忽略；若为主 Beat，建议换类型避免模式化。"
                )

    # 最低出现提醒
    for ekey, remind in {k: v["remind_every"] for k, v in EVENT_RULES.items() if v["remind_every"] < 99}.items():
        last = last_seen.get(ekey, 0)
        gap = chapter - last if last else chapter
        if gap >= remind and ekey not in hit_types:
            reminders.append(
                f"💡 {EVENT_TYPE_LABELS[ekey]} 已 {gap} 章未出现——建议在不迟于第 "
                f"{chapter + max(1, remind - gap)} 章安排一次{EVENT_TYPE_LABELS[ekey]}桥段。"
            )

    # 记录本章事件到 tracker
    for ekey in hit_types:
        last_seen[ekey] = chapter
        events.append({"type": ekey, "chapter": chapter, "label": EVENT_TYPE_LABELS[ekey]})
    # 清理旧记录（保留最近 100 章）
    if len(events) > 200:
        tracker["events"] = [e for e in events if e["chapter"] > chapter - 100]

    if not warnings and not reminders:
        return "", tracker

    lines = ["\n## 事件类型冷却检查"]
    if warnings:
        lines.append("### 冷却违规")
        lines.extend(warnings)
    if reminders:
        lines.append("### 缺失提醒")
        lines.extend(reminders)
    lines.append("> 冷却规则见 `EVENT_TYPE_KEYWORDS`/`EVENT_RULES`；这只是提醒，不阻止写作。")
    return "\n".join(lines) + "\n", tracker


ACTION_SCENE_REFERENCE = "skills/novel-craft/references/action-scenes.md"
ACTION_SCENE_KEYWORDS = {
    "combat": ("打斗", "战斗", "大战", "交手", "厮杀", "搏杀", "拼杀", "对战", "围攻", "反杀", "决斗", "斗法", "巷战"),
    "chase": ("追逐", "追逃", "追杀", "追击", "逃亡", "逃跑", "逃离", "奔逃", "追兵", "甩开", "围堵", "突围"),
    "upgrade": ("升级", "突破", "进阶", "晋级", "境界提升", "破境", "渡劫", "觉醒", "面板", "经验满", "属性提升", "临阵突破"),
}
ACTION_SCENE_LABELS = {
    "combat": "打斗/战斗",
    "chase": "追逐/逃亡",
    "upgrade": "升级/突破",
}
ACTION_SCENE_CHECKLISTS = {
    "combat": (
        "战前写清双方目标、战力差、限制和误判点。",
        "每轮按「动作 -> 反应 -> 结果 -> 新问题」推进，不堆招式名。",
        "至少保留一种代价：伤势、资源消耗、暴露底牌、误伤、时间损失或关系裂痕。",
        "胜负理由来自布局、信息、代价或性格选择，不能作者硬按。",
    ),
    "chase": (
        "写清追逃双方的相对距离如何变化，禁止凭空追上或甩开。",
        "给路线锚和障碍：街巷/屋脊/山道/人群/岔路/伤腿/负重等。",
        "追逐必须消耗体力、灵力、马力、载具、道具或隐蔽性，并影响后续动作。",
        "设置明确终点或倒计时：城门关闭、援兵抵达、毒发、天亮、阵法合拢等。",
    ),
    "upgrade": (
        "突破必须有触发条件：积累、危机、悟到规则、外部机缘或牺牲。",
        "让阈值可见：经验满、灵力冲关、瓶颈松动、面板提示、旧伤反噬。",
        "收益要具体：新增能力、属性变化、感知变化或打法变化。",
        "升级后的战力必须符合 power_system_registry；越级需代价、机缘或限制。",
    ),
}
REVEAL_SCENE_REFERENCE = "skills/novel-craft/references/reveal-scenes.md"
CONFRONTATION_SCENE_REFERENCE = "skills/novel-craft/references/confrontation-scenes.md"
RELATIONSHIP_SCENE_REFERENCE = "skills/novel-craft/references/relationship-scenes.md"
SCENE_GUIDES = (
    {
        "key": "action",
        "reference": ACTION_SCENE_REFERENCE,
        "heading": "专项场景写作清单（自动命中）",
        "lead": "本章先写目标和空间，再写动作；每 300-600 字必须有局势变化或代价增加。",
        "keywords": ACTION_SCENE_KEYWORDS,
        "labels": ACTION_SCENE_LABELS,
        "checklists": ACTION_SCENE_CHECKLISTS,
        "state_note": "本场造成的伤势、消耗、道具损坏、暴露底牌、关系变化、境界变化必须写入 `state_delta`。",
    },
    {
        "key": "reveal",
        "reference": REVEAL_SCENE_REFERENCE,
        "heading": "揭示场景写作清单（自动命中）",
        "lead": "本章先写清谁知道、谁不知道、证据从哪里来，再写反应；揭示不是解释设定，而是改变局势。",
        "keywords": {
            "identity": ("身份曝光", "身份揭露", "掉马", "马甲暴露", "真实身份", "认亲", "身世", "血脉", "冒名", "替身"),
            "truth": ("真相揭示", "真相大白", "揭穿", "揭露", "拆穿", "证据链", "血书", "遗诏", "密信", "内鬼", "背叛真相"),
            "secret": ("秘密暴露", "旧案", "隐情", "封印记忆", "被隐瞒", "伪装", "假死", "幕后黑手"),
        },
        "labels": {
            "identity": "身份曝光/掉马",
            "truth": "真相揭示/证据揭穿",
            "secret": "秘密暴露/旧案回收",
        },
        "checklists": {
            "identity": (
                "写清身份揭示前后，主角的权力、危险或关系地位发生了什么变化。",
                "掉马必须有外部证据或行为破绽，不能只靠旁白宣布。",
                "至少安排一个误判者的反应：否认、沉默、反咬、崩溃或立刻改站队。",
            ),
            "truth": (
                "证据链按「线索 -> 指向 -> 反驳 -> 反证」递进，不一次性倒完设定。",
                "揭穿时保留一个未尽问题，作为下一章动作或集尾钩子。",
                "真相必须迫使角色做选择：认罪、逃跑、翻脸、保护、牺牲或交易。",
            ),
            "secret": (
                "旧秘密回收要标出对应伏笔或前文疑点，避免像临时补丁。",
                "秘密公开后立刻改变至少一条关系线、敌我线或目标线。",
                "不要用大段说明替代现场动作；让证物、表情、沉默和打断承载信息。",
            ),
        },
        "state_note": "本场揭示的新身份、真相、旧案状态、知情人范围和未回答问题必须写入 `state_delta`。",
    },
    {
        "key": "confrontation",
        "reference": CONFRONTATION_SCENE_REFERENCE,
        "heading": "对质/智斗场景写作清单（自动命中）",
        "lead": "本章先写赌注和权力位置，再写证据递进；对质的爽感来自权力翻转，不来自吵得更大声。",
        "keywords": {
            "public": ("公开对质", "当众对质", "当众揭穿", "公堂", "朝堂", "宴席发难", "众目睽睽", "围观", "打脸"),
            "interrogation": ("审讯", "逼问", "盘问", "质问", "拷问", "问供", "套话", "审问"),
            "negotiation": ("谈判", "交易", "交涉", "博弈", "智斗", "设局", "反制", "反将一军", "权谋"),
        },
        "labels": {
            "public": "公开对质/当众打脸",
            "interrogation": "审讯/逼问",
            "negotiation": "谈判/智斗",
        },
        "checklists": {
            "public": (
                "写清现场规则：谁有话语权，谁能裁决，围观者为什么重要。",
                "证据每抛一次，权力位置要变化一次：沉默、倒戈、失态、反击或被迫承认。",
                "当众打脸必须给被打脸者一个反扑动作，避免单向碾压变平。",
            ),
            "interrogation": (
                "逼问要有筹码：证据、时间、疼痛、利益、亲人、把柄或心理漏洞。",
                "每一问都推进信息，不写重复威胁；回答可以是谎言，但要留下可验证裂缝。",
                "审讯结束必须带出新行动：抓人、放人、交易、灭口、逃脱或更大嫌疑。",
            ),
            "negotiation": (
                "谈判双方都要有底线和可让步项；不能只有主角单方面聪明。",
                "智斗至少包含一个信息差和一个反信息差，让胜负来自布局而非降智。",
                "交易结果要留下代价或后患，方便后续章节继续滚动。",
            ),
        },
        "state_note": "本场产生的证据归属、权力翻转、交易条款、敌我变化和新增把柄必须写入 `state_delta`。",
    },
    {
        "key": "relationship",
        "reference": RELATIONSHIP_SCENE_REFERENCE,
        "heading": "关系情绪场景写作清单（自动命中）",
        "lead": "本章先标关系温度变化，再写动作和台词；情绪兑现必须让关系进入不可完全回退的新状态。",
        "keywords": {
            "confession": ("告白", "表白", "承认心意", "心动", "定情", "吻", "亲吻", "牵手", "拥抱"),
            "break": ("决裂", "分手", "翻脸", "误会爆发", "反目", "绝交", "背离", "离开他", "离开她"),
            "repair": ("和解", "破镜重圆", "救赎", "疗伤", "互相救场", "吃醋", "护短", "原谅", "冰释前嫌"),
        },
        "labels": {
            "confession": "告白/心动兑现",
            "break": "决裂/误会爆发",
            "repair": "和解/救赎/互相救场",
        },
        "checklists": {
            "confession": (
                "告白前要有压抑、误会、危机或选择压力；不能凭空甜。",
                "用一个具体动作兑现情绪：递物、挡刀、停步、收手、靠近或主动承认。",
                "台词要有潜台词，避免把所有感受解释成独白。",
            ),
            "break": (
                "决裂必须有触发点：谎言暴露、价值冲突、保护失败、身份差或旧伤复燃。",
                "让双方都付出代价，别把一方写成纯工具人。",
                "结尾留下可追的裂缝：误会未解、证据缺一环、仍有牵挂或共同敌人逼近。",
            ),
            "repair": (
                "和解不是一句道歉，要有补偿动作、风险承担或旧承诺兑现。",
                "救赎场景要写清被救者选择，而不是只被拯救。",
                "关系回暖后必须改变下一章行为：信任额度、称谓、距离、阵营或共同目标。",
            ),
        },
        "state_note": "本场关系温度、称谓变化、承诺、误会状态、阵营/信任变化必须写入 `state_delta`。",
    },
)

# 女频情感清单：题材门控注入（不靠章纲关键词，靠项目 genre/平台/用途判定）。
# 女频/言情向项目里情感线是主产品，逐章都需要颗粒度/CP张力/糖度意识，故按题材整体注入，
# 区别于 SCENE_GUIDES 的「章纲命中才注入」。
FEMALE_FICTION_REFERENCE = "skills/novel-craft/references/女频情感.md"
FEMALE_FICTION_KEYWORDS = (
    "言情", "甜宠", "宠文", "古言", "现言", "女频", "大女主", "宫斗", "宅斗",
    "先婚后爱", "破镜重圆", "虐恋", "虐文", "情感线", "婚后", "双洁", "暗恋",
    "豪门", "婚恋", "be美学", "破镜", "总裁文", "霸总", "种田文",
)
FEMALE_FICTION_PLATFORMS = ("晋江",)
FEMALE_FICTION_CHECKLIST = (
    "情绪写颗粒度：心动/心痛拆成生理反应+微动作+念头三层，别只贴「心动/心碎」标签。",
    "内心戏 ≤150 字一气且要有转折/矛盾，不做情绪复读；能用动作或潜台词演的别用独白说破。",
    "CP 关系温度只进不退；误会靠信息差或性格、不靠降智维持；心动/确认/和解等里程碑由人物挣来。",
    "甜虐有呼吸：撒糖前先给小障碍，避免匀速发糖（腻）或匀速虐（疲劳）；大甜压在里程碑。",
    "对照本项目 `设定/读者契约.md` 的价值边界，避开已登记的女频雷点（男非洁/出轨/用强/BE 无预期/圣母女主/虐女主无底线/副 CP 抢主线）。",
)

RESEARCH_INDEX_REL = "资料/research_sources.json"
OBSERVATION_PACKET_REL_FMT = "写作任务/观察素材_第{chapter:02d}章.md"
OBSERVATION_BANK_REL = "素材/观察素材库.md"
AESTHETIC_BANK_REL = "设定/aesthetic_bank.json"
AESTHETIC_BANK_MD_REL = "设定/审美样本库.md"
SCENE_CARDS_REL = "设定/scene_cards.json"
SCENE_CARDS_REFERENCE = "skills/novel-craft/references/scene-cards.md"
ARC_SUMMARIES_REL = "设定/arc_summaries.json"
EMOTIONAL_PROGRESS_REL = "设定/emotional_progression.json"
ARC_MEMORY_REFERENCE = "skills/novel-craft/references/arc-memory.md"

COMMON_SOURCE_PATHS = (
    "设定/章纲.md",
    "设定/读者契约.md",
    "审稿/demo_gate.json",
    "审稿/state_ledger.json",
)

SOURCE_PATHS_BY_KIND = {
    "create": (
        "设定/创作蓝图.md",
        "设定/设定圣经.md",
        "设定/角色卡.md",
        "设定/世界观.md",
    ),
    "rewrite": (
        "原作.txt",
        "设定/改动spec.md",
        "设定/新设定.md",
        "设定/角色卡.md",
        "设定/世界观.md",
    ),
    "spinoff": (
        "原作.txt",
        "设定/锚点表.json",
        "设定/角色卡.md",
        "设定/世界观.md",
    ),
    "continue": (
        "原作.txt",
        "设定/人物.md",
        "设定/世界观.md",
        "设定/主线骨架.json",
        "设定/末章状态.md",
        "设定/作者口吻.md",
        "设定/续写方向.md",
    ),
    "expand": (
        "原作.txt",
        "设定/事件骨架.json",
        "设定/人物.md",
        "设定/世界观.md",
        "设定/章节映射.md",
    ),
    "condense": (
        "原作.txt",
        "设定/人物.md",
        "设定/主线骨架.json",
        "设定/章节映射.md",
    ),
}


def read_text(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def clip(text, limit=2200):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...（已截断；写章时按路径读取原文件）"


def fmt_list(value):
    if not value:
        return "未填写"
    if isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return "、".join(items) if items else "未填写"
    return str(value).strip() or "未填写"


def chapter_path(root, chapter):
    return os.path.join(root, "章节", f"第{chapter:02d}章.md")


def existing_chapters(root):
    chdir = os.path.join(root, "章节")
    if not os.path.isdir(chdir):
        return set()
    nums = set()
    for name in os.listdir(chdir):
        m = re.search(r"第0*(\d+)章", name)
        if m and name.endswith(".md"):
            nums.add(int(m.group(1)))
    return nums


def parse_outline(root):
    text = read_text(os.path.join(root, "设定", "章纲.md"))
    outline = {}
    for raw in text.splitlines():
        m = CHAPTER_RE.search(raw)
        if not m:
            continue
        chapter = int(m.group(1))
        title = (m.group(2) or "").strip()
        beat = (m.group(3) or raw).strip()
        outline.setdefault(chapter, {"title": title, "beat": beat, "raw": raw.strip()})
    return outline


def load_demo_gate(root, allow_missing=False):
    path = os.path.join(root, "审稿", "demo_gate.json")
    data = load_json(path, None)
    if not data:
        if allow_missing:
            return {}
        raise RuntimeError("缺少 审稿/demo_gate.json；Demo gate 通过前不要批量写章。可加 --allow-missing-demo 只生成准备包。")
    status = data.get("status")
    if status != "passed" and not allow_missing:
        raise RuntimeError(f"Demo gate 未通过：status={status!r}；不能进入批量写章。")
    return data


def require_reader_contract(root, allow_missing=False):
    """读者契约是逐章写作的承重输入（题旨/读者承诺/文学质感）；缺它批量写章会失锚。
    与 demo_gate 同档硬闸：默认缺失即阻断，--allow-missing-reader-contract 才放行（记 waiver）。"""
    path = os.path.join(root, "设定", "读者契约.md")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True
    if allow_missing:
        return False
    raise RuntimeError(
        "缺少 设定/读者契约.md；批量写章前先按 novel-craft/references/reader-contract.md "
        "补题旨/读者承诺/文学质感/禁偏清单。可加 --allow-missing-reader-contract 暂时跳过（会记 waiver）。"
    )


def state_ledger_path(root):
    return os.path.join(root, "审稿", "state_ledger.json")


def state_ledger_lock_path(root):
    return os.path.join(root, "审稿", "state_ledger.lock")


def default_state_ledger():
    return {
        "schema_version": 1,
        "kind": "novel_state_ledger",
        "updated_at": date.today().isoformat(),
        "characters": {},
        "setting_facts": [],
        "open_threads": [],
        "resolved_threads": [],
        "chapter_deltas": {},
    }


def _ensure_state_ledger_unlocked(root):
    path = os.path.join(root, "审稿", "state_ledger.json")
    if os.path.exists(path):
        return load_json(path, {})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = default_state_ledger()
    atomic_write_json(path, data)
    return data


def ensure_state_ledger(root):
    with file_lock(state_ledger_lock_path(root)):
        return _ensure_state_ledger_unlocked(root)


def record_ledger_waiver(root, waiver):
    path = state_ledger_path(root)
    with file_lock(state_ledger_lock_path(root)):
        ledger = _ensure_state_ledger_unlocked(root)
        waivers = ledger.setdefault("waivers", [])
        if not any(w.get("id") == waiver.get("id") for w in waivers):
            waivers.append(waiver)
            ledger["updated_at"] = date.today().isoformat()
            atomic_write_json(path, ledger)


def previous_chapter_excerpt(root, chapter):
    if chapter <= 1:
        return "（无上一章）"
    path = chapter_path(root, chapter - 1)
    text = read_text(path)
    if not text:
        return f"（缺上一章文件：章节/第{chapter - 1:02d}章.md）"
    return clip(text[-1800:], 1800)


def recent_chapters_excerpt(root, chapter, near=3):
    """N-1 全尾 + N-2/N-3 短尾，填平"近章上下文黑洞"。

    此前写章包只注入 chapter-1 的末尾，而检索又刻意排除近 window(=3) 章——于是刚发生
    在 N-2/N-3 的即时因果（刚立的 flag、刚受的伤、刚约定的会面）在写下一章时既不在
    "上一章承接"、也不在检索召回里，是最隐蔽的衔接断裂点。这里对 N-1 给末尾 1800 字，
    对 N-2/N-3 各给末尾 ~400 字尾段，让紧邻数章的收束状态始终在场。"""
    if chapter <= 1:
        return "（无上一章）"
    blocks = []
    prev_text = read_text(chapter_path(root, chapter - 1))
    if prev_text:
        blocks.append(f"### 上一章（第{chapter - 1:02d}章）结尾\n{clip(prev_text[-1800:], 1800)}")
    else:
        blocks.append(f"（缺上一章文件：章节/第{chapter - 1:02d}章.md）")
    for back in range(2, near + 1):
        idx = chapter - back
        if idx < 1:
            continue
        text = read_text(chapter_path(root, idx))
        if text:
            blocks.append(f"### 第{idx:02d}章 收尾（近章因果回顾·勿与上一章混淆时序）\n{clip(text[-400:], 400)}")
    return "\n\n".join(blocks)


def alias_expansions(root, names):
    """给定在场角色规范名，返回其别名列表（读 设定/角色别名.json 的 aliases: {规范名:[别名]}）。

    用于检索 query 的离线"伪语义"扩展：把角色的封号/尊称/旧名并入 query，跨称呼召回同一人的旧场景。
    别名表缺失/坏 → []（优雅跳过）。"""
    alias_map = load_json(os.path.join(root, "设定", "角色别名.json"), {}) or {}
    aliases = alias_map.get("aliases") if isinstance(alias_map, dict) else None
    if not isinstance(aliases, dict):
        return []
    out = []
    name_set = set(names)
    for canonical, alist in aliases.items():
        if canonical in name_set and isinstance(alist, list):
            out.extend(str(a) for a in alist if a)
    return out


FORESHADOW_GRACE = 5  # 与 foreshadow_ledger.DEFAULT_GRACE / logic_sentry 宽容窗一致


def foreshadow_section_for_chapter(root, chapter, grace=FORESHADOW_GRACE):
    """读 novel-wiki 权威伏笔台账，注入本章"该收/该补收"的伏笔清单。

    只读、不改台账（确定性）：pending 且 confirmed 的伏笔，若 expected_payoff_chapter 落在
    [chapter-grace, chapter+grace] → "到期该考虑回收"；若 chapter 已 > expected+grace →
    "已超期，尽快补收或显式 drop"。让 AI 在写这一章时就看得见坑，而不是等 scan 事后报烂尾。"""
    ledger = load_json(os.path.join(root, "设定", "foreshadowing_ledger.json"), {}) or {}
    seeds = ledger.get("seeds") or []
    due, overdue = [], []
    for s in seeds:
        if s.get("status") != "pending" or not s.get("confirmed", True):
            continue
        exp = s.get("expected_payoff_chapter")
        if exp is None:
            continue
        exp = int(exp)
        if chapter > exp + grace:
            overdue.append(s)
        elif exp - grace <= chapter <= exp + grace:
            due.append(s)
    if not due and not overdue:
        return ""
    lines = ["\n## 伏笔回收提醒（写前必读·台账权威源 foreshadowing_ledger.json）"]
    if due:
        lines.append("> 以下伏笔的预期回收窗口覆盖本章，若剧情合适应在本章或邻近数章内回收（回收后跑 foreshadow_ledger.py payoff 登记）：")
        for s in due:
            ent = "、".join(s.get("linked_entities") or []) or "—"
            twist = "，⚡twist型：回收即预期违背，务必做到「意料之外、情理之中」" if s.get("payoff_is_twist") else ""
            lines.append(f"- **{s.get('id')}**（{s.get('importance','medium')}·预期第{s['expected_payoff_chapter']}章）：{s.get('description','')}（相关：{ent}）{twist}")
    if overdue:
        lines.append("> ⚠️ 以下伏笔已超期未收，本章优先考虑补收或显式作废（drop），避免烂尾：")
        for s in overdue:
            lines.append(f"- **{s.get('id')}**（{s.get('importance','medium')}·预期第{s['expected_payoff_chapter']}章·已超期）：{s.get('description','')}")
    return "\n".join(lines) + "\n"


def setting_value(root, key):
    return load_project_settings(root).get(key, "")


def purpose_from_settings(root, meta):
    value = setting_value(root, "小说用途") or meta.get("purpose") or setting_value(root, "目标用途")
    value = normalize_novel_purpose(value)
    if value in {"", "未定", "（未定）", "未指定"}:
        return ""
    return value


def draft_mode_from_settings(root, meta):
    value = setting_value(root, "小说生成模式")
    if value:
        return value
    meta_mode = meta.get("draft_mode")
    explicit_mode = None if meta_mode in {"", None, "稳妥初稿"} else meta_mode
    return resolve_novel_draft_mode(
        explicit_mode,
        purpose=purpose_from_settings(root, meta),
        platform=meta.get("target_platform"),
        scale=meta.get("scale"),
        fallback=meta_mode or "稳妥初稿",
    )


def draft_workflow_from_settings(root, meta):
    value = setting_value(root, "小说生成工作流")
    if value:
        return value
    return meta.get("draft_workflow") or meta.get("writing_workflow") or ""


def text_authorship_mode_from_settings(root, meta):
    return (
        setting_value(root, "文本主创模式")
        or meta.get("text_authorship_mode")
        or ("AI辅助" if meta.get("target_platform") else "")
    )


def live_check_workflow_from_settings(root, meta):
    workflow = str(draft_workflow_from_settings(root, meta) or "默认单步")
    lowered = workflow.lower()
    return "边写边自检" in workflow or "live" in lowered or "write-check" in lowered


def batch_review_interval_from_settings(root, meta):
    value = (
        setting_value(root, "小批回扫间隔")
        or meta.get("batch_review_interval")
        or meta.get("review_interval")
        or "5章"
    )
    text = str(value or "").strip().lower()
    if text in {"", "关闭", "off", "none", "0", "0章"}:
        return 0
    match = re.search(r"(\d+)", text)
    if not match:
        return 5
    return max(1, int(match.group(1)))


def batch_review_window(chapter, interval, meta):
    # due 点计算收口到 novel/_lib/sweep_schedule（单一真值源）：基础平铺 + 项目尾 +
    # 中段防守加密（40-60% 进度带按半间隔加密——长篇矛盾高发区，见该模块 docstring）。
    if interval <= 0:
        return None
    target = int(meta.get("target_chapters") or 0)
    if sweep_schedule.is_due(chapter, interval, target):
        start, end = sweep_schedule.window_for(chapter, interval, target)
        return {"due": True, "start": start, "end": end}
    next_due = sweep_schedule.next_due_after(chapter, interval, target)
    if target and next_due:
        next_due = min(next_due, target)
    return {"due": False, "next_due": next_due}


def use_trio_pipeline(root, meta):
    mode = draft_mode_from_settings(root, meta)
    workflow = str(draft_workflow_from_settings(root, meta) or "")
    workflow_lower = workflow.lower()
    if "默认单步" in workflow or "single" in workflow_lower:
        return False
    if "三步" in workflow or "trio" in workflow_lower:
        return True
    scale = str(meta.get("scale") or "").lower()
    try:
        target_chapters = int(meta.get("target_chapters") or 0)
    except (TypeError, ValueError):
        target_chapters = 0
    return (
        mode in {"商业连载", "漫剧源书"}
        or scale in {"long", "长篇"}
        or target_chapters >= 30
    )


def packet_steps_for_request(root, requested_step):
    if requested_step == "trio":
        return list(TRIO_STEPS)
    if requested_step != "auto":
        return [requested_step]
    meta = load_json(os.path.join(root, "_meta.json"), {})
    return list(TRIO_STEPS) if use_trio_pipeline(root, meta) else ["full"]


def target_words(meta):
    if meta.get("target_words_per_chapter"):
        return meta["target_words_per_chapter"]
    scale = meta.get("scale")
    if scale:
        try:
            return scale_profile(scale)["words_per_chapter"]
        except KeyError:
            pass
    return [1000, 1800]


def source_paths_for_kind(kind):
    """Return the context files a chapter packet must make the writer read."""
    paths = list(SOURCE_PATHS_BY_KIND.get(kind or "", SOURCE_PATHS_BY_KIND["create"]))
    paths.extend(COMMON_SOURCE_PATHS)
    out = []
    seen = set()
    for path in paths:
        if path not in seen:
            out.append(path)
            seen.add(path)
    return out


def scene_match_text(outline_item):
    """Collect chapter outline text used by deterministic scene guide matching."""
    return "\n".join(
        str(outline_item.get(key) or "")
        for key in ("title", "beat", "raw")
    )


def guide_tags_for_outline(outline_item, guide):
    """Detect scene guide tags from chapter title/outline text."""
    text = scene_match_text(outline_item)
    tags = []
    for tag, keywords in guide["keywords"].items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags


def action_scene_tags_for_outline(outline_item):
    """Detect high-motion scene types from chapter title/outline text."""
    return guide_tags_for_outline(outline_item, SCENE_GUIDES[0])


def scene_guide_matches(outline_item):
    matches = []
    for guide in SCENE_GUIDES:
        tags = guide_tags_for_outline(outline_item, guide)
        if tags:
            matches.append((guide, tags))
    return matches


def scene_guide_references(matches):
    refs = []
    seen = set()
    for guide, _tags in matches:
        ref = guide["reference"]
        if ref not in seen:
            refs.append(ref)
            seen.add(ref)
    return refs


def scene_guide_section(guide, tags):
    if not tags:
        return ""
    labels = "、".join(guide["labels"][tag] for tag in tags)
    lines = [
        f"\n## {guide['heading']}",
        f"- 命中类型：{labels}",
        f"- 参考全文：`{guide['reference']}`",
        f"- {guide['lead']}",
    ]
    for tag in tags:
        lines.append(f"\n### {guide['labels'][tag]}")
        for item in guide["checklists"][tag]:
            lines.append(f"- {item}")
    lines.append("\n### 状态增量提醒")
    lines.append(f"- {guide['state_note']}")
    return "\n".join(lines) + "\n"


def scene_guide_sections(matches):
    return "".join(scene_guide_section(guide, tags) for guide, tags in matches)


def action_scene_section(tags):
    """Backward-compatible wrapper for the action scene guide."""
    return scene_guide_section(SCENE_GUIDES[0], tags)


def female_fiction_signal_text(root, meta):
    """Collect project-level genre/platform/purpose text used for 女频 gating."""
    parts = [
        str(meta.get("genre") or ""),
        str(meta.get("target_platform") or ""),
        str(purpose_from_settings(root, meta) or ""),
        str(setting_value(root, "题材") or ""),
        str(setting_value(root, "目标平台") or ""),
    ]
    return "\n".join(p for p in parts if p)


def female_fiction_active(root, meta):
    """Genre-gate: True when the project reads as 女频/言情向 (情感线 is the product)."""
    text = female_fiction_signal_text(root, meta)
    if any(keyword in text for keyword in FEMALE_FICTION_KEYWORDS):
        return True
    if any(platform in text for platform in FEMALE_FICTION_PLATFORMS):
        return True
    return False


def female_fiction_section():
    lines = [
        "\n## 女频情感写作清单（题材命中）",
        f"- 参考全文：`{FEMALE_FICTION_REFERENCE}`",
        "- 本项目题材/平台判定为女频·言情向，情感线是主产品，逐章按下列清单写：",
    ]
    for item in FEMALE_FICTION_CHECKLIST:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def research_chapter_applies(value, chapter):
    """Whether a research pack/fact applies to the current chapter.

    Keep this local instead of importing novel-research so draft packet
    generation remains tolerant when only novel-craft is distributed.
    """
    if value in (None, "", []):
        return False
    if isinstance(value, str):
        values = [value]
    else:
        values = value if isinstance(value, list) else [value]
    for item in values:
        if item == "all":
            return True
        if isinstance(item, int) and item == chapter:
            return True
        text = str(item)
        if text.isdigit() and int(text) == chapter:
            return True
        m = re.match(r"^0*(\d+)\s*[-~至]\s*0*(\d+)$", text)
        if m and int(m.group(1)) <= chapter <= int(m.group(2)):
            return True
    return False


def research_packs_for_chapter(root, chapter, outline_item):
    """Return professional research packs applicable to a chapter."""
    payload = load_json(os.path.join(root, RESEARCH_INDEX_REL), {}) or {}
    packs = payload.get("packs") or []
    if not isinstance(packs, list):
        return []
    match_text = scene_match_text(outline_item)
    out = []
    for pack in packs:
        if not isinstance(pack, dict):
            continue
        applies = research_chapter_applies(pack.get("applicable_chapters"), chapter)
        keywords = pack.get("keywords") or []
        keyword_hit = bool(match_text and keywords and any(str(kw) in match_text for kw in keywords))
        if applies or keyword_hit:
            out.append(pack)
    return out


def research_pack_section(packs):
    """Human-readable packet section for evidence-backed professional facts."""
    if not packs:
        return ""
    lines = [
        "\n## 专业资料包（自动命中）",
        "- 本章涉及专业/行业事实时，只能把 ready 资料包中有来源的 facts 写成确定事实；不确定项和禁用项不得写成旁白定论。",
        "- 若资料包不是 ready，本章只能写准备稿或先回 `novel-research` 补证据。",
    ]
    for pack in packs:
        path = pack.get("pack_path") or "未写 pack_path"
        claims = pack.get("claims") or []
        forbidden = pack.get("forbidden_items") or []
        uncertain = pack.get("uncertain_items") or []
        status = pack.get("status", "draft")
        is_ready = status == "ready"
        # 非 ready 包不把 facts 呈现为可写事实——只标"未定稿·先补证据"，避免文案说"只用 ready"、
        # 正文却把未定稿 facts 当确定事实写（G8）。
        head = (
            f"- **{pack.get('topic') or pack.get('topic_slug') or '未命名'}** "
            f"[{pack.get('domain', 'other')}/{pack.get('risk_level', 'medium')}/{status}] `{path}`；"
        )
        if is_ready:
            lines.append(head + f"facts={len(claims)}（可作确定事实写入）")
        else:
            lines.append(head + f"⚠ 未 ready（{status}）：本章**不得**把该包 facts 写成确定事实；"
                                f"先回 `novel-research` 补齐/定稿，或本章只写准备稿。")
        if uncertain:
            lines.append(f"  - 不确定项（禁止写成旁白定论）：{'；'.join(str(x) for x in uncertain[:3])}")
        if forbidden:
            lines.append(f"  - 禁用项（不得出现）：{'；'.join(str(x) for x in forbidden[:3])}")
    return "\n".join(lines) + "\n"


def observation_packet_section(root, chapter):
    """Return selected life-observation material for this chapter."""
    packet_rel = OBSERVATION_PACKET_REL_FMT.format(chapter=chapter)
    packet_path = os.path.join(root, packet_rel)
    if os.path.exists(packet_path):
        text = read_text(packet_path)
        return (
            "\n## 生活观察素材（逐章精选）\n"
            f"- 来源：`{packet_rel}`\n"
            "- 用法：把动作、五感、职业细节和生活逻辑转写进场景，不要原样堆资料。\n\n"
            f"{clip(text, 1800)}\n",
            [packet_rel],
        )
    bank_path = os.path.join(root, OBSERVATION_BANK_REL)
    if os.path.exists(bank_path):
        return (
            "\n## 生活观察素材（待选择）\n"
            f"- 已存在 `{OBSERVATION_BANK_REL}`，但本章没有精选包 `{packet_rel}`。\n"
            "- 建议先跑 `python3 skills/novel-observe/scripts/observe.py select \"<作品根>\" --chapter "
            f"{chapter} --write-packet`，再生成写章包。\n",
            [OBSERVATION_BANK_REL],
        )
    return "", []


def aesthetic_bank_section(root):
    """Return transferable positive craft rules from the aesthetic bank."""
    refs: list[str] = []
    bank_path = os.path.join(root, AESTHETIC_BANK_REL)
    md_path = os.path.join(root, AESTHETIC_BANK_MD_REL)
    if os.path.exists(bank_path):
        refs.append(AESTHETIC_BANK_REL)
        payload = load_json(bank_path, {}) or {}
        samples = payload.get("samples") if isinstance(payload, dict) else []
        if isinstance(samples, list) and samples:
            # 选样不再无差别取前 3：优先保证 novelty/surprise/premise 维度样本进包（至多 2 条），
            # 否则登记了想象力样本也永远轮不到注入（B2）；再用工艺样本补满到 3 条。
            novelty_dims = {"novelty", "surprise", "premise"}
            valid = [s for s in samples if isinstance(s, dict)]
            novelty_samples = [s for s in valid if novelty_dims.intersection(set(s.get("dimensions") or []))]
            picked, seen = [], set()
            for s in (novelty_samples[:2] + valid):
                sid = id(s)
                if sid in seen:
                    continue
                seen.add(sid)
                picked.append(s)
                if len(picked) >= 3:
                    break
            lines = [
                "\n## 正向审美样本（迁移规则）",
                "- 只迁移机制，不复制样本文句、专名或在世作者风格。",
            ]
            for sample in picked:
                is_novelty = bool(novelty_dims.intersection(set(sample.get("dimensions") or [])))
                tag = "🌟新颖度样本 · " if is_novelty else ""
                lines.append(f"\n### {tag}{sample.get('sample_id') or 'AES'} · {sample.get('source_title') or '未命名样本'}")
                lines.append(f"- 维度：{fmt_list(sample.get('dimensions'))}")
                lines.append(f"- 为什么有效：{sample.get('why_it_works') or '未填写'}")
                if sample.get("why_it_is_new"):
                    lines.append(f"- 新在哪（可迁移的不落俗套点）：{sample.get('why_it_is_new')}")
                lines.append(f"- 可迁移规则：{sample.get('transfer_rule') or '未填写'}")
                if sample.get("anti_copy_note"):
                    lines.append(f"- 禁抄说明：{sample.get('anti_copy_note')}")
                if sample.get("applicable_when"):
                    lines.append(f"- 适用：{sample.get('applicable_when')}")
            return "\n".join(lines).rstrip() + "\n", refs
        raw = json.dumps(payload, ensure_ascii=False, indent=2) if isinstance(payload, dict) else read_text(bank_path)
        return (
            "\n## 正向审美样本（待补全）\n"
            f"- 来源：`{AESTHETIC_BANK_REL}`；样本库为空或 schema 不完整，line edit 前先补 `why_it_works` / `transfer_rule`。\n\n"
            f"```json\n{clip(raw, 1200)}\n```\n",
            refs,
        )
    if os.path.exists(md_path):
        refs.append(AESTHETIC_BANK_MD_REL)
        return (
            "\n## 正向审美样本（人工库）\n"
            f"- 来源：`{AESTHETIC_BANK_MD_REL}`；优先迁移“为什么有效/可迁移规则”，不要复刻样本文句。\n\n"
            f"{clip(read_text(md_path), 1400)}\n",
            refs,
        )
    return "", refs


def scene_cards_for_chapter(root, chapter):
    """Return scene cards for this chapter if the project has scene_cards.json."""
    payload = load_json(os.path.join(root, SCENE_CARDS_REL), {}) or {}
    scenes = payload.get("scenes") if isinstance(payload, dict) else []
    if not isinstance(scenes, list):
        return []
    out = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        try:
            ch = int(scene.get("chapter") or 0)
        except (TypeError, ValueError):
            ch = 0
        if ch == chapter:
            out.append(scene)
    out.sort(key=lambda s: (int(s.get("scene_no") or 0), s.get("id") or ""))
    return out


def scene_cards_section(cards):
    if not cards:
        return ""
    lines = [
        "\n## 场景卡（Scene Cards · 写时逐场兑现）",
        f"- 参考全文：`{SCENE_CARDS_REFERENCE}`",
        "- 每个场景必须有目标、阻碍、冲突、转折和价值变化；没有转折的场景要合并、删除或重写。",
    ]
    for card in cards:
        lines.append(f"\n### {card.get('id') or 'SCENE'} · 第{card.get('scene_no') or '?'}场")
        for key, label in (
            ("pov", "POV"),
            ("location", "地点"),
            ("time", "时间"),
            ("desire", "目标"),
            ("obstacle", "阻碍"),
            ("conflict", "冲突"),
            ("turn", "转折"),
            ("value_shift", "价值变化"),
            ("reveal_or_payoff", "揭示/兑现"),
            ("subtext", "潜台词"),
            ("sensory_anchor", "五感锚点"),
        ):
            value = str(card.get(key) or "").strip()
            lines.append(f"- {label}：{value or '（待补；写前先补 scene card）'}")
    return "\n".join(lines) + "\n"


def parse_chapter_range(value):
    m = re.fullmatch(r"\s*0*(\d+)\s*[-~至]\s*0*(\d+)\s*", str(value or ""))
    if not m:
        return None
    start, end = int(m.group(1)), int(m.group(2))
    if start > end:
        start, end = end, start
    return start, end


def arc_memory_for_chapter(root, chapter):
    payload = load_json(os.path.join(root, ARC_SUMMARIES_REL), {}) or {}
    arcs = payload.get("arcs") if isinstance(payload, dict) else []
    out = []
    if isinstance(arcs, list):
        for arc in arcs:
            if not isinstance(arc, dict):
                continue
            rng = parse_chapter_range(arc.get("range"))
            if rng and rng[0] <= chapter <= rng[1]:
                out.append(arc)
    emo = load_json(os.path.join(root, EMOTIONAL_PROGRESS_REL), {}) or {}
    emotions = []
    if isinstance(emo, dict):
        for item in emo.get("chapters") or []:
            if not isinstance(item, dict):
                continue
            try:
                ch = int(item.get("chapter") or 0)
            except (TypeError, ValueError):
                ch = 0
            if ch == chapter:
                emotions.append(item)
    return out, emotions


def arc_memory_section(arcs, emotions):
    if not arcs and not emotions:
        return ""
    lines = [
        "\n## 弧段记忆（Arc Memory · 长程上下文）",
        f"- 参考全文：`{ARC_MEMORY_REFERENCE}`",
        "- 这些是跨 3 章窗口之外的弧段级记忆；写本章时必须承接 carry_forward、未收线程和情绪债务。",
    ]
    for arc in arcs:
        lines.append(f"\n### {arc.get('id') or 'ARC'} · {arc.get('title') or arc.get('range')}")
        for key, label in (
            ("plot_summary", "剧情摘要"),
            ("character_changes", "人物变化"),
            ("open_threads", "未收线程"),
            ("payoffs", "已兑现"),
            ("carry_forward", "后续必须承接"),
        ):
            value = arc.get(key)
            lines.append(f"- {label}：{fmt_list(value)}")
    for item in emotions:
        lines.append("\n### 本章情绪进度")
        lines.append(f"- 主导情绪：{item.get('dominant_emotion') or '未填写'}")
        lines.append(f"- 张力分：{item.get('tension_score') if item.get('tension_score') is not None else '未填写'}")
        lines.append(f"- 读者承诺推进：{item.get('reader_promise_progress') or '未填写'}")
        lines.append(f"- 下一步情绪债务：{item.get('next_emotional_debt') or '未填写'}")
    return "\n".join(lines) + "\n"


def ledger_excerpt_for_packet(ledger, limit=2600, extract_static=False):
    """写章包注入的状态账本聚焦视图：只给长期记忆（角色 / 设定事实 / 未收与已收线程），
    丢掉逐章 `chapter_deltas` 大 blob（写下一章用不到，且几百章后会撑爆注入预算），改用计数替代。
    保证无论写到第几百章，注入的"记忆"都聚焦在 canonical 状态而非历史流水。

    新增：检测 chapter_deltas 中的 stale 标记（上游改写导致的非线性失效），
    在注入文本中追加醒目警告，提醒写作者下游章节的状态可能已过期。"""
    if not isinstance(ledger, dict):
        return json.dumps(ledger, ensure_ascii=False, indent=2)[:limit]
    # 提取 stale 章节信息后再移除 chapter_deltas
    deltas = ledger.get("chapter_deltas")
    stale_info = ""
    if isinstance(deltas, dict):
        stale_chapters = []
        for key, entry in deltas.items():
            if isinstance(entry, dict) and entry.get("stale"):
                m = re.match(r"chapter_(\d+)", key)
                if m:
                    sources = entry.get("stale_sources", [])
                    stale_chapters.append((int(m.group(1)), sources))
        if stale_chapters:
            stale_chapters.sort()
            lines = ["\n## ⚠️ 状态账本过期警告（上游改写）",
                     "> 以下章节的 state_delta 是在**上游章节改写前**合并的，其角色状态/设定事实可能已过期。",
                     "> 建议在写入本章前，先对这些章节重新跑 `reconcile_ledger --merge --verified`。"]
            for ch, sources in stale_chapters:
                src_str = "、".join(f"第{s}章" for s in sources)
                lines.append(f"- 第{ch:02d}章：因 {src_str} 改写而标记为 stale")
            stale_info = "\n".join(lines) + "\n"
    view = {k: v for k, v in ledger.items() if k != "chapter_deltas"}
    if isinstance(deltas, dict):
        view["chapter_deltas_count"] = len(deltas)
    text = json.dumps(view, ensure_ascii=False, indent=2)
    if len(text) + len(stale_info) <= limit:
        return stale_info + text
    # stale 信息优先保留，截断 JSON 部分
    return stale_info + text[:max(0, limit - len(stale_info))].rstrip() + "\n...（账本较大已截断；canonical 状态优先，逐章明细见 审稿/state_ledger.json）"


def load_revision_plan(root):
    """读 修订/revision_plan.json（revision_planner 汇流 review/score/balance/feedback/simulate）。
    缺失返回 None——修订回流是可选增强，无计划时静默不注入。"""
    path = os.path.join(root, "修订", "revision_plan.json")
    data = load_json(path, None)
    return data if isinstance(data, dict) else None


def revision_section_for_chapter(root, chapter):
    """把 revision_plan 中命中本章的修订任务注入写章包，让汇流后的修订计划真正回流到下一轮
    drafting——否则 revision_plan.json 只是个没人读的报告。无章号的全书级 P0 也提示一次。"""
    plan = load_revision_plan(root)
    if not plan:
        return ""
    tasks = [t for t in (plan.get("tasks") or []) if isinstance(t, dict)]
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    mine = sorted((t for t in tasks if t.get("chapter") == chapter),
                  key=lambda t: rank.get(t.get("priority"), 9))
    global_p0 = [t for t in tasks if t.get("chapter") is None and t.get("priority") == "P0"]
    if not mine and not global_p0:
        return ""
    lines = ["\n## 本章待处理修订项（来自 `修订/revision_plan.json`）",
             "> review/score/balance/feedback/simulate 汇流的统一修订计划——**本章重写/精修须先消化这些**："]
    for t in mine:
        reason = (t.get("reason") or "").strip()
        lines.append(
            f"- [{t.get('priority')}] {t.get('title')}"
            f"（{t.get('recommended_skill')}·{t.get('return_to_stage')}）"
            + (f" — {reason}" if reason else ""))
    if global_p0:
        lines.append(
            f"- ⚠️ 另有 {len(global_p0)} 项全书级 P0 修订（评分结论/无章号阻断），"
            "详见 `修订/修订计划.md`，安排到对应阶段处理。")
    return "\n".join(lines) + "\n"


CAST_ARC_REFERENCE = "skills/novel-craft/references/群像与角色弧光.md"


def on_stage_names(names, title, beat_text):
    """Names whose character appears in this chapter's title/outline text."""
    return [n for n in names if n and (n in title or n in beat_text)]


def current_arc_stage(stages, chapter):
    """Pick the active弧光阶段：第一个 by_chapter >= 当前章的阶段；都过了取末阶段。"""
    parsed = []
    for s in stages or []:
        try:
            by = int(s.get("by_chapter"))
        except (TypeError, ValueError):
            continue
        parsed.append((by, str(s.get("stage") or "")))
    if not parsed:
        return ""
    parsed.sort()
    for by, stage in parsed:
        if chapter <= by:
            return f"（目标 ≤第{by}章）{stage}"
    return f"（已过末阶段）{parsed[-1][1]}"


def cast_arc_section(root, chapter, title, beat_text, char_voices):
    """注入在场角色的弧光阶段（来自可选 设定/角色弧光.json）+ ≥3 人同台的群像辨识度提醒。

    无 角色弧光.json 也无 ≥3 同台时返回空串——纯增量、不强制建文件。
    """
    arc_data = load_json(os.path.join(root, "设定", "角色弧光.json"), {}) or {}
    arc_chars = arc_data.get("characters", {}) if isinstance(arc_data, dict) else {}
    on_stage_arc = on_stage_names(list(arc_chars.keys()), title, beat_text)
    on_stage_all = set(on_stage_arc) | set(on_stage_names(list(char_voices.keys()), title, beat_text))
    lines = []
    if on_stage_arc:
        lines.append("\n## 在场角色弧光（写时推进）")
        for name in on_stage_arc:
            c = arc_chars.get(name) or {}
            bits = []
            for key, label in (("function", "功能"), ("want", "want"), ("need", "need"), ("lie", "lie")):
                if c.get(key):
                    bits.append(f"{label}={c[key]}")
            lines.append(f"- **{name}**：{'；'.join(bits) if bits else '（弧光字段未填）'}")
            stage = current_arc_stage(c.get("arc_stages"), chapter)
            if stage:
                lines.append(f"  - 当前弧光阶段：{stage}")
            if c.get("distinct_tag"):
                lines.append(f"  - 辨识度锚：{c['distinct_tag']}")
        lines.append(f"- 本章至少推进其中一人的弧光：用「与过去相反的选择」兑现，别作者口头宣布（见 `{CAST_ARC_REFERENCE}`）。")
    if len(on_stage_all) >= 3:
        lines.append("\n## 群像辨识度提醒（本章 ≥3 名角色同台）")
        lines.append(f"- 同台有名角色：{'、'.join(sorted(on_stage_all))}")
        lines.append(f"- 给每人「只有他会做的反应」，别让配角沦为应声虫/背景板；功能/声音/标记三维互不撞车（见 `{CAST_ARC_REFERENCE}`）。")
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def build_packet(root, chapter, *, allow_missing_demo=False, allow_missing_reader_contract=False, step="full"):
    meta = load_json(os.path.join(root, "_meta.json"), {})
    if not meta:
        raise RuntimeError("缺少 _meta.json")
    outline = parse_outline(root)
    gate = load_demo_gate(root, allow_missing=allow_missing_demo)
    demo_waiver = None
    if allow_missing_demo and (not gate or gate.get("status") != "passed"):
        demo_waiver = make_waiver(
            "missing_demo_gate",
            reason="explicit --allow-missing-demo while generating draft packet",
            affected_gate="demo_gate",
            source="novel-craft/scripts/draft_packets.py",
            details={"chapter": chapter, "demo_gate_status": gate.get("status") if gate else None},
        )
        append_waiver(root, demo_waiver)
        record_ledger_waiver(root, demo_waiver)
    has_reader_contract = require_reader_contract(root, allow_missing=allow_missing_reader_contract)
    if allow_missing_reader_contract and not has_reader_contract:
        rc_waiver = make_waiver(
            "missing_reader_contract",
            reason="explicit --allow-missing-reader-contract while generating draft packet",
            affected_gate="reader_contract",
            source="novel-craft/scripts/draft_packets.py",
            details={"chapter": chapter},
        )
        append_waiver(root, rc_waiver)
        record_ledger_waiver(root, rc_waiver)
    ledger = ensure_state_ledger(root)
    plot_loops = load_json(os.path.join(root, "设定", "剧情环.json"), {}).get("loops", [])
    pending_loops = [L for L in plot_loops if L.get("status") in ("buried", "teasing")]
    
    char_voices = load_json(os.path.join(root, "设定", "角色语感.json"), {})
    
    words = target_words(meta)
    outline_item = outline.get(chapter, {"title": "", "beat": "（章纲未写本章条目）", "raw": ""})
    title = outline_item.get("title") or ""
    beat_text = outline_item.get("beat") or ""
    scene_matches = scene_guide_matches(outline_item)
    event_cooling_section, event_tracker = event_cooldown_section(root, chapter, beat_text)
    # 保存事件冷却追踪器（只在追踪器有实质性更新时写盘）
    if event_tracker.get("events"):
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        # 用 file_lock 保护并发写盘
        tracker_path = os.path.join(root, EVENT_COOLDOWN_PATH)
        try:
            atomic_write_json(tracker_path, event_tracker)
        except Exception:
            pass  # 冷却追踪写失败不影响主流程

    active_voices = []
    for char_name, vfp in char_voices.items():
        if char_name in title or char_name in beat_text:
            active_voices.append((char_name, vfp))
            
    voice_section = ""
    if active_voices:
        voice_section = "\n## 角色语感约束\n"
        for name, fp in active_voices:
            sp = fp.get("syntax_profile", {})
            voice_section += f"- **{name}**: 句均长 {sp.get('avg_sentence_length')} 字，短句比 {sp.get('short_sentence_ratio')}，长句比 {sp.get('long_sentence_ratio')}。词频特征: {', '.join(x['term'] for x in fp.get('lexicon_anchor', [])[:5])}\n"
    
    draft_mode = draft_mode_from_settings(root, meta)
    authorship_mode = text_authorship_mode_from_settings(root, meta)
    workflow_setting = draft_workflow_from_settings(root, meta)
    draft_workflow = workflow_setting or ("三步迭代（长篇/商业自动）" if use_trio_pipeline(root, meta) else "默认单步")
    live_check = live_check_workflow_from_settings(root, meta)
    batch_interval = batch_review_interval_from_settings(root, meta)
    
    # Workflow step adjustments
    step_note = ""
    out_file = f"章节/第{chapter:02d}章.md"
    
    # Tension & Tone logic injection
    tension_ledger_path = os.path.join(root, "设定", "tension_ledger.json")
    tension_note = ""
    if os.path.exists(tension_ledger_path):
        try:
            with open(tension_ledger_path, "r", encoding="utf-8") as f:
                tension_data = json.load(f)
                tension_note = f"\n## Tension Ledger (情绪 ROI)\n- 未解决悬念钩子 (Unresolved Hooks): {len(tension_data.get('unresolved_hooks', []))}个\n"
                for hook in tension_data.get("unresolved_hooks", [])[:3]:
                    tension_note += f"  - [{hook.get('urgency', 'normal')}] {hook.get('question')}\n"
        except Exception: pass
        
    tone_curve_path = os.path.join(root, "设定", "tone_curve.json")
    vibe_note = ""
    if os.path.exists(tone_curve_path):
        try:
            with open(tone_curve_path, "r", encoding="utf-8") as f:
                tone_data = json.load(f)
                for arc in tone_data.get("arcs", []):
                    rng = arc.get("range", "").split("-")
                    if len(rng) == 2 and int(rng[0]) <= chapter <= int(rng[1]):
                        vibe_note = f"\n## Semantic Vibe (当前 Arc: {arc.get('arc_name', '未知')})\n- Target Vibe: {arc.get('target_vibe')}\n- 请严格遵循该语境的情感基调，不要偏离。\n"
                        break
        except Exception: pass

    source_paths = source_paths_for_kind(meta.get("kind"))
    # 整部不变的圣经基底（kind 决定，跨章/跨 step 一致）——进 static_context 缓存前缀；
    # 后续按本章/本 step 追加的引用（场景卡/弧光/研究包/cast/beats/draft）会逐章变化，
    # 渲染时拆到 dynamic_context，避免污染缓存前缀（见下方 dynamic_source_paths）。
    static_source_paths = list(source_paths)
    scene_cards = scene_cards_for_chapter(root, chapter)
    if scene_cards:
        for rel in (SCENE_CARDS_REL, SCENE_CARDS_REFERENCE):
            if rel not in source_paths:
                source_paths.append(rel)
    arc_memories, emotional_progress = arc_memory_for_chapter(root, chapter)
    if arc_memories or emotional_progress:
        for rel in (ARC_SUMMARIES_REL, EMOTIONAL_PROGRESS_REL, ARC_MEMORY_REFERENCE):
            if rel not in source_paths:
                source_paths.append(rel)
    for ref in scene_guide_references(scene_matches):
        if ref not in source_paths:
            source_paths.append(ref)
    female_active = female_fiction_active(root, meta)
    if female_active and FEMALE_FICTION_REFERENCE not in source_paths:
        source_paths.append(FEMALE_FICTION_REFERENCE)
        static_source_paths.append(FEMALE_FICTION_REFERENCE)  # 题材级常量，跨章一致 → 留在静态基底
    cast_section = cast_arc_section(root, chapter, title, beat_text, char_voices)
    if cast_section and CAST_ARC_REFERENCE not in source_paths:
        source_paths.append(CAST_ARC_REFERENCE)
    research_packs = research_packs_for_chapter(root, chapter, outline_item)
    for pack in research_packs:
        rel = pack.get("pack_path")
        if rel and rel not in source_paths:
            source_paths.append(rel)
    observation_section_text, observation_refs = observation_packet_section(root, chapter)
    aesthetic_section_text, aesthetic_refs = aesthetic_bank_section(root)
    for rel in [*observation_refs, *aesthetic_refs]:
        if rel and rel not in source_paths:
            source_paths.append(rel)
    # 在分支前先算好：editor 子任务的 step_note（下方）也要引用它，否则 editor 步会
    # 触发 "cannot access local variable 'delta_path'"。
    delta_path = f"审稿/state_delta_第{chapter:02d}章.json"

    if step == "architect":
        step_note = "\n## 当前子任务：Architect Pass (剧情架构师)\n- **目标**：将骨干章纲转化为「节拍与潜台词(Beats & Subtext)」脚本。\n- **禁止**：禁止写优美的文学散文，纯干货输出。\n- **字数**：约 300-500 字。"
        words = [300, 600]
        out_file = f"写作任务/第{chapter:02d}章_beats.md"
    elif step == "ghostwriter":
        step_note = "\n## 当前子任务：Ghostwriter Pass (代笔枪手)\n- **前提**：已完成 Architect 节拍脚本。\n- **目标**：基于节拍脚本，填充环境描写、心理活动，输出流畅的初稿正文。\n- **注意**：请严格复刻文风指纹，并使用 `[CHAR_xx]`、`[PROP_xx]` 等标签标记视觉资产。"
        out_file = f"写作任务/第{chapter:02d}章_draft.md"
        source_paths.append(f"写作任务/第{chapter:02d}章_beats.md")
    elif step == "editor":
        step_note = f"""
## 当前子任务：Senior Editor Pass (主编润色)
- **前提**：已完成 Ghostwriter 初稿。
- **目标**：专门进行「五感丰富」与「去AI味」的滤网打磨（杀掉抽象词、动词升级、环境映衬）。
- **同步产出 (重要)**：除正文外，必须同时输出本章的「状态增量 JSON」(State Delta)，用于更新作品百科与伏笔账本。
- **输出**：最终交付正文写入 `章节/第{chapter:02d}章.md`；状态增量写入 `{delta_path}`。"""
        out_file = f"章节/第{chapter:02d}章.md"
        source_paths.append(f"写作任务/第{chapter:02d}章_draft.md")

    if step != "full" and step != "editor":
        pass # Out file already set above
    
    # Optional dynamic injections
    step_note += tension_note + vibe_note

    demo_anchor = gate.get("style_anchor", {}) if gate else {}
    promises = gate.get("reader_promises", []) if gate else []
    constraints = gate.get("setting_constraints", []) if gate else []
    banned = gate.get("banned_drift", []) if gate else []
    reader_contract = gate.get("reader_contract", {}) if gate else {}
    contract_path = os.path.join(root, "设定", "读者契约.md")
    contract_text = read_text(contract_path)
    contract_promises = reader_contract.get("reader_promises") or promises
    contract_banned = reader_contract.get("banned_drift") or banned
    # Demo gate bypass 降级 (P3-⑬)：当 demo gate 未通过时，gate 中 reader_contract 为空，
    # 导致所有字段显示"未填写"。此时从 读者契约.md 原文中提取关键信息的近似值作为降级默认约束，
    # 保证写作任务包至少带有基本的题旨方向，不至于在无约束状态下跑偏。
    downgraded = ""
    if (demo_waiver or not gate or not reader_contract) and contract_text:
        downgraded = "\n\n> ⚠️ **Demo gate 未通过/降级模式**：以下约束从 `设定/读者契约.md` 降级提取，" \
                     "仅作最低限度方向指引——**正式批量写章前请先通过 Demo gate**。\n"
        # 降级提取：从契约原文中抽取题旨和戏剧问题的近似行
        if not reader_contract.get("theme"):
            for line in contract_text.split("\n"):
                if "题旨" in line or "theme" in line.lower():
                    reader_contract["theme"] = line.split("：", 1)[-1].split(":", 1)[-1].strip() or reader_contract.get("theme")
                    break
        if not reader_contract.get("dramatic_question"):
            for line in contract_text.split("\n"):
                if "核心戏剧问题" in line or "dramatic_question" in line.lower():
                    reader_contract["dramatic_question"] = line.split("：", 1)[-1].split(":", 1)[-1].strip() or reader_contract.get("dramatic_question")
                    break
        if not contract_promises:
            for line in contract_text.split("\n"):
                stripped = line.strip()
                if stripped.startswith("- ") and ("承诺" in stripped or "promise" in stripped.lower() or "保证" in stripped):
                    contract_promises = list(contract_promises or []) + [stripped.lstrip("- ")]
        if not contract_banned:
            for line in contract_text.split("\n"):
                stripped = line.strip()
                if stripped.startswith("- ") and ("禁止" in stripped or "漂移" in stripped or "banned" in stripped.lower()):
                    contract_banned = list(contract_banned or []) + [stripped.lstrip("- ")]
        # 降级模式下至少填入"（降级提取）"标记以区别于正式 gate
        reader_contract.setdefault("theme", "（降级提取）")
        reader_contract.setdefault("dramatic_question", "（降级提取）")
    contract_section = f"""
## 题旨与读者契约{downgraded}
- 核心题旨：{reader_contract.get("theme") or "未填写；写前先补 `设定/读者契约.md`"}
- 核心戏剧问题：{reader_contract.get("dramatic_question") or "未填写"}
- 终局必须回答：{fmt_list(reader_contract.get("must_answer"))}
- 读者承诺：{fmt_list(contract_promises)}
- 好看机制：{fmt_list(reader_contract.get("delight_engine"))}
- 文学质感：{reader_contract.get("aesthetic_register") or "未填写"}
- 禁偏清单：{fmt_list(contract_banned)}

### `设定/读者契约.md` 摘录
{clip(contract_text, 1600) if contract_text else "（缺 `设定/读者契约.md`；至少按 reader-contract.md 模板补齐题旨、读者承诺、文学质感和禁偏清单。）"}
"""
    special_scene_sections = scene_guide_sections(scene_matches)
    scene_card_section = scene_cards_section(scene_cards)
    arc_mem_section = arc_memory_section(arc_memories, emotional_progress)
    female_section = female_fiction_section() if female_active else ""
    research_section = research_pack_section(research_packs)
    waiver_section = ""
    if demo_waiver:
        waiver_section = f"""
## 显式豁免
- {demo_waiver['id']} [{demo_waiver['type']}] {demo_waiver['reason']}
- 风险：缺少已通过 Demo gate 的文风锚点、读者承诺和禁止漂移项；本任务包只能作为准备包，不能替代正式批量写章 gate。
"""
    revision_section = revision_section_for_chapter(root, chapter)
    loop_section = ""
    if pending_loops:
        loop_section = "\n## 剧情环提醒（伏笔/钩子）\n"
        for L in pending_loops:
            loop_section += f"- **{L['title']}** ({L['id']}): {L['description']} [状态: {L['status']}, 埋于: {L.get('buried_in', '未知')}, 预计回收: {L.get('expected_recovery', '未知')}]\n"

    # 伏笔台账注入（种↔收打通）：此前写章包只注入 剧情环.json，不读 novel-wiki 权威的
    # foreshadowing_ledger.json——AI 写章时看不到"本章预期回收 SEED_003"，漏收全靠事后 scan 补救。
    # 这里注入①预期回收章落在本章 ±grace 内的 pending 伏笔（该收了）②已严重超期的伏笔（补收）。
    foreshadow_section = foreshadow_section_for_chapter(root, chapter)

    # 跨窗口语义检索（检索增强）：用本章章纲当 query，在前 3 章窗口**之外**的旧章里召回最相关的，
    # 补"固定窗口够不着久远相关旧章"的长程依赖盲区（写第230章想得起第47章埋的伏笔）。
    retrieval_section = ""
    if relevant_chapters is not None and chapter > 4:
        # query 富化：除本章章纲外，并入未收线程/伏笔环/在场角色名**及其别名**，
        # 让 BM25 能召回"久远但仍相关"的旧章（光靠章纲一行信号太弱，长程伏笔召不回）。
        # 别名扩展是离线"伪语义"：纯字面 BM25 召不回"半块断剑↔残缺剑刃"这类同义改写，
        # 但把在场角色的别称并入 query 至少能跨"本名/封号/尊称"召回同一人的旧场景。
        extra_terms = []
        for L in pending_loops[:5]:
            extra_terms.append(str(L.get("title") or ""))
            extra_terms.append(str(L.get("description") or ""))
        for ot in (ledger.get("open_threads") or [])[:8]:
            extra_terms.append(str(ot.get("thread") or ""))
        active_names = [name for name, _ in active_voices]
        extra_terms.extend(active_names)
        extra_terms.extend(alias_expansions(root, active_names))
        query = " ".join(
            str(x) for x in
            ([outline_item.get("raw") or outline_item.get("beat") or "", title] + extra_terms)
            if x and str(x).strip()
        )
        # 召回预算随书长自适应：短篇 3 章够，长篇越写越需要更宽召回和更早的窗口。
        target_ch = int(meta.get("target_chapters") or 0)
        ret_k = min(6, 3 + chapter // 150)
        ret_window = 3 if target_ch < 120 else 4
        try:
            hits = relevant_chapters(root, chapter, query, k=ret_k, window=ret_window, min_score=0.15)
        except Exception:
            hits = []
        if hits:
            retrieval_section = "\n## 相关历史回溯（跨窗口检索·写前必读）\n" \
                "> 以下旧章经词面相关度召回，可能含本章要呼应/承接的久远伏笔或设定，注意保持一致：\n"
            for h in hits:
                retrieval_section += f"- **第{h['chapter']:02d}章**（相关度 {h['score']}）：{h['excerpt'][:140]}…\n"

    concl_path = f"审稿/state_verify_第{chapter:02d}章.json"
    live_check_section = ""
    if live_check:
        live_check_section = f"""
## 边写边自检闭环（已选择）
- 本章交付不只写正文：必须同步产出 `章节/第{chapter:02d}章.md`、`{delta_path}`，以及对账结论 `{concl_path}`。
- 对账结论是你对「正文与状态增量是否一致」的自检判断，最简形如（hash 不用填，脚本会按当前正文自动盖章）：
```json
{{"chapter": {chapter}, "status": "ok", "notes": "delta 与正文一致；若有差异写明"}}
```
- 写完三样后，一条命令跑完自检并合并账本：
```bash
python3 skills/novel/scripts/post_write.py "{root}" --chapter 第{chapter:02d}章 --conclusion "{root}/{concl_path}"
```
- `post_write.py` 会跑读者契约/账本对账/百科/逻辑哨兵/力量体系/时间线自检，全过后**自动合并状态账本再标进度 ✅**——「进度✅」与「账本已合并」同生共死，不会再在 review/export 阶段报 STATE-LEDGER-MISSING。任一硬闸失败时先修正文或状态增量再重跑，不要手动标 ✅。
- 若不带 `--conclusion` 跑（不推荐），脚本只做自检不合并账本，会明确警告账本未合并，需另行合并后才能过 review/export。
"""
    batch_section = ""
    if live_check and batch_interval > 0:
        window = batch_review_window(chapter, batch_interval, meta)
        if window and window.get("due"):
            start, end = window["start"], window["end"]
            batch_json = f"审稿/batch_mechanical_第{start:02d}-{end:02d}章.json"
            batch_section = f"""
## 小批回扫修正点（第 {start:02d}-{end:02d} 章）
- 本章写后自检通过后，进入小批回扫：集中看文风、节奏、钩子、人设和读者承诺，不要只看格式机检。
- 先跑确定性机检：
```bash
python3 skills/novel-review/scripts/mechanical_check.py "{root}" --range {start}-{end} --json-out "{root}/{batch_json}"
```
- 然后让 AI/人工按 `novel-review/references/checklist.md` 审第 {start:02d}-{end:02d} 章，重点输出需集中修正的章节、问题维度和修法；修完后重跑本窗口机检。
"""
        elif window:
            batch_section = f"""
## 小批回扫节奏
- 已开启小批回扫：每 {batch_interval} 章集中跑一次 `novel-review`（文风/节奏/钩子/人设/读者承诺）。
- 当前未到回扫点；下一次预计在第 {window["next_due"]:02d} 章写后触发。
"""

    # Prompt Caching：static_context 是缓存前缀。缓存按字节前缀匹配（render 顺序 tools→system→messages），
    # 任何位置一处字节变化都会让其后所有断点失效。所以这里把「整部小说不变、且跨 architect/ghostwriter/editor
    # 三步也不变」的稳定上下文（必读源文件、基本盘、Demo 风格锚点、读者契约、女频清单）全部放进 static_context，
    # 只把逐章/逐 step 变化的内容（本章任务、章纲、承接、场景卡、研究包、账本摘录…）留在 dynamic_context。
    # 稳定块必须物理在前 + 跨章字节一致，否则缓存读取静默为 0。
    # 校验：prompt_cache_metrics.py 的 shared_static_prefix（跨包 static 块 hash 是否一致）。
    # 逐章/逐 step 追加的引用拆出来，单独放进 dynamic_context，保证 static 前缀字节一致。
    static_set = set(static_source_paths)
    dynamic_source_paths = [p for p in source_paths if p not in static_set]
    dynamic_source_section = ""
    if dynamic_source_paths:
        dynamic_source_section = "## 本章附加必读（逐章/逐 step）\n" + \
            "\n".join(f"- `{p}`" for p in dynamic_source_paths) + "\n"

    static_context = f"""<static_context cache_control="ephemeral">
## 必读源文件 (Cached)
{chr(10).join(f"- `{p}`" for p in static_source_paths)}

## 小说基本盘（整部不变）
- 小说用途：{purpose_from_settings(root, meta) or "未指定"}
- 人称视角：{meta.get("person", "未指定")}
- 目标平台：{meta.get("target_platform", "未指定")}
- 小说生成模式：{draft_mode}
- 文本主创模式：{authorship_mode or "未指定"}（人类主创=AI 只给任务/审稿/局部辅助；AI辅助=正文需人工最终取舍；AI生成=投稿/发布高风险）
- 小说生成工作流：{draft_workflow}

## Demo 风格锚点
- 来源章节：{demo_anchor.get("source_chapter", "未指定")}
- 风格要点：{demo_anchor.get("summary") or ("（降级）从 `设定/读者契约.md` 推断；正式写章前请通过 Demo gate" if contract_text else "未填写；写前先从 Demo 章抽取")}
- 读者承诺：{", ".join(promises) if promises else (", ".join(contract_promises) if contract_promises else "未填写")}
- 设定硬约束：{", ".join(constraints) if constraints else "未填写"}
- 禁止漂移：{", ".join(banned) if banned else (", ".join(contract_banned) if contract_banned else "未填写")}
{contract_section}
{female_section}
</static_context>
"""

    return static_context + f"""<dynamic_context>
# 第 {chapter:02d} 章写作任务包 ({step if step != "full" else "完整稿"})

## 本章任务
- 输出文件：`{out_file}`
- 标题：{title or "按章纲拟一个短标题"}
- 建议篇幅：{words[0]}-{words[1]} 字（仅作容量参考和质检预警，节拍闭环优先）{step_note}

{dynamic_source_section}{waiver_section}
## 本章章纲
{outline_item.get("raw") or outline_item.get("beat")}

## 上一章承接
{recent_chapters_excerpt(root, chapter)}
{revision_section}{retrieval_section}{foreshadow_section}{loop_section}{voice_section}{cast_section}
{arc_mem_section}
{scene_card_section}
{special_scene_sections}
{event_cooling_section}
{observation_section_text}
{aesthetic_section_text}
{research_section}
{live_check_section}
{batch_section}

## 当前状态账本摘录（canonical 长期记忆；逐章明细见 state_ledger.json）
```json
{ledger_excerpt_for_packet(ledger)}
```

## 写作要求
- 默认输出一章正文，第一行必须是 `# 第{chapter}章 {title or "<标题>"}`；若文本主创模式为 `人类主创`，则输出本章写作/编辑指导和关键段落建议，不直接生成可投稿正文。
- 第二行写 meta 注释：`<!-- meta: demo=false; packet=写作任务/第{chapter:02d}章.md; step={step} -->`。
- 本章必须兑现章纲里的戏剧节拍，至少保留一个钩子或承诺。
- 若章纲给本章登记了意外性设计位（预期违背），必须兑现"意料之外、情理之中"：违背读者预期线但回看伏笔成立；未登记设计位的章，至少留一处微意外（人物选择、对白潜台词或细节反第一直觉），不许整章顺撇可预测。
- 若文本主创模式为 `人类主创`，最终正文由人类作者改写和定稿，AI 只做结构、检查、局部建议和非替代性辅助。
- 本章必须推进 `读者契约` 中的至少一项：核心题旨、读者承诺、关系弧光、秘密揭示、能力代价或文学质感；不能只刷事件。
- 不新增会推翻必读设定/骨架文件的能力、关系、地点规则；新增设定必须写入章末状态增量。
- 若本章确实回答了读者契约的核心戏剧问题（解决主线核心冲突），必须把状态增量的 `core_conflict_resolved` 置 `true` 如实声明——非终局章节的该声明会被弧段 gate 硬阻断（反向刹车），瞒报则只剩关键词提醒、失去硬保护。
- 写完后填写 `{delta_path}`，再跑 `python3 skills/novel-review/scripts/mechanical_check.py "{root}"`（字数带宽会自动读取 `_meta.target_wordcount_min_max`，不要手填旧默认）；若已选择 `边写边自检`，同步填写 `{concl_path}`，继续跑 `python3 skills/novel/scripts/post_write.py "{root}" --chapter 第{chapter:02d}章 --conclusion "{root}/{concl_path}"`。

## 状态增量模板
```json
{{
  "schema_version": 1,
  "kind": "novel_state_delta",
  "chapter": {chapter},
  "chapter_file": "{out_file}",
  "new_facts": [],
  "character_changes": [],
  "relationship_changes": [],
  "open_threads_added": [],
  "threads_resolved": [],
  "reader_contract_progress": [],
  "theme_alignment": "",
  "core_conflict_resolved": false,
  "setting_constraints_added": [],
  "next_chapter_carry": []
}}
```
> **character_changes 生死/退场必带 `event` 枚举**（death/exit/revival），例：
> `{{"name":"王五","event":"death","change":"力战而亡"}}`。这是确定性生死闸(阻断级)的唯一输入——
> 只写自由文本 change 不带 event，「已死角色后文再动作」的硬矛盾抓不住。复活桥段补 `event:"revival"` 解闸。
</dynamic_context>
"""


def resolve_chapters(args, root):
    if args.chapter:
        return [args.chapter]
    if args.range:
        m = re.fullmatch(r"(\d+)-(\d+)", args.range)
        if not m:
            raise RuntimeError("--range 格式应为 4-8")
        start, end = int(m.group(1)), int(m.group(2))
        if end < start:
            raise RuntimeError("--range 结束章不能小于开始章")
        return list(range(start, end + 1))
    meta = load_json(os.path.join(root, "_meta.json"), {})
    target = int(meta.get("target_chapters") or 0)
    done = existing_chapters(root)
    start = 1
    demo_count = int(meta.get("demo_chapters") or 0)
    if args.next and demo_count:
        start = demo_count + 1
    for chapter in range(start, target + 1):
        if chapter not in done:
            return [chapter]
    raise RuntimeError("未找到待写章节；可用 --chapter 指定。")


def main():
    ap = argparse.ArgumentParser(description="生成 novel 批量写章任务包")
    ap.add_argument("project_root")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--chapter", type=int)
    group.add_argument("--range", dest="range", default=None, help="例如 4-8")
    group.add_argument("--next", action="store_true", help="按 _meta/demo_chapters 和现有章节找下一章")
    ap.add_argument("--out-dir", default=None, help="缺省 <作品根>/写作任务")
    ap.add_argument("--stdout", action="store_true", help="只打印，不写文件")
    ap.add_argument("--allow-missing-demo", action="store_true", help="Demo gate 未通过时也允许生成准备包")
    ap.add_argument("--allow-missing-reader-contract", action="store_true",
                    help="设定/读者契约.md 缺失时也允许生成任务包（记 waiver）")
    ap.add_argument(
        "--step",
        default="auto",
        choices=["auto", "full", "trio", "architect", "ghostwriter", "editor"],
        help="工作流步骤；auto 会让 长篇/商业连载/漫剧源书/三步迭代 默认生成 trio 三段任务包",
    )
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    try:
        chapters = resolve_chapters(args, root)
        steps = packet_steps_for_request(root, args.step)
        packets = [
            (chapter, step, build_packet(root, chapter, allow_missing_demo=args.allow_missing_demo,
                                         allow_missing_reader_contract=args.allow_missing_reader_contract, step=step))
            for chapter in chapters
            for step in steps
        ]
    except Exception as e:
        print(f"[err] {e}", file=sys.stderr)
        sys.exit(2)

    if args.stdout:
        for idx, (chapter, step, packet) in enumerate(packets):
            if idx:
                print("\n\n" + "=" * 60 + "\n")
            print(packet)
        return

    out_dir = os.path.abspath(args.out_dir or os.path.join(root, "写作任务"))
    os.makedirs(out_dir, exist_ok=True)
    wrote_steps = []
    for chapter, step, packet in packets:
        suffix = f"_{step}" if step != "full" else ""
        path = os.path.join(out_dir, f"第{chapter:02d}章{suffix}.md")
        atomic_write_text(path, packet)
        wrote_steps.append(step)
        print(f"[ok] 写作任务包：{path}")
    if any(step in TRIO_STEPS for step in wrote_steps):
        print("[next] 三步迭代顺序：先按 _architect 产 beats，再按 _ghostwriter 产 draft，最后按 _editor 写入 章节/第NN章.md；完成后填写 state_delta 并跑 novel-review。")
    else:
        print("[next] 按任务包写入 章节/第NN章.md，填写 审稿/state_delta_第NN章.json，再跑 novel-review 机检/人判。")
    meta = load_json(os.path.join(root, "_meta.json"), {})
    if live_check_workflow_from_settings(root, meta):
        print("[next] 已选择 边写边自检：每章正文和 state_delta 落盘后，立刻跑 novel/scripts/post_write.py 自动过账本/百科/逻辑/力量体系自检。")
        interval = batch_review_interval_from_settings(root, meta)
        if interval > 0:
            print(f"[next] 小批回扫保留：每 {interval} 章跑一次 novel-review，集中修文风/节奏/钩子/人设/读者承诺。")


if __name__ == "__main__":
    main()
