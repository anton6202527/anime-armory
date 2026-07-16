#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Professional research packet scaffolding, checks, and refresh audits.

The script does not browse the web. Agents collect evidence with realtime
search or user-provided sources, then store it here for deterministic reuse.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
INDEX_KIND = "novel_research_sources"
REPORT_KIND = "novel_research_fact_support"
REFRESH_PLAN_KIND = "novel_research_refresh_audit"
NEEDS_KIND = "novel_research_needs"
RESEARCH_JOBS_KIND = "novel_research_jobs"
RESEARCH_SCENE_USAGE_KIND = "novel_research_scene_usage"

SOURCE_EVALUATION_AXES = ("currency", "relevance", "authority", "accuracy", "purpose")

DEFAULT_FRESHNESS_DAYS = 90
# 按领域分档有效期（天）：把 SKILL.md 早已承诺却没落地的「平台/法律/医疗短、历史/文化长」写进代码。
# 平台规则最易变（当日就可能改），历史近乎静态。未列领域回退 DEFAULT_FRESHNESS_DAYS。
# 仅当资料包**没有显式** freshness_days 时生效；作者手填的 --freshness-days 永远优先。
DOMAIN_FRESHNESS_DEFAULTS = {
    "platform": 30,
    "legal": 90, "finance": 90, "medical": 120, "technology": 120,
    "military": 180, "career": 180, "crime": 365, "overseas": 365,
    "religion": 730, "history": 1825,
}


def domain_freshness_default(domain: str | None) -> int:
    return DOMAIN_FRESHNESS_DEFAULTS.get(str(domain or "").strip().lower(), DEFAULT_FRESHNESS_DAYS)

HIGH_RISK_DOMAINS = {
    "medical",
    "legal",
    "crime",
    "finance",
    "military",
    "history",
    "religion",
    "overseas",
    "technology",
    "career",
    "platform",
}

# 每个高风险领域的**必备子主题清单**：一个 ready 资料包不该只"有来源有 claim"，还要覆盖
# 该领域写专业场景绕不开的核心子面。coverage 用 claim 文本关键词命中判定（启发式·只出建议级，
# 不硬阻断——按 B10，关键词命中不做 BLOCK）。子主题的意义是把"结构齐全"升级为"深度够"：
# 例如医疗急救场景，缺"给药/剂量/禁忌/法律边界"任一子面，也照样能 status=ready，正文就容易外行。
# 每个子主题 = (子面名, 命中关键词元组)。命中任一关键词即视为该子面已覆盖。
DOMAIN_REQUIRED_SUBTOPICS = {
    "medical": (
        ("诊断/病理", ("诊断", "病理", "症状", "体征", "鉴别")),
        ("用药/剂量", ("用药", "剂量", "给药", "药物", "禁忌", "配伍")),
        ("操作/流程", ("手术", "操作", "流程", "急救", "抢救", "护理")),
        ("法律/伦理边界", ("知情同意", "法律", "伦理", "责任", "边界", "规范")),
    ),
    "legal": (
        ("实体法/罪名要件", ("构成要件", "罪名", "责任", "权利", "义务", "实体")),
        ("程序/流程", ("程序", "流程", "立案", "开庭", "举证", "上诉", "时效")),
        ("证据规则", ("证据", "举证责任", "证明标准", "非法证据", "质证")),
        ("管辖/文书", ("管辖", "文书", "判决", "裁定", "送达", "格式")),
    ),
    "crime": (
        ("现场/物证", ("现场勘查", "物证", "痕迹", "指纹", "DNA", "提取")),
        ("法医/尸检", ("法医", "尸检", "死亡时间", "死因", "损伤")),
        ("侦查/审讯", ("侦查", "审讯", "口供", "讯问", "同步录音录像")),
        ("程序/证据链", ("立案", "证据链", "证据规则", "羁押", "强制措施")),
    ),
    "finance": (
        ("产品/工具", ("股票", "债券", "基金", "期货", "外汇", "衍生品")),
        ("交易/规则", ("交易", "结算", "涨跌停", "做市", "撮合", "T+")),
        ("监管/合规", ("监管", "合规", "内幕", "披露", "反洗钱", "牌照")),
        ("风控/估值", ("风控", "估值", "杠杆", "对冲", "尽调", "审计")),
    ),
    "military": (
        ("编制/军衔", ("编制", "军衔", "建制", "番号", "序列")),
        ("战术/条令", ("战术", "条令", "作战", "队形", "协同")),
        ("装备/弹药", ("装备", "武器", "弹药", "口径", "射程", "制式")),
        ("后勤/指挥", ("后勤", "指挥", "通信", "情报", "保障")),
    ),
    "history": (
        ("制度/官制", ("制度", "官制", "科举", "职官", "品级")),
        ("纪年/称谓", ("年号", "纪年", "谥号", "称谓", "避讳")),
        ("器物/礼法", ("器物", "服饰", "礼法", "度量", "饮食")),
        ("史料依据", ("史料", "考据", "出处", "文献", "记载")),
    ),
    "religion": (
        ("教义/经典", ("教义", "经典", "经文", "戒律", "教理")),
        ("仪轨/节庆", ("仪轨", "法会", "礼拜", "节庆", "斋")),
        ("组织/神职", ("神职", "教阶", "寺庙", "教会", "僧团")),
        ("禁忌/边界", ("禁忌", "亵渎", "边界", "尊重", "敏感")),
    ),
    "overseas": (
        ("身份/签证", ("签证", "身份", "移民", "居留", "工卡")),
        ("法律辖区", ("辖区", "法律", "版权", "合规", "管辖")),
        ("文化/风俗", ("文化", "风俗", "禁忌", "本地化", "习惯")),
        ("生活/流程", ("流程", "手续", "税务", "银行", "医疗", "租房")),
    ),
    "technology": (
        ("原理/约束", ("原理", "算法", "架构", "约束", "限制")),
        ("术语/规范", ("术语", "协议", "规范", "标准", "接口")),
        ("流程/工程", ("流程", "工程", "部署", "测试", "运维")),
        ("边界/风险", ("漏洞", "安全", "风险", "边界", "失效")),
    ),
    "career": (
        ("岗位/职责", ("岗位", "职责", "分工", "角色", "职级")),
        ("流程/规范", ("流程", "规范", "标准", "作业", "SOP")),
        ("黑话/日常", ("术语", "黑话", "行话", "日常", "工具")),
        ("红线/合规", ("红线", "合规", "禁忌", "责任", "边界")),
    ),
    "platform": (
        ("题材/尺度", ("题材", "尺度", "红线", "敏感", "限流")),
        ("审核/备案", ("审核", "备案", "许可证", "上线", "报审")),
        ("合规/披露", ("合规", "披露", "AI标识", "实名", "未成年")),
        ("发行/辖区", ("发行", "辖区", "版权", "分成", "结算")),
    ),
}

# 外行雷区：领域内**高频术语混用/常识性硬伤**的关键词信号。命中只出建议级候选（B10 启发式·
# 需人工核实是否真错——有语境下可能合理），意义是把"最常见的外行破绽"前置到写作/审稿视野。
# 每项 = (触发词或共现词组, 为什么疑似外行 + 正确说法)。co 元组表示"同章共现才触发"。
DOMAIN_PITFALLS = {
    "medical": [
        ("消炎药", "口语‘消炎药’常被误用为抗生素；抗生素抗的是细菌感染，非抗炎；病毒/无菌炎症用抗生素是外行硬伤"),
        (("青霉素", "直接注射"), "青霉素类给药前需皮试，‘直接注射’易露怯"),
        ("葡萄糖", "低血糖才补糖；对疑似糖尿病/未知患者盲目静推葡萄糖是外行"),
    ],
    "legal": [
        (("民事", "逮捕"), "逮捕是刑事强制措施；民事纠纷不存在‘逮捕’，应为查封/拘传/司法拘留"),
        (("死缓", "立即执行"), "死缓=死刑缓期二年执行，与‘立即执行’自相矛盾"),
        ("画押", "现代诉讼是签名捺印，非古代‘画押’；除非历史/古代背景"),
    ],
    "crime": [
        (("测谎", "定罪"), "测谎结论在多数法域不能作为定罪证据，只作侦查参考"),
        (("尸斑", "死亡时间"), "尸斑/尸僵只能大致推断死亡时间，写成精确到分钟是外行"),
    ],
    "finance": [
        (("涨停", "继续买入成交"), "A股涨停后封单排队，未必能继续成交买入"),
        ("T+0", "A股股票是 T+1，随口 T+0 交易需确认标的（仅部分品种/市场）"),
    ],
    "military": [
        ("拉栓上膛", "多数自动武器是拉套筒/拉机柄上膛，‘拉栓’仅限栓动步枪"),
        (("将军", "连长"), "军衔与职务混用（将军是军衔，连长是职务），层级错配易露怯"),
    ],
    "history": [
        ("辣椒", "辣椒明代才传入中国；写唐宋人吃辣是时代错位"),
        ("土豆", "土豆/玉米/红薯为明代传入；上古中古背景出现是常见穿帮"),
        ("陛下", "‘陛下’称皇帝；对王侯/未称帝者用‘陛下’是称谓错位"),
    ],
    "religion": [
        (("僧人", "吃肉"), "汉传佛教僧人持素戒荤；僧人日常大口吃肉需特定语境（破戒/济公式），否则外行"),
        (("道士", "化缘"), "‘化缘’是佛教僧人乞食用语；道士称‘募化/募捐’，混用露怯"),
        (("清真", "猪"), "清真饮食禁猪；穆斯林角色吃猪肉、清真馆上猪肉是宗教常识硬伤"),
        (("罗马教皇", "东正教"), "东正教不承认罗马教皇权威；把教皇安到东正教是混淆天主教/东正教"),
    ],
    "overseas": [
        (("美国", "身份证"), "美国无全国统一身份证，通用证件是驾照/SSN/护照；‘出示身份证’是中式错位"),
        (("英国", "总统"), "英国君主立宪+首相制，无‘总统’；国家元首是君主、政府首脑是首相"),
        (("日本", "农历"), "日本明治后过公历元旦、不过农历春节（除非在日华人语境）；节庆错位常见"),
    ],
    "technology": [
        (("量子", "瞬间通信"), "量子纠缠不能超光速传信息（无通信定理）；‘量子瞬时通讯’是伪科学"),
        (("黑客", "秒破"), "口令/加密暴力破解需算力与时间，影视式‘敲几下键盘即破’是外行"),
        (("IP", "门牌"), "公网 IP 只能定位到运营商/城市级；精确到门牌需运营商配合，非随手可查"),
    ],
    "career": [
        (("上市公司", "一个人说了算"), "上市公司重大事项须董事会/股东会决议；一人独断不合规且易被监管否决"),
        (("试用期", "不签合同"), "用工即须订立劳动合同、缴社保，试用期也不例外；‘试用期不签合同’违法"),
        (("年终奖", "离职就没"), "年终奖归属看合同/制度约定，非‘一离职必然作废’；一刀切写法失真"),
    ],
    "platform": [
        (("独家", "多平台同步"), "签约独家文不能多平台同步首发；‘各大平台同步上架’与独家条款直接冲突"),
        (("上架", "全免费"), "签约上架章节通常转付费/分成；写成‘上架后全部免费看到底’与平台商业模式冲突"),
    ],
}

DOMAIN_KEYWORDS = {
    "medical": ("医疗", "医院", "医生", "手术", "抢救", "急诊", "药物", "用药", "诊断", "病历", "护士", "ICU", "麻醉"),
    "legal": ("法律", "律师", "法院", "法庭", "诉讼", "合同", "判决", "检察", "证据规则", "刑法", "民法"),
    "crime": ("刑侦", "侦查", "法医", "尸检", "案发", "审讯", "口供", "指纹", "DNA", "监控", "现场勘查"),
    "finance": ("金融", "股票", "基金", "债券", "投行", "并购", "财报", "审计", "期货", "外汇", "风控"),
    "military": ("军事", "军队", "战术", "武器", "弹药", "舰队", "作战", "军衔", "后勤", "情报"),
    "history": ("历史", "朝代", "年号", "制度", "科举", "官制", "礼法", "史料", "考据"),
    "religion": ("宗教", "佛教", "道教", "基督教", "伊斯兰", "神职", "教义", "寺庙", "教会"),
    "overseas": ("海外", "出海", "移民", "签证", "美国", "日本", "东南亚", "跨境", "本地化", "版权辖区"),
    "technology": ("科技", "算法", "芯片", "AI", "人工智能", "网络安全", "黑客", "数据库", "机器人", "工程"),
    "career": ("职场", "行业", "公司", "职业", "流程", "岗位", "医生", "律师", "警察", "记者", "导演", "科研"),
    "platform": ("投稿", "平台", "审核", "备案", "合规", "短剧", "漫剧", "商业连载", "出海", "发行"),
}

COMMERCIAL_SIGNALS = (
    "商业连载",
    "平台投稿",
    "投稿",
    "出海",
    "本地化",
    "改编",
    "漫剧",
    "短剧",
    "红果",
    "番茄",
    "抖音",
    "KDP",
)

DOMAIN_ALIASES = {
    "医学": "medical",
    "医疗": "medical",
    "医院": "medical",
    "法律": "legal",
    "法务": "legal",
    "刑侦": "crime",
    "刑事": "crime",
    "犯罪": "crime",
    "金融": "finance",
    "财经": "finance",
    "军事": "military",
    "军警": "military",
    "历史": "history",
    "考据": "history",
    "宗教": "religion",
    "海外": "overseas",
    "出海": "overseas",
    "本地化": "overseas",
    "科技": "technology",
    "技术": "technology",
    "AI": "technology",
    "人工智能": "technology",
    "职业": "career",
    "行业": "career",
    "平台": "platform",
    "商业": "platform",
    "投稿": "platform",
}

REQUIRED_DOMAIN_KEYS = (
    "research_required_domains",
    "required_research_domains",
    "professional_domains",
    "required_professional_domains",
    "必须专业核验领域",
    "专业资料包必需领域",
)


def today() -> str:
    return date.today().isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def slugify(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "untitled"
    normalized = re.sub(r"[\\/:*?\"<>|\s]+", "_", text)
    normalized = normalized.strip("._")
    return normalized[:80] or "untitled"


def index_path(root: Path) -> Path:
    return root / "资料" / "research_sources.json"


def report_path(root: Path) -> Path:
    return root / "审稿" / "research_fact_support.json"


def refresh_plan_path(root: Path) -> Path:
    return root / "资料" / "research_refresh_plan.md"


def needs_json_path(root: Path) -> Path:
    return root / "资料" / "research_needs.json"


def needs_md_path(root: Path) -> Path:
    return root / "资料" / "research_needs.md"


def jobs_json_path(root: Path) -> Path:
    return root / "资料" / "research_jobs.json"


def jobs_md_path(root: Path) -> Path:
    return root / "资料" / "research_jobs.md"


def scene_usage_json_path(root: Path) -> Path:
    return root / "资料" / "research_scene_usage.json"


def scene_usage_md_path(root: Path) -> Path:
    return root / "资料" / "research_scene_usage.md"


def load_index(root: Path) -> dict[str, Any]:
    payload = load_json(index_path(root), None)
    if isinstance(payload, dict):
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload.setdefault("kind", INDEX_KIND)
        payload.setdefault("packs", [])
        return payload
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": INDEX_KIND,
        "updated_at": today(),
        "packs": [],
    }


def parse_chapters(value: str | None) -> list[Any]:
    if not value:
        return []
    text = str(value).strip()
    if not text:
        return []
    if text.lower() == "all" or text == "全书":
        return ["all"]
    out: list[Any] = []
    for part in re.split(r"[,，、\s]+", text):
        if not part:
            continue
        m = re.match(r"^0*(\d+)\s*[-~至]\s*0*(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start > end:
                start, end = end, start
            out.append(f"{start}-{end}")
            continue
        if part.isdigit():
            out.append(int(part))
        else:
            out.append(part)
    return out


def chapter_applies(spec: Any, chapter: int | None) -> bool:
    if chapter is None:
        return True
    if spec in (None, "", []):
        return False
    if isinstance(spec, str):
        specs = [spec]
    else:
        specs = spec if isinstance(spec, list) else [spec]
    for item in specs:
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


def parse_source_evaluation(raw: str, *, source_type: str, reliability: str, has_date: bool) -> dict[str, str]:
    evaluation = {
        "currency": "date_recorded" if has_date else "missing_date",
        "relevance": "direct_topic",
        "authority": "high_authority" if reliability == "high" or source_type in {"official", "regulation", "law", "paper", "academic", "textbook"} else ("low_authority" if reliability == "low" else "medium_authority"),
        "accuracy": "source_bound_claims",
        "purpose": "informational" if source_type in {"official", "regulation", "law", "paper", "academic", "textbook"} else "purpose_checked",
    }
    text = str(raw or "").strip()
    if not text:
        return evaluation
    for part in re.split(r"[;；]", text):
        if not part.strip():
            continue
        if "=" in part:
            key, value = part.split("=", 1)
        elif "：" in part:
            key, value = part.split("：", 1)
        elif ":" in part:
            key, value = part.split(":", 1)
        else:
            continue
        key = key.strip().lower()
        if key in SOURCE_EVALUATION_AXES:
            evaluation[key] = value.strip()
    return evaluation


def parse_source(spec: str, idx: int) -> dict[str, Any]:
    parts = [p.strip() for p in spec.split("|")]
    while len(parts) < 7:
        parts.append("")
    title, published_date, source_type, reliability, url, notes, evaluation_spec = parts[:7]
    source_type = source_type or "other"
    reliability = reliability or "medium"
    return {
        "id": f"SRC-{idx:03d}",
        "title": title,
        "url": url,
        "source_type": source_type,
        "published_date": published_date,
        "accessed_date": today(),
        "reliability": reliability,
        "notes": notes,
        "evaluation": parse_source_evaluation(
            evaluation_spec,
            source_type=source_type,
            reliability=reliability,
            has_date=bool(published_date),
        ),
    }


def parse_claim(spec: str, idx: int) -> dict[str, Any]:
    parts = [p.strip() for p in spec.split("|")]
    while len(parts) < 7:
        parts.append("")
    claim, source_ids, confidence, chapters, usage, uncertainty, forbidden_use = parts[:7]
    ids = [p.strip() for p in re.split(r"[,，、\s]+", source_ids) if p.strip()]
    return {
        "id": f"FACT-{idx:03d}",
        "claim": claim,
        "source_ids": ids,
        "confidence": confidence or "medium",
        "applicable_chapters": parse_chapters(chapters),
        "usage": usage,
        "uncertainty": uncertainty,
        "forbidden_use": forbidden_use,
    }


def pack_by_slug(index: dict[str, Any], slug: str) -> dict[str, Any] | None:
    for pack in index.get("packs", []):
        if pack.get("topic_slug") == slug:
            return pack
    return None


def render_markdown(pack: dict[str, Any]) -> str:
    lines = [
        f"# 专业资料包：{pack.get('topic') or pack.get('topic_slug')}",
        "",
        f"- 领域：{pack.get('domain', 'other')}",
        f"- 风险级别：{pack.get('risk_level', 'medium')}",
        f"- 状态：{pack.get('status', 'draft')}",
        f"- 适用章节：{fmt_chapters(pack.get('applicable_chapters'))}",
        f"- 更新日期：{pack.get('updated_at', today())}",
        f"- 有效期：{pack.get('freshness_days', 90)} 天",
        "",
        "## 写作使用边界",
        "",
        "- 只能把“证据支持事实”里的内容写成确定事实。",
        "- “不确定项”只能写成角色视角的疑问、误判或待核验，不得由旁白盖棺定论。",
        "- “禁用项”不得写成行业真相，可作为反派错误操作、谣言或影视化夸张并明确纠正。",
        "",
        "## 来源",
        "",
        "| id | 标题 | 类型 | 日期 | 访问日期 | 可信度 | URL/出处 |",
        "|---|---|---|---|---|---|---|",
    ]
    for src in pack.get("sources", []):
        lines.append(
            f"| {src.get('id','')} | {src.get('title','')} | {src.get('source_type','')} | "
            f"{src.get('published_date','')} | {src.get('accessed_date','')} | "
            f"{src.get('reliability','')} | {src.get('url','')} |"
        )
    if not pack.get("sources"):
        lines.append("| TODO | 待补来源 |  |  |  |  |  |")
    lines.extend([
        "",
        "## 来源五轴评估",
        "",
        "| id | 时效 currency | 相关 relevance | 权威 authority | 准确 accuracy | 目的 purpose |",
        "|---|---|---|---|---|---|",
    ])
    for src in pack.get("sources", []):
        evaluation = src.get("evaluation") if isinstance(src.get("evaluation"), dict) else {}
        lines.append(
            f"| {src.get('id','')} | {evaluation.get('currency','未评估')} | "
            f"{evaluation.get('relevance','未评估')} | {evaluation.get('authority','未评估')} | "
            f"{evaluation.get('accuracy','未评估')} | {evaluation.get('purpose','未评估')} |"
        )
    if not pack.get("sources"):
        lines.append("| TODO | 待补来源评估 |  |  |  |  |")
    lines.extend([
        "",
        "## 证据支持事实",
        "",
        "| id | 事实 | 来源 | 可信度 | 适用章节 | 使用方式 | 不确定项 | 禁用写法 |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for claim in pack.get("claims", []):
        lines.append(
            f"| {claim.get('id','')} | {claim.get('claim','')} | {','.join(claim.get('source_ids') or [])} | "
            f"{claim.get('confidence','')} | {fmt_chapters(claim.get('applicable_chapters'))} | "
            f"{claim.get('usage','')} | {claim.get('uncertainty','')} | {claim.get('forbidden_use','')} |"
        )
    if not pack.get("claims"):
        lines.append("| TODO | 待补事实 |  |  |  |  |  |  |")
    lines.extend(["", "## 不确定项", ""])
    for item in pack.get("uncertain_items") or []:
        lines.append(f"- {item}")
    if not pack.get("uncertain_items"):
        lines.append("- （暂无；遇到证据冲突或无法确认时写这里）")
    lines.extend(["", "## 禁用项", ""])
    for item in pack.get("forbidden_items") or []:
        lines.append(f"- {item}")
    if not pack.get("forbidden_items"):
        lines.append("- （暂无；行业误区、影视夸张、平台/法规风险写这里）")
    return "\n".join(lines) + "\n"


def fmt_chapters(value: Any) -> str:
    if value in (None, "", []):
        return "未填写"
    if isinstance(value, list):
        return "、".join(str(v) for v in value)
    return str(value)


def scaffold(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    root = Path(root)
    index = load_index(root)
    slug = slugify(args.topic)
    existing = pack_by_slug(index, slug)
    sources = [parse_source(spec, i + 1) for i, spec in enumerate(args.source or [])]
    claims = [parse_claim(spec, i + 1) for i, spec in enumerate(args.claim or [])]
    status = args.status or ("ready" if sources and claims else "draft")
    pack_path = f"资料/专业资料包_{slug}.md"
    pack = existing or {}
    pack.update({
        "topic": args.topic,
        "topic_slug": slug,
        "domain": args.domain,
        "risk_level": args.risk,
        "status": status,
        "pack_path": pack_path,
        "applicable_chapters": parse_chapters(args.chapters) or ["all"],
        "keywords": args.keyword or [],
        "freshness_days": args.freshness_days if args.freshness_days is not None else domain_freshness_default(args.domain),
        "updated_at": today(),
        "sources": sources or pack.get("sources", []),
        "claims": claims or pack.get("claims", []),
        "uncertain_items": args.uncertain or pack.get("uncertain_items", []),
        "forbidden_items": args.forbidden or pack.get("forbidden_items", []),
    })
    if existing is None:
        index["packs"].append(pack)
    index["updated_at"] = today()
    write_json(index_path(root), index)
    write_text(root / pack_path, render_markdown(pack))
    return {"pack_path": str(root / pack_path), "index_path": str(index_path(root)), "status": status}


def read_project_text(root: Path) -> str:
    paths = [
        root / "_meta.json",
        root / "_设置.md",
        root / "设定" / "章纲.md",
        root / "设定" / "创作蓝图.md",
    ]
    chunks = []
    for path in paths:
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def read_chapter_text(root: Path, chapter: int | None) -> str:
    cdir = root / "章节"
    if not cdir.is_dir():
        return ""
    if chapter is None:
        chunks = []
        for path in sorted(cdir.glob("*.md")):
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        return "\n".join(chunks)
    patterns = [f"第{chapter:02d}章", f"第{chapter}章"]
    for path in sorted(cdir.glob("*.md")):
        if any(p in path.name for p in patterns):
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def detect_domains(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        hits = [kw for kw in keywords if kw and kw in text]
        if hits:
            found[domain] = hits
    return found


def commercial_signal(text: str) -> list[str]:
    return [kw for kw in COMMERCIAL_SIGNALS if kw in text]


def normalize_domain(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text in HIGH_RISK_DOMAINS:
        return text
    if text.lower() in HIGH_RISK_DOMAINS:
        return text.lower()
    return DOMAIN_ALIASES.get(text) or DOMAIN_ALIASES.get(text.upper()) or text.lower()


def parse_domain_list(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    raw: list[Any]
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,，、;\s]+", str(value))
    out: list[str] = []
    for item in raw:
        domain = normalize_domain(str(item))
        if domain and domain not in out:
            out.append(domain)
    return out


def read_required_domains(root: Path) -> list[str]:
    domains: list[str] = []
    meta = load_json(root / "_meta.json", {}) or {}
    if isinstance(meta, dict):
        for key in REQUIRED_DOMAIN_KEYS:
            for item in parse_domain_list(meta.get(key)):
                if item not in domains:
                    domains.append(item)
    req = load_json(root / "资料" / "research_requirements.json", {}) or {}
    if isinstance(req, dict):
        for key in ("required_domains", "domains", "professional_domains"):
            for item in parse_domain_list(req.get(key)):
                if item not in domains:
                    domains.append(item)
    settings_path = root / "_设置.md"
    if settings_path.exists():
        text = settings_path.read_text(encoding="utf-8", errors="replace")
        for key in REQUIRED_DOMAIN_KEYS:
            pattern = re.compile(rf"{re.escape(key)}\s*[:：]\s*([^\n]+)")
            for match in pattern.finditer(text):
                for item in parse_domain_list(match.group(1)):
                    if item not in domains:
                        domains.append(item)
    return domains


def pack_matches_domain(pack: dict[str, Any], domain: str, chapter: int | None, text: str) -> bool:
    if pack.get("domain") == domain and chapter_applies(pack.get("applicable_chapters"), chapter):
        return True
    keywords = pack.get("keywords") or []
    if keywords and any(str(kw) in text for kw in keywords):
        return chapter_applies(pack.get("applicable_chapters"), chapter)
    return False


def relevant_packs(index: dict[str, Any], chapter: int | None, text: str = "") -> list[dict[str, Any]]:
    packs = []
    for pack in index.get("packs", []):
        if chapter_applies(pack.get("applicable_chapters"), chapter):
            packs.append(pack)
            continue
        keywords = pack.get("keywords") or []
        if text and keywords and any(str(kw) in text for kw in keywords):
            packs.append(pack)
    return packs


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def pack_is_high_risk(pack: dict[str, Any]) -> bool:
    risk = str(pack.get("risk_level") or "").strip().lower()
    return risk in {"high", "高", "高风险"} or pack.get("domain") in HIGH_RISK_DOMAINS


def pack_freshness(pack: dict[str, Any]) -> dict[str, Any]:
    # 显式 freshness_days 优先；缺失/None → 按领域分档默认（平台短、历史长），而非一刀切 90。
    freshness_days = safe_int(pack.get("freshness_days"), domain_freshness_default(pack.get("domain")))
    raw_updated_at = str(pack.get("updated_at") or "").strip()
    updated_at = parse_date(raw_updated_at)
    if not updated_at:
        return {
            "updated_at": raw_updated_at,
            "freshness_days": freshness_days,
            "age_days": None,
            "days_remaining": None,
            "stale": True,
            "reason": "missing_updated_at",
        }
    age_days = (date.today() - updated_at).days
    return {
        "updated_at": updated_at.isoformat(),
        "freshness_days": freshness_days,
        "age_days": age_days,
        "days_remaining": freshness_days - age_days,
        "stale": age_days > freshness_days,
        "reason": "expired" if age_days > freshness_days else "fresh",
    }


def finding(severity: str, typ: str, message: str, *, pack: str = "", domain: str = "", evidence: str = "") -> dict[str, Any]:
    return {
        "severity": severity,
        "type": typ,
        "message": message,
        "pack": pack,
        "domain": domain,
        "evidence": evidence,
    }


def pack_depth_gaps(pack: dict[str, Any]) -> list[str]:
    """返回该资料包在其领域必备子主题里**未覆盖**的子面名列表（启发式关键词命中）。

    coverage 语料 = 所有 claim 文本 + usage + uncertainty + pack topic/domain。领域无必备
    子主题清单（如非高风险自定义领域）返回空。用于把"结构齐全"升级为"深度够"。"""
    domain = str(pack.get("domain") or "").strip().lower()
    required = DOMAIN_REQUIRED_SUBTOPICS.get(domain)
    if not required:
        return []
    corpus_parts = [str(pack.get("topic") or ""), domain]
    for claim in pack.get("claims") or []:
        corpus_parts.append(str(claim.get("claim") or ""))
        corpus_parts.append(str(claim.get("usage") or ""))
        corpus_parts.append(str(claim.get("uncertainty") or ""))
    corpus = " ".join(corpus_parts)
    gaps = []
    for name, keywords in required:
        if not any(kw in corpus for kw in keywords):
            gaps.append(name)
    return gaps


def validate_pack(root: Path, pack: dict[str, Any], chapter: int | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    topic = pack.get("topic") or pack.get("topic_slug") or "unknown"
    status = pack.get("status") or "draft"
    high_risk = pack_is_high_risk(pack)
    if chapter is not None and not chapter_applies(pack.get("applicable_chapters"), chapter):
        return out
    if status != "ready":
        sev = "阻断级" if high_risk else "建议级"
        out.append(finding(sev, "pack_not_ready", f"资料包 {topic} 不是 ready：status={status}", pack=topic))
    rel = pack.get("pack_path")
    if rel and not (root / rel).exists():
        out.append(finding("阻断级", "pack_file_missing", f"资料包文件不存在：{rel}", pack=topic))
    sources = pack.get("sources") or []
    claims = pack.get("claims") or []
    if not sources:
        out.append(finding("阻断级" if high_risk else "建议级", "no_sources", f"资料包 {topic} 缺来源", pack=topic))
    if not claims:
        out.append(finding("阻断级" if high_risk else "建议级", "no_claims", f"资料包 {topic} 缺可写事实 claims", pack=topic))
    # 专业深度分级：ready 包若在其领域必备子主题上有缺口，出建议级提醒（关键词启发式·不硬阻断）。
    # 这把"有来源有 claim"升级为"覆盖了该领域绕不开的核心子面"，防外行硬伤在写作前就补齐。
    if claims:
        gaps = pack_depth_gaps(pack)
        if gaps:
            out.append(finding(
                "建议级", "pack_depth_insufficient",
                f"资料包 {topic}（{pack.get('domain')}）专业深度不足，未覆盖必备子面：{', '.join(gaps)}"
                "；写该领域专业场景前建议补齐对应 claim，否则易外行。",
                pack=topic,
            ))
    source_ids = {src.get("id") for src in sources if src.get("id")}
    for src in sources:
        sid = src.get("id") or "SRC-?"
        if not src.get("title"):
            out.append(finding("阻断级", "source_missing_title", f"{sid} 缺标题/出处名", pack=topic))
        if not (src.get("published_date") or src.get("accessed_date")):
            out.append(finding("阻断级", "source_missing_date", f"{sid} 缺发布日期或访问日期", pack=topic))
        if src.get("reliability") not in {"high", "medium", "low"}:
            out.append(finding("阻断级", "source_missing_reliability", f"{sid} 可信度必须是 high/medium/low", pack=topic))
        evaluation = src.get("evaluation") if isinstance(src.get("evaluation"), dict) else {}
        missing_axes = [axis for axis in SOURCE_EVALUATION_AXES if not str(evaluation.get(axis) or "").strip()]
        if missing_axes:
            out.append(finding("建议级", "source_evaluation_missing", f"{sid} 缺来源五轴评估：{', '.join(missing_axes)}", pack=topic))
        weak_values = {"unchecked", "unknown", "未知", "未评估", "missing_date", "low_authority", "unknown_purpose"}
        weak_axes = [
            axis for axis in SOURCE_EVALUATION_AXES
            if str(evaluation.get(axis) or "").strip().lower() in weak_values
        ]
        if weak_axes:
            out.append(finding("建议级", "source_evaluation_weak", f"{sid} 来源评估偏弱：{', '.join(weak_axes)}", pack=topic))
    for claim in claims:
        cid = claim.get("id") or "FACT-?"
        ids = set(claim.get("source_ids") or [])
        if not claim.get("claim"):
            out.append(finding("阻断级", "claim_missing_text", f"{cid} 缺事实文本", pack=topic))
        if not ids:
            out.append(finding("阻断级", "claim_missing_source", f"{cid} 未绑定来源", pack=topic))
        missing = sorted(ids - source_ids)
        if missing:
            out.append(finding("阻断级", "claim_unknown_source", f"{cid} 引用未知来源：{', '.join(missing)}", pack=topic))
        if claim.get("confidence") not in {"high", "medium", "low"}:
            out.append(finding("阻断级", "claim_missing_confidence", f"{cid} 可信度必须是 high/medium/low", pack=topic))
        # 置信度↔来源质量绑定：high 置信不该压在单条非权威来源上（幻觉最易在此处混过审）。
        # 规则：confidence=high 要么至少一条 reliability=high 来源，要么 ≥2 条来源交叉印证；否则建议降级或补源。
        # 关键词/可信度都是结构化字段，判定确定性；但"权威度"有主观性，故只出建议级（守 B10：不硬拦）。
        if claim.get("confidence") == "high":
            bound = [s for s in sources if s.get("id") in ids]
            if bound:
                has_high_authority = any(s.get("reliability") == "high" for s in bound)
                corroborated = len(bound) >= 2
                if not has_high_authority and not corroborated:
                    out.append(finding(
                        "建议级", "claim_confidence_unbacked",
                        f"{cid} 标 confidence=high，却既无 high 可信度来源、也无 ≥2 条来源交叉印证"
                        f"（当前 {len(bound)} 条来源）——high 置信不应压在单条非权威来源上：补一条权威来源、"
                        "加一条独立印证，或把置信度降为 medium。",
                        pack=topic))
        if not claim.get("applicable_chapters"):
            out.append(finding("建议级", "claim_missing_chapter_scope", f"{cid} 未写适用章节", pack=topic))
    freshness = pack_freshness(pack)
    freshness_days = freshness["freshness_days"]
    if freshness["reason"] == "missing_updated_at":
        sev = "阻断级" if high_risk else "建议级"
        out.append(finding(sev, "pack_missing_updated_at", f"资料包 {topic} 缺 updated_at，无法判断是否过期", pack=topic))
    elif freshness["stale"]:
        sev = "阻断级" if high_risk else "建议级"
        out.append(finding(
            sev,
            "pack_stale",
            f"资料包 {topic} 已超过 {freshness_days} 天有效期（updated_at={freshness['updated_at']}，age={freshness['age_days']} 天）",
            pack=topic,
        ))
    return out


def scan_amateur_pitfalls(text: str, domains: dict[str, list[str]]) -> list[dict[str, Any]]:
    """扫正文里的领域外行雷区（术语混用/常识硬伤）→ 建议级候选。只对已检测到的领域扫。"""
    out: list[dict[str, Any]] = []
    for domain in domains:
        for trigger, why in DOMAIN_PITFALLS.get(domain, []):
            if isinstance(trigger, tuple):
                if all(t in text for t in trigger):
                    hit = "+".join(trigger)
                else:
                    continue
            elif trigger in text:
                hit = trigger
            else:
                continue
            out.append(finding(
                "建议级", "amateur_pitfall_candidate",
                f"[{domain}] 疑似外行硬伤「{hit}」：{why}（启发式候选·请结合语境人工核实）",
                domain=domain, evidence=hit,
            ))
    return out


def scan_unsupported_professional_details(text: str, packs: list[dict[str, Any]],
                                          domains: dict[str, list[str]]) -> list[dict[str, Any]]:
    """本章命中的领域专业关键词，若在该领域 ready 包的 claims 语料里找不到 → 疑似"凭记忆编"。

    建议级候选：提醒作者本章这些专业点可能没有资料支撑（反向 scene-usage）。"""
    out: list[dict[str, Any]] = []
    for domain, hits in domains.items():
        ready = [p for p in packs if p.get("domain") == domain and p.get("status") == "ready"]
        if not ready:
            continue  # 无 ready 包由 missing_research_pack 覆盖，这里只管"有包但没覆盖到"
        corpus = " ".join(
            str(c.get("claim") or "") + " " + str(c.get("usage") or "")
            for p in ready for c in (p.get("claims") or [])
        )
        unsupported = [h for h in hits if h not in corpus]
        if unsupported:
            out.append(finding(
                "建议级", "unsupported_professional_detail",
                f"[{domain}] 本章出现专业关键词 {', '.join(unsupported[:8])}，但 ready 资料包 claims 未覆盖"
                "——疑似凭记忆写专业细节，建议补对应 claim 或回 novel-research 深搜。",
                domain=domain, evidence="、".join(unsupported[:8]),
            ))
    return out


def check_project(root: str | Path, chapter: int | None = None, *, write: bool = True) -> dict[str, Any]:
    root = Path(root)
    idx = load_index(root)
    has_index = index_path(root).exists()
    project_text = read_project_text(root)
    chapter_text = read_chapter_text(root, chapter)
    text = "\n".join([project_text, chapter_text])
    domains = detect_domains(text)
    required_domains = read_required_domains(root)
    commercial = commercial_signal(text)
    findings: list[dict[str, Any]] = []
    packs = idx.get("packs", []) if has_index else []
    for domain in required_domains:
        matched = [
            p for p in packs
            if pack_matches_domain(p, domain, chapter, text)
            or (p.get("domain") == domain and chapter_applies(p.get("applicable_chapters"), chapter))
        ]
        ready = [p for p in matched if p.get("status") == "ready"]
        if not ready:
            findings.append(finding(
                "阻断级",
                "missing_required_research_pack",
                f"项目声明 {domain} 为必须专业核验领域，但没有适用的 ready 专业资料包",
                domain=domain,
                evidence="research_required_domains",
            ))
    for domain, hits in domains.items():
        matched = [p for p in packs if pack_matches_domain(p, domain, chapter, text)]
        ready = [p for p in matched if p.get("status") == "ready"]
        if not ready:
            findings.append(finding(
                "阻断级",
                "missing_research_pack",
                f"检测到 {domain} 专业场景关键词，但没有适用的 ready 专业资料包",
                domain=domain,
                evidence="、".join(hits[:8]),
            ))
    if commercial and not has_index:
        findings.append(finding(
            "建议级",
            "commercial_research_recommended",
            "商业/平台/出海/改编项目建议建立平台规则或目标市场资料包",
            evidence="、".join(commercial[:8]),
        ))
    for pack in relevant_packs(idx, chapter, text):
        findings.extend(validate_pack(root, pack, chapter=chapter))
    # 外行雷区 + 未绑定专业细节：只在逐章检查时扫本章正文（建议级候选·把资料约束正文从软约束变闭环）。
    if chapter is not None and chapter_text.strip():
        findings.extend(scan_amateur_pitfalls(chapter_text, domains))
        findings.extend(scan_unsupported_professional_details(chapter_text, packs, domains))
    blocking = sum(1 for item in findings if item.get("severity") == "阻断级")
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "generated_at": today(),
        "project_root": str(root.resolve()),
        "chapter": chapter,
        "ran": True,
        "detected_domains": domains,
        "required_domains": required_domains,
        "commercial_signals": commercial,
        "packs_checked": [
            {
                "topic": p.get("topic"),
                "domain": p.get("domain"),
                "status": p.get("status"),
                "pack_path": p.get("pack_path"),
            }
            for p in relevant_packs(idx, chapter, text)
        ],
        "total": len(findings),
        "blocking": blocking,
        "alerts": findings,
    }
    if write:
        write_json(report_path(root), report)
    return report


def _domain_need_topic(domain: str, hits: list[str], commercial: list[str]) -> str:
    labels = {
        "medical": "医疗流程与风险边界",
        "legal": "法律流程与证据边界",
        "crime": "刑侦/法医流程",
        "finance": "金融规则与行业流程",
        "military": "军事制度与战术边界",
        "history": "历史制度与时代细节",
        "religion": "宗教仪式与禁忌",
        "overseas": "出海/本地化规则",
        "technology": "技术原理与行业实践",
        "career": "职业流程与行业质感",
        "platform": "平台规则与商业连载证据",
    }
    if domain in labels:
        return labels[domain]
    if hits:
        return f"{hits[0]}相关专业资料"
    if commercial:
        return "商业发布与平台规则资料"
    return f"{domain} 专业资料"


def _research_command(root: Path, domain: str, topic: str, chapter: int | None, hits: list[str]) -> str:
    chapters = str(chapter) if chapter is not None else "all"
    risk = "high" if domain in HIGH_RISK_DOMAINS else "medium"
    keyword = hits[0] if hits else topic
    return (
        f'python3 skills/novel-research/scripts/research_pack.py scaffold "{root}" '
        f'--topic "{topic}" --domain {domain} --chapters {chapters} --risk {risk} '
        f'--keyword "{keyword}" --source "<标题>|<日期>|official|high|<URL>|<说明>" '
        f'--claim "<可写事实>|SRC-001|high|{chapters}|<写作用法>|<不确定项>|<禁用写法>"'
    )


def build_research_needs(root: str | Path, chapter: int | None = None, *, write: bool = False) -> dict[str, Any]:
    root = Path(root)
    idx = load_index(root)
    has_index = index_path(root).exists()
    project_text = read_project_text(root)
    chapter_text = read_chapter_text(root, chapter)
    text = "\n".join([project_text, chapter_text])
    detected = detect_domains(text)
    required = read_required_domains(root)
    commercial = commercial_signal(text)
    packs = idx.get("packs", []) if has_index else []
    domains: list[str] = []
    for domain in [*required, *detected.keys()]:
        if domain not in domains:
            domains.append(domain)
    if commercial and "platform" not in domains:
        domains.append("platform")

    needs: list[dict[str, Any]] = []
    ready_domains: list[str] = []
    for domain in domains:
        hits = detected.get(domain, [])
        matched = [
            p for p in packs
            if pack_matches_domain(p, domain, chapter, text)
            or (p.get("domain") == domain and chapter_applies(p.get("applicable_chapters"), chapter))
        ]
        ready = [p for p in matched if p.get("status") == "ready"]
        draft = [p for p in matched if p.get("status") != "ready"]
        required_domain = domain in required
        detected_high_risk = domain in detected and domain in HIGH_RISK_DOMAINS
        commercial_platform = domain == "platform" and bool(commercial)
        severity = "ready" if ready else ("blocking" if required_domain or detected_high_risk else "warning")
        if ready:
            ready_domains.append(domain)
        topic = _domain_need_topic(domain, hits, commercial)
        needs.append({
            "domain": domain,
            "topic": topic,
            "severity": severity,
            "required": required_domain,
            "detected_keywords": hits,
            "commercial_signals": commercial if commercial_platform else [],
            "ready_packs": [
                {"topic": p.get("topic"), "pack_path": p.get("pack_path"), "updated_at": p.get("updated_at")}
                for p in ready
            ],
            "draft_or_stale_packs": [
                {"topic": p.get("topic"), "status": p.get("status"), "pack_path": p.get("pack_path")}
                for p in draft
            ],
            "suggested_query": " ".join(part for part in [topic, domain, "官方 最新 规则 指南", today()[:4]] if part),
            "suggested_command": "" if ready else _research_command(root, domain, topic, chapter, hits),
        })

    open_market_tasks = []
    task_path = root / "评分" / "market_evidence_tasks.json"
    if task_path.exists():
        payload = load_json(task_path, {}) or {}
        raw_tasks = payload.get("tasks") if isinstance(payload, dict) else payload
        if isinstance(raw_tasks, list):
            open_market_tasks = [
                item for item in raw_tasks
                if isinstance(item, dict) and str(item.get("status") or "open") in {"open", "todo", "pending"}
            ]

    missing = [item for item in needs if item["severity"] in {"blocking", "warning"}]
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": NEEDS_KIND,
        "generated_at": today(),
        "project_root": str(root.resolve()),
        "chapter": chapter,
        "has_research_index": has_index,
        "detected_domains": detected,
        "required_domains": required,
        "commercial_signals": commercial,
        "ready_domains": ready_domains,
        "missing_count": len(missing),
        "blocking_count": sum(1 for item in missing if item["severity"] == "blocking"),
        "warning_count": sum(1 for item in missing if item["severity"] == "warning"),
        "needs": needs,
        "open_market_evidence_tasks": open_market_tasks,
    }
    if write:
        write_json(needs_json_path(root), report)
        write_text(needs_md_path(root), render_research_needs(report))
    return report


def render_research_needs(report: dict[str, Any]) -> str:
    lines = [
        "# 专业资料需求清单",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- 作品根：{report.get('project_root')}",
        f"- 章节：{report.get('chapter') if report.get('chapter') is not None else '全书/蓝图'}",
        f"- 阻断：{report.get('blocking_count', 0)}",
        f"- 建议：{report.get('warning_count', 0)}",
        "",
        "## 需求",
        "",
        "| 状态 | 领域 | 主题 | 命中/商业信号 | ready 包 | 下一步 |",
        "|---|---|---|---|---|---|",
    ]
    for item in report.get("needs", []):
        ready = "、".join(str(p.get("topic") or p.get("pack_path")) for p in item.get("ready_packs") or [])
        signals = "、".join([*(item.get("detected_keywords") or []), *(item.get("commercial_signals") or [])])
        next_step = "已覆盖" if item.get("severity") == "ready" else item.get("suggested_query")
        lines.append(
            "| "
            + " | ".join([
                md_cell(item.get("severity")),
                md_cell(item.get("domain")),
                md_cell(item.get("topic")),
                md_cell(signals),
                md_cell(ready or "无"),
                md_cell(next_step),
            ])
            + " |"
        )
    if not report.get("needs"):
        lines.append("| ready | 无命中专业领域 |  |  |  | 暂无需专业资料包；商业发布前仍建议跑一次 check |")
    missing = [item for item in report.get("needs", []) if item.get("suggested_command")]
    if missing:
        lines.extend(["", "## 推荐命令", ""])
        for item in missing:
            lines.extend([
                f"### {item.get('domain')} · {item.get('topic')}",
                "",
                "```bash",
                str(item.get("suggested_command")),
                "```",
                "",
            ])
    tasks = report.get("open_market_evidence_tasks") or []
    if tasks:
        lines.extend(["", "## 未完成市场证据任务", ""])
        for item in tasks[:20]:
            lines.append(f"- {item.get('topic') or item.get('id') or 'market evidence'}：{item.get('reason') or item.get('query') or ''}")
    return "\n".join(lines).rstrip() + "\n"


def build_research_jobs(root: str | Path, chapter: int | None = None, *, write: bool = False) -> dict[str, Any]:
    root = Path(root)
    needs = build_research_needs(root, chapter=chapter, write=write)
    existing = load_json(jobs_json_path(root), {}) or {}
    existing_by_key = {}
    if isinstance(existing, dict):
        for job in existing.get("jobs") or []:
            if not isinstance(job, dict):
                continue
            key = (str(job.get("domain") or ""), str(job.get("topic") or ""))
            existing_by_key[key] = job
    jobs: list[dict[str, Any]] = []
    for idx, item in enumerate(needs.get("needs") or [], 1):
        if item.get("severity") not in {"blocking", "warning"}:
            continue
        domain = str(item.get("domain") or "other")
        severity = str(item.get("severity") or "warning")
        topic = item.get("topic") or domain
        previous = existing_by_key.get((domain, str(topic))) or {}
        job = {
            "id": f"RJ-{idx:03d}-{domain.upper()}",
            "topic": topic,
            "domain": domain,
            "severity": severity,
            "priority": "P0" if severity == "blocking" else "P1",
            "required": bool(item.get("required")),
            "detected_keywords": item.get("detected_keywords") or [],
            "commercial_signals": item.get("commercial_signals") or [],
            "suggested_query": item.get("suggested_query") or "",
            "suggested_command": item.get("suggested_command") or "",
            "source_count": int(previous.get("source_count") or 0),
            "status": previous.get("status") or "open",
            "assignee": previous.get("assignee") or "",
            "notes": previous.get("notes") or "",
            "created_at": previous.get("created_at") or today(),
            "updated_at": previous.get("updated_at") or "",
            "verified_at": previous.get("verified_at") or "",
            "needs_ref": {
                "path": "资料/research_needs.json",
                "domain": domain,
                "topic": topic,
            },
        }
        if job["status"] in {"done", "waived"} and severity == "blocking":
            job["priority"] = "P0"
        jobs.append(job)
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": RESEARCH_JOBS_KIND,
        "generated_at": today(),
        "project_root": str(root.resolve()),
        "chapter": chapter,
        "needs_path": str(needs_json_path(root).resolve()),
        "job_count": len(jobs),
        "blocking_count": sum(1 for item in jobs if item.get("severity") == "blocking"),
        "warning_count": sum(1 for item in jobs if item.get("severity") == "warning"),
        "jobs": jobs,
    }
    if write:
        write_json(jobs_json_path(root), report)
        write_text(jobs_md_path(root), render_research_jobs(report))
    return report


def update_research_job(
    root: str | Path,
    job_id: str,
    *,
    status: str | None = None,
    assignee: str | None = None,
    source_count: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    payload = load_json(jobs_json_path(root), {}) or {}
    if not isinstance(payload, dict) or payload.get("kind") != RESEARCH_JOBS_KIND:
        payload = build_research_jobs(root, write=True)
    jobs = payload.get("jobs") or []
    matched = None
    for job in jobs:
        if isinstance(job, dict) and job.get("id") == job_id:
            matched = job
            break
    if matched is None:
        raise ValueError(f"unknown research job id: {job_id}")
    if status is not None:
        matched["status"] = status
        if status in {"done", "verified"} and not matched.get("verified_at"):
            matched["verified_at"] = today()
    if assignee is not None:
        matched["assignee"] = assignee
    if source_count is not None:
        matched["source_count"] = max(0, int(source_count))
    if notes is not None:
        matched["notes"] = notes
    matched["updated_at"] = today()
    payload["job_count"] = len(jobs)
    payload["blocking_count"] = sum(1 for item in jobs if item.get("severity") == "blocking" and item.get("status") not in {"done", "verified", "waived"})
    payload["warning_count"] = sum(1 for item in jobs if item.get("severity") == "warning" and item.get("status") not in {"done", "verified", "waived"})
    write_json(jobs_json_path(root), payload)
    write_text(jobs_md_path(root), render_research_jobs(payload))
    return matched


def render_research_jobs(report: dict[str, Any]) -> str:
    lines = [
        "# 专业资料深搜任务",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- 作品根：{report.get('project_root')}",
        f"- 章节：{report.get('chapter') if report.get('chapter') is not None else '全书/蓝图'}",
        f"- 任务数：{report.get('job_count', 0)}",
        f"- 阻断：{report.get('blocking_count', 0)}",
        f"- 建议：{report.get('warning_count', 0)}",
        "",
        "## 任务表",
        "",
        "| ID | 优先级 | 领域 | 主题 | 建议检索式 | 状态 | 负责人 | 来源数 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for job in report.get("jobs") or []:
        lines.append(
            "| "
            + " | ".join([
                md_cell(job.get("id")),
                md_cell(job.get("priority")),
                md_cell(job.get("domain")),
                md_cell(job.get("topic")),
                md_cell(job.get("suggested_query")),
                md_cell(job.get("status")),
                md_cell(job.get("assignee")),
                md_cell(job.get("source_count")),
            ])
            + " |"
        )
    if not report.get("jobs"):
        lines.append("| 无 |  |  |  | 暂无待补专业资料任务 | done |")
    commands = [job for job in report.get("jobs") or [] if job.get("suggested_command")]
    if commands:
        lines.extend(["", "## 推荐 scaffold 命令", ""])
        for job in commands:
            lines.extend([
                f"### {job.get('id')} · {job.get('topic')}",
                "",
                "```bash",
                str(job.get("suggested_command")),
                "```",
                "",
            ])
    return "\n".join(lines).rstrip() + "\n"


def _chapter_values(value: Any) -> list[int | str]:
    if value in (None, "", []):
        return []
    values = value if isinstance(value, list) else [value]
    out: list[int | str] = []
    for item in values:
        if item == "all":
            out.append("all")
            continue
        if isinstance(item, int):
            out.append(item)
            continue
        text = str(item).strip()
        if text.isdigit():
            out.append(int(text))
            continue
        m = re.match(r"^0*(\d+)\s*[-~至]\s*0*(\d+)$", text)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start > end:
                start, end = end, start
            out.extend(range(start, end + 1))
        elif text:
            out.append(text)
    dedup: list[int | str] = []
    for item in out:
        if item not in dedup:
            dedup.append(item)
    return dedup


def _scene_index(root: Path) -> dict[int, list[dict[str, Any]]]:
    payload = load_json(root / "设定" / "scene_cards.json", {}) or {}
    out: dict[int, list[dict[str, Any]]] = {}
    for scene in payload.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        try:
            chapter = int(scene.get("chapter") or 0)
        except (TypeError, ValueError):
            continue
        if chapter:
            out.setdefault(chapter, []).append(scene)
    return out


def build_scene_usage(root: str | Path, chapter: int | None = None, *, write: bool = False) -> dict[str, Any]:
    root = Path(root)
    idx = load_index(root)
    scenes_by_chapter = _scene_index(root)
    usages: list[dict[str, Any]] = []
    for pack in idx.get("packs") or []:
        if not isinstance(pack, dict):
            continue
        pack_chapters = _chapter_values(pack.get("applicable_chapters")) or ["all"]
        for claim in pack.get("claims") or []:
            if not isinstance(claim, dict):
                continue
            claim_chapters = _chapter_values(claim.get("applicable_chapters")) or pack_chapters
            if chapter is not None:
                if not chapter_applies(claim_chapters, chapter):
                    continue
                target_chapters: list[int | str] = [chapter]
            else:
                target_chapters = claim_chapters
            for ch in target_chapters:
                if ch == "all":
                    scene_ids: list[str] = []
                elif isinstance(ch, int):
                    scene_ids = [str(scene.get("id")) for scene in scenes_by_chapter.get(ch, []) if scene.get("id")]
                else:
                    scene_ids = []
                usages.append({
                    "pack_topic": pack.get("topic") or pack.get("topic_slug"),
                    "pack_path": pack.get("pack_path"),
                    "domain": pack.get("domain"),
                    "claim_id": claim.get("id"),
                    "claim": claim.get("claim"),
                    "source_ids": claim.get("source_ids") or [],
                    "chapter": ch,
                    "scene_ids": scene_ids,
                    "dramatic_use": claim.get("usage") or "待填写：这条事实如何转化为场景行动、阻碍、道具、台词或误判。",
                    "uncertainty": claim.get("uncertainty") or "",
                    "forbidden_use": claim.get("forbidden_use") or "",
                })
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": RESEARCH_SCENE_USAGE_KIND,
        "generated_at": today(),
        "project_root": str(root.resolve()),
        "chapter": chapter,
        "usage_count": len(usages),
        "has_scene_cards": bool(scenes_by_chapter),
        "usages": usages,
    }
    if write:
        write_json(scene_usage_json_path(root), report)
        write_text(scene_usage_md_path(root), render_scene_usage(report))
    return report


def render_scene_usage(report: dict[str, Any]) -> str:
    lines = [
        "# 专业资料场景使用图",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- 章节：{report.get('chapter') if report.get('chapter') is not None else '全书'}",
        f"- 使用项：{report.get('usage_count', 0)}",
        f"- scene_cards：{report.get('has_scene_cards')}",
        "",
        "| 章节 | scene | 资料包 | fact | 来源 | 戏剧化用法 | 禁用写法 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in report.get("usages") or []:
        lines.append(
            "| "
            + " | ".join([
                md_cell(item.get("chapter")),
                md_cell("、".join(item.get("scene_ids") or [])),
                md_cell(item.get("pack_topic")),
                md_cell(item.get("claim")),
                md_cell(",".join(item.get("source_ids") or [])),
                md_cell(item.get("dramatic_use")),
                md_cell(item.get("forbidden_use")),
            ])
            + " |"
        )
    if not report.get("usages"):
        lines.append("| 无 |  |  |  |  | 暂无可映射 claims；先补 research_sources.json claims |  |")
    return "\n".join(lines).rstrip() + "\n"


def md_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", " ").replace("|", "\\|").strip()


def relpath(path: str | Path, base: str | Path) -> str:
    path = Path(path)
    base = Path(base)
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def find_research_indexes(scan_root: str | Path) -> list[Path]:
    root = Path(scan_root)
    seen: dict[str, Path] = {}
    direct = index_path(root)
    if direct.exists():
        seen[str(direct.resolve())] = direct
    bases = []
    novel_root = root / "创作区" / "写小说"
    if novel_root.exists():
        bases.append(novel_root)
    bases.append(root)
    for base in bases:
        if not base.exists():
            continue
        for path in base.glob("**/资料/research_sources.json"):
            seen.setdefault(str(path.resolve()), path)
    return sorted(seen.values(), key=lambda p: str(p))


def refresh_task_for_pack(project_root: Path, pack: dict[str, Any], freshness: dict[str, Any]) -> dict[str, Any]:
    topic = pack.get("topic") or pack.get("topic_slug") or "unknown"
    domain = pack.get("domain") or "other"
    keywords = " ".join(str(k) for k in (pack.get("keywords") or [])[:5])
    query_parts = [str(topic), str(domain), keywords, "官方", "最新", "指南", "规则", today()[:4]]
    return {
        "project_root": str(project_root.resolve()),
        "topic": topic,
        "domain": domain,
        "risk_level": pack.get("risk_level") or "medium",
        "pack_path": pack.get("pack_path") or "",
        "updated_at": freshness.get("updated_at") or "",
        "freshness_days": freshness.get("freshness_days"),
        "age_days": freshness.get("age_days"),
        "reason": freshness.get("reason") or "expired",
        "suggested_query": " ".join(part for part in query_parts if str(part).strip()),
        "action": "实时深搜核验；更新 sources/claims/updated_at；不能确认的内容转入 uncertain_items/forbidden_items。",
    }


def audit_project_refresh(index_file: str | Path) -> dict[str, Any]:
    index_file = Path(index_file)
    project_root = index_file.parent.parent
    payload = load_json(index_file, {}) or {}
    packs = payload.get("packs") if isinstance(payload, dict) else []
    if not isinstance(packs, list):
        packs = []
    items = []
    tasks = []
    stale_count = 0
    blocking_count = 0
    near_expiry_count = 0
    for pack in packs:
        if not isinstance(pack, dict):
            continue
        freshness = pack_freshness(pack)
        high_risk = pack_is_high_risk(pack)
        severity = ""
        if freshness["stale"]:
            stale_count += 1
            severity = "阻断级" if high_risk else "建议级"
            if high_risk:
                blocking_count += 1
                tasks.append(refresh_task_for_pack(project_root, pack, freshness))
        elif freshness.get("days_remaining") is not None and freshness["days_remaining"] <= 14:
            near_expiry_count += 1
            severity = "临期提醒"
        item = {
            "topic": pack.get("topic") or pack.get("topic_slug") or "unknown",
            "domain": pack.get("domain") or "other",
            "risk_level": pack.get("risk_level") or "medium",
            "status": pack.get("status") or "draft",
            "pack_path": pack.get("pack_path") or "",
            "updated_at": freshness.get("updated_at") or "",
            "freshness_days": freshness.get("freshness_days"),
            "age_days": freshness.get("age_days"),
            "days_remaining": freshness.get("days_remaining"),
            "stale": freshness["stale"],
            "reason": freshness["reason"],
            "severity": severity,
            "high_risk": high_risk,
        }
        items.append(item)
    return {
        "project_root": str(project_root.resolve()),
        "index_path": str(index_file.resolve()),
        "plan_path": str(refresh_plan_path(project_root).resolve()),
        "pack_count": len(items),
        "stale_count": stale_count,
        "near_expiry_count": near_expiry_count,
        "blocking": blocking_count,
        "high_risk_tasks": tasks,
        "packs": items,
    }


def render_project_refresh_plan(report: dict[str, Any]) -> str:
    lines = [
        "# 专业资料包刷新计划",
        "",
        f"- 生成日期：{today()}",
        f"- 作品根：{report.get('project_root')}",
        f"- 来源索引：{report.get('index_path')}",
        f"- 总资料包：{report.get('pack_count', 0)}",
        f"- 已过期：{report.get('stale_count', 0)}",
        f"- 临近过期：{report.get('near_expiry_count', 0)}",
        f"- 阻断级高风险过期包：{report.get('blocking', 0)}",
        "",
        "## 需实时深搜任务清单",
        "",
    ]
    tasks = report.get("high_risk_tasks") or []
    if tasks:
        lines.extend([
            "| 主题 | 领域 | 风险 | 过期原因 | 建议检索式 | 动作 |",
            "|---|---|---|---|---|---|",
        ])
        for task in tasks:
            lines.append(
                "| "
                + " | ".join([
                    md_cell(task.get("topic")),
                    md_cell(task.get("domain")),
                    md_cell(task.get("risk_level")),
                    md_cell(task.get("reason")),
                    md_cell(task.get("suggested_query")),
                    md_cell(task.get("action")),
                ])
                + " |"
            )
    else:
        lines.append("- 暂无阻断级高风险过期资料包。")
    lines.extend([
        "",
        "## 过期或临近过期资料包",
        "",
        "| 状态 | 主题 | 领域 | 风险 | updated_at | 有效期 | age | 剩余天数 | 文件 |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    rows = [
        p for p in report.get("packs", [])
        if p.get("stale") or p.get("severity") == "临期提醒"
    ]
    if rows:
        for pack in rows:
            lines.append(
                "| "
                + " | ".join([
                    md_cell(pack.get("severity") or ("过期" if pack.get("stale") else "正常")),
                    md_cell(pack.get("topic")),
                    md_cell(pack.get("domain")),
                    md_cell(pack.get("risk_level")),
                    md_cell(pack.get("updated_at")),
                    md_cell(pack.get("freshness_days")),
                    md_cell(pack.get("age_days")),
                    md_cell(pack.get("days_remaining")),
                    md_cell(pack.get("pack_path")),
                ])
                + " |"
            )
    else:
        lines.append("| 无 |  |  |  |  |  |  |  |  |")
    lines.extend([
        "",
        "## 全部资料包 freshness",
        "",
        "| 主题 | 领域 | 风险 | 状态 | updated_at | 有效期 | age | 剩余天数 | stale |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for pack in report.get("packs", []):
        lines.append(
            "| "
            + " | ".join([
                md_cell(pack.get("topic")),
                md_cell(pack.get("domain")),
                md_cell(pack.get("risk_level")),
                md_cell(pack.get("status")),
                md_cell(pack.get("updated_at")),
                md_cell(pack.get("freshness_days")),
                md_cell(pack.get("age_days")),
                md_cell(pack.get("days_remaining")),
                md_cell(pack.get("stale")),
            ])
            + " |"
        )
    if not report.get("packs"):
        lines.append("| 无资料包 |  |  |  |  |  |  |  |  |")
    return "\n".join(lines) + "\n"


def render_aggregate_refresh_plan(audit: dict[str, Any]) -> str:
    lines = [
        "# novel-research 全库刷新计划",
        "",
        f"- 生成日期：{today()}",
        f"- 扫描根：{audit.get('scan_root')}",
        f"- 项目数：{audit.get('project_count', 0)}",
        f"- 资料包总数：{audit.get('pack_count', 0)}",
        f"- 已过期资料包：{audit.get('stale_count', 0)}",
        f"- 阻断级高风险过期包：{audit.get('blocking', 0)}",
        "",
        "## 需实时深搜任务清单",
        "",
    ]
    tasks = audit.get("high_risk_tasks") or []
    if tasks:
        lines.extend([
            "| 项目 | 主题 | 领域 | 风险 | updated_at | 建议检索式 | 动作 |",
            "|---|---|---|---|---|---|---|",
        ])
        scan_root = Path(audit.get("scan_root") or ".")
        for task in tasks:
            lines.append(
                "| "
                + " | ".join([
                    md_cell(relpath(task.get("project_root") or "", scan_root)),
                    md_cell(task.get("topic")),
                    md_cell(task.get("domain")),
                    md_cell(task.get("risk_level")),
                    md_cell(task.get("updated_at")),
                    md_cell(task.get("suggested_query")),
                    md_cell(task.get("action")),
                ])
                + " |"
            )
    else:
        lines.append("- 暂无阻断级高风险过期资料包。")
    lines.extend([
        "",
        "## 项目汇总",
        "",
        "| 项目 | 资料包 | 已过期 | 临近过期 | 阻断 | 计划文件 |",
        "|---|---|---|---|---|---|",
    ])
    for project in audit.get("projects", []):
        scan_root = Path(audit.get("scan_root") or ".")
        lines.append(
            "| "
            + " | ".join([
                md_cell(relpath(project.get("project_root") or "", scan_root)),
                md_cell(project.get("pack_count")),
                md_cell(project.get("stale_count")),
                md_cell(project.get("near_expiry_count")),
                md_cell(project.get("blocking")),
                md_cell(relpath(project.get("plan_path") or "", scan_root)),
            ])
            + " |"
        )
    if not audit.get("projects"):
        lines.append("| 未找到 research_sources.json | 0 | 0 | 0 | 0 |  |")
    return "\n".join(lines) + "\n"


def refresh_audit(scan_root: str | Path, *, write: bool = True, aggregate_out: str | Path | None = None) -> dict[str, Any]:
    root = Path(scan_root)
    indexes = find_research_indexes(root)
    projects = [audit_project_refresh(path) for path in indexes]
    tasks = []
    for project in projects:
        tasks.extend(project.get("high_risk_tasks") or [])
    audit = {
        "schema_version": SCHEMA_VERSION,
        "kind": REFRESH_PLAN_KIND,
        "generated_at": today(),
        "scan_root": str(root.resolve()),
        "project_count": len(projects),
        "pack_count": sum(p.get("pack_count", 0) for p in projects),
        "stale_count": sum(p.get("stale_count", 0) for p in projects),
        "near_expiry_count": sum(p.get("near_expiry_count", 0) for p in projects),
        "blocking": sum(p.get("blocking", 0) for p in projects),
        "high_risk_tasks": tasks,
        "projects": projects,
        "aggregate_plan_path": "",
    }
    if write:
        for project in projects:
            write_text(Path(project["plan_path"]), render_project_refresh_plan(project))
        out_path: Path | None = None
        if aggregate_out:
            out_path = Path(aggregate_out)
        elif len(projects) != 1:
            out_path = refresh_plan_path(root)
        elif projects:
            audit["aggregate_plan_path"] = projects[0]["plan_path"]
        if out_path:
            audit["aggregate_plan_path"] = str(out_path.resolve())
            write_text(out_path, render_aggregate_refresh_plan(audit))
    return audit


def cmd_scaffold(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    result = scaffold(root, args)
    print(f"[ok] 专业资料包 → {result['pack_path']}")
    print(f"[ok] 来源索引 → {result['index_path']}")
    print(f"     status={result['status']}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = check_project(root, chapter=args.chapter, write=True)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[ok] 专业事实证据检查 → {report_path(root)}")
        print(f"     阻断：{report['blocking']} | 总问题：{report['total']}")
        for item in report["alerts"][:10]:
            print(f"  - [{item['severity']}] {item['type']}: {item['message']}")
    return 1 if report["blocking"] else 0


def cmd_needs(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = build_research_needs(root, chapter=args.chapter, write=not args.no_write)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if not args.no_write:
            print(f"[ok] 专业资料需求 JSON → {needs_json_path(root)}")
            print(f"[ok] 专业资料需求 MD   → {needs_md_path(root)}")
        print(f"     阻断：{report['blocking_count']} | 建议：{report['warning_count']} | 缺口：{report['missing_count']}")
        for item in report.get("needs", [])[:10]:
            print(f"  - [{item['severity']}] {item['domain']}: {item['topic']}")
    return 0


def cmd_jobs(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = build_research_jobs(root, chapter=args.chapter, write=not args.no_write)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if not args.no_write:
            print(f"[ok] 专业资料任务 JSON → {jobs_json_path(root)}")
            print(f"[ok] 专业资料任务 MD   → {jobs_md_path(root)}")
        print(f"     阻断：{report['blocking_count']} | 建议：{report['warning_count']} | 任务：{report['job_count']}")
        for item in report.get("jobs", [])[:10]:
            print(f"  - [{item['priority']}] {item['domain']}: {item['topic']}")
    return 0


def cmd_job_update(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    try:
        job = update_research_job(
            root,
            args.job_id,
            status=args.status,
            assignee=args.assignee,
            source_count=args.source_count,
            notes=args.notes,
        )
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(job, ensure_ascii=False, indent=2))
    else:
        print(f"[ok] research job updated: {job['id']} status={job.get('status')} assignee={job.get('assignee') or '-'} sources={job.get('source_count', 0)}")
        print(f"[ok] 专业资料任务 JSON → {jobs_json_path(root)}")
        print(f"[ok] 专业资料任务 MD   → {jobs_md_path(root)}")
    return 0


def cmd_scene_usage(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = build_scene_usage(root, chapter=args.chapter, write=not args.no_write)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if not args.no_write:
            print(f"[ok] research scene usage JSON → {scene_usage_json_path(root)}")
            print(f"[ok] research scene usage MD   → {scene_usage_md_path(root)}")
        print(f"     使用项：{report['usage_count']} | scene_cards={report['has_scene_cards']}")
    return 0


def cmd_refresh_audit(args: argparse.Namespace) -> int:
    root = Path(args.scan_root)
    if not root.exists():
        print(f"[err] 找不到扫描根：{root}", file=sys.stderr)
        return 2
    report = refresh_audit(root, write=not args.no_write, aggregate_out=args.aggregate_out)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if report.get("aggregate_plan_path"):
            print(f"[ok] 全库刷新计划 → {report['aggregate_plan_path']}")
        print(
            f"     项目：{report['project_count']} | 资料包：{report['pack_count']} | "
            f"过期：{report['stale_count']} | 阻断级高风险：{report['blocking']}"
        )
        for task in report.get("high_risk_tasks", [])[:10]:
            print(f"  - [需实时深搜] {task['topic']} ({task['domain']}): {task['suggested_query']}")
    return 1 if report["blocking"] and not args.no_fail else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="novel professional research packet tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold", help="create/update a professional research packet")
    sc.add_argument("project_root")
    sc.add_argument("--topic", required=True)
    sc.add_argument("--domain", default="other")
    sc.add_argument("--chapters", default="all")
    sc.add_argument("--risk", choices=["high", "medium", "low"], default="high")
    sc.add_argument("--status", choices=["draft", "ready", "stale", "needs_review"], default=None)
    sc.add_argument("--freshness-days", type=int, default=None,
                    help="有效期天数；不填则按领域分档默认（平台30/法律医疗90-120/历史1825…）")
    sc.add_argument("--keyword", action="append", default=[])
    sc.add_argument("--source", action="append", default=[], help="标题|日期|类型|可信度|URL|说明")
    sc.add_argument("--claim", action="append", default=[], help="事实|来源ID|可信度|章节|使用方式|不确定项|禁用写法")
    sc.add_argument("--uncertain", action="append", default=[])
    sc.add_argument("--forbidden", action="append", default=[])
    sc.set_defaults(func=cmd_scaffold)

    ck = sub.add_parser("check", help="validate research evidence coverage")
    ck.add_argument("project_root")
    ck.add_argument("--chapter", type=int, default=None)
    ck.add_argument("--json", action="store_true")
    ck.set_defaults(func=cmd_check)

    nd = sub.add_parser("needs", help="detect missing specialist research packets before drafting")
    nd.add_argument("project_root")
    nd.add_argument("--chapter", type=int, default=None)
    nd.add_argument("--json", action="store_true")
    nd.add_argument("--no-write", action="store_true")
    nd.set_defaults(func=cmd_needs)

    jobs = sub.add_parser("jobs", help="turn missing specialist research needs into actionable search jobs")
    jobs.add_argument("project_root")
    jobs.add_argument("--chapter", type=int, default=None)
    jobs.add_argument("--json", action="store_true")
    jobs.add_argument("--no-write", action="store_true")
    jobs.set_defaults(func=cmd_jobs)

    ju = sub.add_parser("job-update", help="update a research job status/assignee/source count")
    ju.add_argument("project_root")
    ju.add_argument("job_id")
    ju.add_argument("--status", choices=["open", "in_progress", "done", "verified", "waived", "blocked"], default=None)
    ju.add_argument("--assignee", default=None)
    ju.add_argument("--source-count", type=int, default=None)
    ju.add_argument("--notes", default=None)
    ju.add_argument("--json", action="store_true")
    ju.set_defaults(func=cmd_job_update)

    su = sub.add_parser("scene-usage", help="map research claims to chapters/scenes for drafting and review")
    su.add_argument("project_root")
    su.add_argument("--chapter", type=int, default=None)
    su.add_argument("--json", action="store_true")
    su.add_argument("--no-write", action="store_true")
    su.set_defaults(func=cmd_scene_usage)

    ra = sub.add_parser("refresh-audit", help="scan research_sources.json files and write refresh plans")
    ra.add_argument("scan_root", nargs="?", default=".")
    ra.add_argument("--json", action="store_true")
    ra.add_argument("--no-write", action="store_true")
    ra.add_argument("--no-fail", action="store_true", help="return 0 even when high-risk stale packs exist")
    ra.add_argument("--aggregate-out", default=None, help="optional aggregate research_refresh_plan.md path")
    ra.set_defaults(func=cmd_refresh_audit)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
