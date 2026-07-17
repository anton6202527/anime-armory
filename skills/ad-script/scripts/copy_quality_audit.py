#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告文案质量机检（ad 线编剧轴 P2·advisory）——VO 冗余 / 卖点复读 / 套话堆砌 / 语速密度。

为什么存在：
    ad-script 现有机检只管**合规**与**算术**：`ad_law_check.py` 查违禁词，
    `finalize_storyboard.py` 对账时长/强制项落镜/接缝。两者都不问一句话：
    **「这 30 秒的文案本身写得好不好？」**——同一件事说了两遍、同一个卖点复读三次、
    整句都是「匠心品质·卓越体验」这类无实证形容词、VO 塞得根本念不完。
    这些在成片里是**直接浪费秒数**（广告总时长是硬约束，每一秒都是钱），却全线无人检。

治什么根因：
    「30 秒的预算被复读和套话吃掉」——广告不像剧集有 20 分钟摊薄冗余，一句废话
    ≈ 丢掉一个卖点的展示位。本脚本在**配音前**把浪费的秒数标出来，改文案比改成片便宜。

⚠️ 三条与漫剧版（n2d/comic）的领域差异——本脚本据此重新定义判据，**不是移植**：
    ① **广告里的重复是刻意手法**。品牌名/slogan/CTA/法律声明反复出现 = 提升 recall 的
       正当设计，不是缺陷。所以冗余检测**先把这些片段从文本里抠掉再比**（见 `mask_exempt`），
       排除表取自 `需求/brief.json` 的 mandatories 与 `设定库/asset_registry.json` 的
       brand.name/slogan/text_logo。不抠 = 每条广告的片尾都被报一遍 = 本脚本直接不可用。
    ② **广告 VO 本来就要直给卖点**。n2d 的「信息直给/自陈情绪」口径搬过来会全线误报
       （「0 糖 0 卡，一天一盒」正是好广告文案）。ad 版把它重定义为
       **套话/空洞形容词堆砌**：无实证的赞美词密集出现（匠心·卓越·非凡·尊享…）。
       同一行里有数字/单位等实证时降为 info——有支撑的形容词不是套话。
    ③ **与 `ad_law_check.py` 去重**。套话词表与《广告法》「绝对化用语」词表天然重叠
       （顶级/极致/终极/最佳/唯一/领先…）。双重去重：
         · **静态**：`EMPTY_ADJECTIVES` 刻意**不收**任何 ad_law_check 已覆盖的词（见词表注释）；
         · **运行时**：读 `脚本/广告法机检报告.json`（若存在），**已被广告法机检命中的行不再报
           套话**——同一句话不该在两份报告里各响一次，否则文案只会开始无视告警。

诚实边界：
    - **advisory：默认只产 warn/info，永不产 block**。脆弱的关键词/相似度启发式无权硬阻断
      付费流程——同仓明写「Creative heuristics stay advisory」（ad-craft/gate.py:519），
      只有独立的广告法闸门能 block。`--strict` 只影响退出码，不改变严重度。
    - 阈值全是内部启发式（`provenance: internal-heuristic·confidence=low`），env 可标定。
      语速 12 字符/秒**只发 WARN、不冒充法定或行业数值**——与 ad-script SKILL.md 对
      「内部 12 字符/秒与 3% 字高只发 WARN」的既定纪律一致。
    - VO 时长是**实测值**才有意义：占位配音（`vo_placeholder`/`has_placeholder`）下的密度结论
      建立在估算时长上 → 降为 info 并注明，不拿估算值当证据。
    - 缺 `脚本/voiceover.txt` → `available=false` + warn，不崩、不臆造通过。
    - 广告不拆集：粒度是整支片，无集/话参数。

VO 解析：广告 VO 是**逐句纯文本**，没有 n2d 的 `[镜头N·角色·情绪]` 前缀（那是漫剧格式），
    所以自带解析器：一行一句，跳空行与 `#` 注释，保留**原始行号**（供与广告法报告的
    line 对齐去重）。允许可选的 `旁白：`/`VO:`/`0-3s` 之类前缀，剥掉后再比。

用法：
    cd skills/ad-script/scripts
    python3 copy_quality_audit.py <作品根> [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

VERSION = 1
KIND = "ad_copy_quality_audit"
REPORT_REL = os.path.join("生产数据", "ad_copy_quality_audit.json")
LAW_REPORT_REL = os.path.join("脚本", "广告法机检报告.json")

# ── 阈值（内部启发式·env 可标定·confidence=low） ───────────────────────────────
# char-2gram Jaccard：参考 n2d/redundancy_audit 的 0.6/0.75 口径（对中文短句 0.6 ≈ 大半重合）。
# 但**严重度不跟着抄**：n2d 在 ≥0.75 升 block，ad 线一律 warn（advisory 纪律，见 docstring）。
PAIR_SIM_WARN = float(os.environ.get("AD_COPY_SIM_WARN", "0.6"))
PAIR_SIM_HIGH = float(os.environ.get("AD_COPY_SIM_HIGH", "0.75"))
MIN_LINE_CHARS = int(os.environ.get("AD_COPY_MIN_CHARS", "8"))
# 同一卖点 n-gram 在 ≥3 句复现 = 30s 里至少浪费两次曝光位。
USP_NGRAM_LEN = int(os.environ.get("AD_COPY_USP_NGRAM_LEN", "4"))
USP_MIN_LINES = int(os.environ.get("AD_COPY_USP_MIN_LINES", "3"))
# 一行里空洞形容词命中数达到这个数 = 堆砌。
EMPTY_ADJ_STACK_MIN = int(os.environ.get("AD_COPY_EMPTY_ADJ_MIN", "2"))
# 语速上限（字符/秒）。**内部值·只 WARN·不是法定/行业标准**。
VO_DENSITY_WARN = float(os.environ.get("AD_COPY_DENSITY_WARN", "12"))

NGRAM = 2
PROVENANCE = "internal-heuristic·confidence=low"

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】]+")
# 可选行首标记：`旁白：` / `VO:` / `字幕：` / `0-3s` / `1.` —— 剥掉后才是文案本体。
_VO_PREFIX_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)?\s*[-–~]\s*\d+(?:\.\d+)?\s*s\b\s*[:：]?\s*)?"
                           r"(?:(?:旁白|画外音|配音|字幕|VO|voiceover|V\.?O\.?)\s*[:：]\s*)?"
                           r"(?:\d+[.)、]\s*)?", re.IGNORECASE)
# 实证信号：有数字/单位/百分比 → 形容词有支撑，套话结论降级。
_EVIDENCE_RE = re.compile(r"\d|[％%]|毫克|克|ml|升|小时|分钟|天|年|倍|款|项|次", re.IGNORECASE)

# 空洞形容词词表（内部启发式·confidence=low）。
# **刻意不收** ad_law_check.py 已覆盖的词：顶级/顶尖/极致/极品/终极/最佳/最好/唯一/独一无二/
# 独家/首选/领先/遥遥领先/无与伦比/万能/第一…——那些由广告法机检负责（且严重度更高），
# 这里再收一遍只会让同一句话响两次（见模块 docstring ③）。
EMPTY_ADJECTIVES = (
    "匠心", "匠人精神", "匠造", "精工", "臻品", "臻选", "臻享", "至臻", "至尊",
    "卓越", "非凡", "超凡", "出众", "卓尔不凡", "尊享", "尊贵", "奢华", "华贵",
    "完美", "震撼", "惊艳", "梦幻", "神奇", "魅力", "质感", "格调", "品味",
    "高端", "精致", "优雅", "时尚", "潮流", "用心", "甄选", "优选",
    "尽享", "畅享", "悦享", "焕新", "蜕变", "传承经典", "淋漓尽致", "无微不至",
    "全新升级", "品质卓越", "值得拥有", "不容错过",
)


# ── 纯函数（无 IO·可测） ──────────────────────────────────────────────────────

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str) -> Dict[str, str]:
    """ad gate 消费 `msg` 键（见 ad-craft/gate.py:52）。"""
    return {"severity": severity, "code": code, "msg": msg}


def clean(text: str) -> str:
    """去标点/空白，得到用于比对的裸文本。纯函数·可测。"""
    return _NOISE_RE.sub("", str(text or ""))


def shingles(text: str, n: int = NGRAM) -> Set[str]:
    """去噪后的 char n-gram 集合。纯函数·可测（与 n2d 同法，本线自包含·复制不 import）。"""
    c = clean(text)
    if len(c) < n:
        return {c} if c else set()
    return {c[i:i + n] for i in range(len(c) - n + 1)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0


def parse_voiceover(text: str) -> List[Dict[str, Any]]:
    """广告 VO 纯文本 → [{line, text}]（line = **原始行号**，1-based）。纯函数·可测。

    广告 VO 没有 `[镜头N·角色·情绪]` 前缀（那是 n2d 格式）——一行一句。保留原始行号是为了
    与 `脚本/广告法机检报告.json` 的 `line` 对齐做去重（见 `law_flagged_lines`）。"""
    out: List[Dict[str, Any]] = []
    for lineno, raw in enumerate(str(text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        body = _VO_PREFIX_RE.sub("", line, count=1).strip()
        if not body:
            continue
        out.append({"line": lineno, "text": body, "raw": line})
    return out


def exempt_phrases(brief: Optional[Mapping[str, Any]],
                   registry: Optional[Mapping[str, Any]]) -> List[str]:
    """**豁免表**：品牌名 / slogan / 文字标识 / CTA / 法律声明。纯函数·可测。

    这些在广告里重复是**刻意手法**（重复曝光提升 recall），不是缺陷——冗余检测必须先把它们
    从文本里抠掉再比，否则每支广告的片尾都被误报。这是本脚本能否用的生死线（docstring ①）。
    来源：brief.mandatories（slogan/cta/endcard_cta/legal_lines/logo）
        + asset_registry.brand（name/slogan/text_logo）。"""
    out: List[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and len(clean(value)) >= 2:
            out.append(value.strip())
        elif isinstance(value, (list, tuple)):
            for v in value:
                add(v)

    mand = (brief or {}).get("mandatories") or {}
    if isinstance(mand, Mapping):
        for key in ("slogan", "cta", "endcard_cta", "legal_lines", "logo", "tagline", "disclaimer"):
            add(mand.get(key))
    brand = (registry or {}).get("brand") or {}
    if isinstance(brand, Mapping):
        for key in ("name", "slogan", "text_logo", "tagline"):
            add(brand.get(key))
    # 长的先抠，避免短语是长语的子串时抠成碎片
    seen: Set[str] = set()
    uniq: List[str] = []
    for p in sorted(out, key=lambda s: -len(clean(s))):
        c = clean(p)
        if c in seen:
            continue
        seen.add(c)
        uniq.append(p)
    return uniq


def mask_exempt(text: str, phrases: Sequence[str]) -> str:
    """把豁免片段（品牌名/slogan/CTA/法律声明）从文本里抠掉，返回**残余文案**。纯函数·可测。

    刻意选「抠掉再比」而不是「整行豁免」：整行豁免会让「<品牌名>，今天你喝了吗」这类
    夹带品牌名的普通 VO 完全逃过冗余检测（召回塌陷）；抠掉后只有**纯品牌/slogan/CTA 行**
    残余为空而被跳过，夹带品牌名的正常句子仍照常比对残余部分。"""
    out = clean(text)
    for p in phrases:
        c = clean(p)
        if len(c) >= 2:
            out = out.replace(c, "")
    return out


def law_flagged_lines(law_report: Optional[Mapping[str, Any]]) -> Set[int]:
    """广告法机检报告里**来自 voiceover.txt** 的命中行号。纯函数·可测。

    只认 voiceover.txt 的命中（报告还含 广告脚本.md/storyboard.json 等文件，行号不同源，
    混用会误抑制）。这些行已经有一条广告法告警了，本脚本不再对同一行报套话（docstring ③）。"""
    out: Set[int] = set()
    for f in ((law_report or {}).get("findings") or []):
        if not isinstance(f, Mapping):
            continue
        name = os.path.basename(str(f.get("file") or ""))
        if name != "voiceover.txt":
            continue
        try:
            out.add(int(f.get("line")))
        except (TypeError, ValueError):
            continue
    return out


def redundant_pairs(lines: Sequence[Mapping[str, Any]], phrases: Sequence[str],
                    threshold: float = PAIR_SIM_WARN,
                    min_chars: int = MIN_LINE_CHARS) -> List[Dict[str, Any]]:
    """VO 两两相似度（比的是**抠掉豁免片段后的残余**）。纯函数·可测。

    残余不足 min_chars 的行不参与：纯 slogan/CTA 行残余为空 → 天然跳过（这正是要的）；
    短句（「来一盒」）相似度噪声大，也不比。"""
    rows: List[Tuple[Mapping[str, Any], Set[str]]] = []
    for row in lines:
        residual = mask_exempt(row.get("text") or "", phrases)
        if len(residual) < min_chars:
            continue
        rows.append((row, shingles(residual)))
    out: List[Dict[str, Any]] = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            sim = jaccard(rows[i][1], rows[j][1])
            if sim >= threshold:
                a, b = rows[i][0], rows[j][0]
                out.append({
                    "lines": [a.get("line"), b.get("line")],
                    "similarity": round(sim, 3),
                    "texts": [str(a.get("text"))[:60], str(b.get("text"))[:60]],
                })
    return out


def repeated_usp_mentions(lines: Sequence[Mapping[str, Any]], phrases: Sequence[str],
                          ngram_len: int = USP_NGRAM_LEN,
                          min_lines: int = USP_MIN_LINES) -> List[Dict[str, Any]]:
    """同一卖点短语（char n-gram）在 ≥min_lines 句复现。纯函数·可测。

    Jaccard 抓不到「换个说法把同一卖点又讲一遍」里共用的那个短语，所以单列。
    同样在**抠掉豁免片段后的残余**上统计——品牌名/slogan 复现是设计，不是浪费。"""
    gram_lines: Dict[str, List[int]] = {}
    for row in lines:
        residual = mask_exempt(row.get("text") or "", phrases)
        seen: Set[str] = set()
        for i in range(max(0, len(residual) - ngram_len + 1)):
            gram = residual[i:i + ngram_len]
            if gram in seen:
                continue
            seen.add(gram)
            gram_lines.setdefault(gram, []).append(int(row.get("line") or 0))
    hits = {g: ls for g, ls in gram_lines.items() if len(ls) >= min_lines}
    out: List[Dict[str, Any]] = []
    for gram in sorted(hits, key=lambda g: (-len(hits[g]), g)):
        # 合并同一短语的滑窗碎片（出现行集合相同且互为子串）
        if any(gram in prev["phrase"] or prev["phrase"] in gram for prev in out
               if set(prev["lines"]) == set(hits[gram])):
            continue
        out.append({"phrase": gram, "lines": hits[gram]})
    return out[:8]


def empty_adjective_hits(lines: Sequence[Mapping[str, Any]],
                         skip_lines: Optional[Set[int]] = None,
                         stack_min: int = EMPTY_ADJ_STACK_MIN) -> List[Dict[str, Any]]:
    """套话/空洞形容词堆砌（一行命中 ≥stack_min 个）。纯函数·可测。

    `skip_lines`：已被广告法机检命中的行——不重复报（docstring ③）。
    `has_evidence`：同行有数字/单位等实证 → 形容词有支撑，调用方降为 info。"""
    skip = skip_lines or set()
    out: List[Dict[str, Any]] = []
    for row in lines:
        lineno = int(row.get("line") or 0)
        if lineno in skip:
            continue
        text = str(row.get("text") or "")
        c = clean(text)
        hits = [w for w in EMPTY_ADJECTIVES if w in c]
        if len(hits) < stack_min:
            continue
        out.append({"line": lineno, "terms": hits, "text": text[:60],
                    "has_evidence": bool(_EVIDENCE_RE.search(text))})
    return out


def vo_density(lines: Sequence[Mapping[str, Any]], seconds: Optional[float]) -> Optional[float]:
    """VO 字符数 / 实测秒数（字符/秒）。纯函数·可测；秒数缺失/为 0 → None。"""
    if not seconds or seconds <= 0:
        return None
    chars = sum(len(clean(row.get("text") or "")) for row in lines)
    return round(chars / seconds, 2)


def build_findings(lines: Sequence[Mapping[str, Any]], phrases: Sequence[str],
                   skip_lines: Set[int], seconds: Optional[float],
                   placeholder: bool) -> List[Dict[str, str]]:
    """全部 checks → findings。纯函数·可测。**全部 warn/info，无 block**（advisory 纪律）。"""
    out: List[Dict[str, str]] = []

    for pair in redundant_pairs(lines, phrases):
        level = "高度雷同" if pair["similarity"] >= PAIR_SIM_HIGH else "疑似同义反复"
        out.append(finding("warn", "redundant_vo_pair",
                           f"第 {pair['lines'][0]} 行与第 {pair['lines'][1]} 行 VO 相似度 "
                           f"{pair['similarity']:.0%}（{level}）：『{pair['texts'][0]}』≈"
                           f"『{pair['texts'][1]}』——广告只有几十秒，同一件事说两遍等于丢掉一个"
                           "卖点的展示位；合并成一句，把省下的秒数还给卖点或 CTA。"
                           "（已排除品牌名/slogan/CTA/法律声明后比对；若确属刻意重复手法，忽略本条。）"))

    for hit in repeated_usp_mentions(lines, phrases):
        rows = "/".join(str(x) for x in hit["lines"])
        out.append(finding("warn", "repeated_usp_mention",
                           f"卖点短语『{hit['phrase']}』在第 {rows} 行复现 {len(hit['lines'])} 次"
                           f"（内部阈值 ≥{USP_MIN_LINES} 句）——同一卖点讲三遍是在花秒数买重复，"
                           "而不是买信息；只留信息首次落地那一处，其余改推进或删除。"
                           "（品牌名/slogan/CTA 已排除——那类重复是刻意曝光设计。）"))

    for hit in empty_adjective_hits(lines, skip_lines):
        terms = "、".join(hit["terms"][:4])
        if hit["has_evidence"]:
            out.append(finding("info", "empty_adjective_stack",
                               f"第 {hit['line']} 行堆了 {len(hit['terms'])} 个赞美词（{terms}）："
                               f"『{hit['text']}』——同行有数字/实证，暂按可接受记；仍建议让实证自己"
                               "说话，形容词减到一个。"))
        else:
            out.append(finding("warn", "empty_adjective_stack",
                               f"第 {hit['line']} 行堆了 {len(hit['terms'])} 个无实证形容词（{terms}）："
                               f"『{hit['text']}』——套话不携带任何信息，观众记不住也不相信；"
                               "换成可验证的事实（数字/对比/场景），或删。"
                               "（本条只看措辞空洞与否，不含合规判断——违禁词由 ad_law_check.py 负责。）"))

    if not lines:
        return out
    density = vo_density(lines, seconds)
    if density is None:
        out.append(finding("info", "vo_density_unavailable",
                           "缺 脚本/镜头时长.json 与 配音/时长清单.json 的实测 VO 秒数，"
                           "跳过语速密度核算（insufficient_data——不代表念得完）。"))
    elif density > VO_DENSITY_WARN:
        note = ("；**注意**配音仍是占位（时长为估算值），本条结论不可当证据，换真实 VO 后复跑"
                if placeholder else "")
        sev = "info" if placeholder else "warn"
        out.append(finding(sev, "vo_density_high",
                           f"VO 密度 {density} 字符/秒 > 内部参考 {VO_DENSITY_WARN} 字符/秒"
                           f"（{sum(len(clean(r.get('text') or '')) for r in lines)} 字 / {seconds:.2f}s）"
                           "——念得太赶，观众听不清且没有留白给画面；砍字或加秒。"
                           "该阈值是**内部启发式，不是法定/行业标准数值**，只作提示" + note + "。"))
    return out


# ── IO（best-effort·缺则 None/空） ────────────────────────────────────────────

def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_vo_text(root: Path) -> Optional[str]:
    try:
        return (root / "脚本" / "voiceover.txt").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def load_brief(root: Path) -> Optional[Dict[str, Any]]:
    data = load_json(root / "需求" / "brief.json")
    return data if isinstance(data, dict) else None


def load_registry(root: Path) -> Optional[Dict[str, Any]]:
    """定妆库母本优先（`设定库/asset_registry.json` 是人写的母本，见 ad-craft/gate.py:257），
    缺失时回退出图快照。"""
    for rel in (("设定库", "asset_registry.json"), ("出图", "共享", "asset_registry.json")):
        data = load_json(root.joinpath(*rel))
        if isinstance(data, dict):
            return data
    return None


def load_law_report(root: Path) -> Optional[Dict[str, Any]]:
    data = load_json(root / LAW_REPORT_REL)
    return data if isinstance(data, dict) else None


def load_vo_seconds(root: Path) -> Tuple[Optional[float], bool]:
    """实测 VO 总秒数 + 是否占位。返回 (seconds|None, placeholder)。

    优先 `脚本/镜头时长.json`（finalize_storyboard 的产物，含权威 vo_seconds/vo_placeholder），
    回退 `配音/时长清单.json` 自行汇总（顶层 has_placeholder 是占位单一真值源）。"""
    fin = load_json(root / "脚本" / "镜头时长.json")
    if isinstance(fin, Mapping) and fin.get("vo_seconds"):
        try:
            return float(fin["vo_seconds"]), bool(fin.get("vo_placeholder"))
        except (TypeError, ValueError):
            pass
    dl = load_json(root / "配音" / "时长清单.json")
    if isinstance(dl, Mapping):
        items = dl.get("lines") or []
        placeholder = bool(dl.get("has_placeholder")) if "has_placeholder" in dl else None
    elif isinstance(dl, list):
        items, placeholder = dl, None
    else:
        return None, False
    total = 0.0
    for it in items:
        if not isinstance(it, Mapping):
            continue
        try:
            total += float(it.get("seconds", it.get("时长", it.get("duration", 0))) or 0)
            total += float(it.get("gap_after", 0) or 0)
        except (TypeError, ValueError):
            continue
    if placeholder is None:
        placeholder = any(isinstance(it, Mapping) and (it.get("占位") or it.get("placeholder"))
                          for it in items)
    return (round(total, 3) or None), bool(placeholder)


def build(root: Path) -> Dict[str, Any]:
    """契约形状（findings 用 `msg` 键，ad gate 可直接消费）：

        {"schema_version":1,"kind":"ad_copy_quality_audit","available":bool,
         "summary":{"block","warn","info"},"findings":[{"severity","code","msg"}]}

    `summary.block` 恒为 0——advisory 纪律（见模块 docstring）。"""
    root = Path(root)
    text = load_vo_text(root)
    available = text is not None
    findings: List[Dict[str, str]] = []

    if not available:
        findings.append(finding("warn", "voiceover_missing",
                                "缺 脚本/voiceover.txt——没有 VO 文案可审（insufficient_data，"
                                "不代表文案没问题）。先跑 ad-script 脚本 pass 产出 voiceover.txt。"))
        lines: List[Dict[str, Any]] = []
        phrases: List[str] = []
        seconds, placeholder = None, False
        law = None
    else:
        lines = parse_voiceover(text)
        brief = load_brief(root)
        registry = load_registry(root)
        phrases = exempt_phrases(brief, registry)
        law = load_law_report(root)
        seconds, placeholder = load_vo_seconds(root)
        if not lines:
            findings.append(finding("warn", "voiceover_empty",
                                    "脚本/voiceover.txt 存在但没有任何可解析的 VO 句"
                                    "（只有空行/注释？）——文案还没落档。"))
        if not phrases:
            findings.append(finding("info", "exempt_list_unavailable",
                                    "缺 需求/brief.json 的 mandatories 与 设定库/asset_registry.json 的 "
                                    "brand——无法排除品牌名/slogan/CTA/法律声明，冗余检测**可能把刻意的"
                                    "品牌重复误报为冗余**；补齐后复跑再看本报告。"))
        findings.extend(build_findings(lines, phrases, law_flagged_lines(law), seconds, placeholder))

    return {
        "schema_version": VERSION,
        "kind": KIND,
        "available": available,
        "project_root": str(root),
        "generated_at": now_iso(),
        "thresholds": {
            "pair_sim_warn": PAIR_SIM_WARN, "pair_sim_high": PAIR_SIM_HIGH,
            "min_line_chars": MIN_LINE_CHARS, "usp_ngram_len": USP_NGRAM_LEN,
            "usp_min_lines": USP_MIN_LINES, "empty_adj_stack_min": EMPTY_ADJ_STACK_MIN,
            "vo_density_warn": VO_DENSITY_WARN, "ngram": NGRAM,
            "provenance": PROVENANCE,
            "note": "advisory：本检永不产 block（Creative heuristics stay advisory）。"
                    "12 字符/秒是内部参考值，不是法定或行业标准。",
        },
        "inputs": {
            "vo_lines": len(lines),
            "exempt_phrases": list(phrases),
            "vo_seconds": seconds,
            "vo_placeholder": placeholder if available else False,
            "law_report_available": law is not None,
        },
        "summary": {
            "block": 0,  # advisory：恒 0，不是「这次刚好没有」
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    i = report.get("inputs") or {}
    lines = ["# 广告文案质量机检 · VO", ""]
    if not report.get("available"):
        lines += ["- ⚠️ 未找到 `脚本/voiceover.txt`（available=false·降级为建议，不阻断）", ""]
    lines += [f"- VO {i.get('vo_lines')} 句 · 实测时长 {i.get('vo_seconds') or '—'}s"
              f" · 豁免片段 {len(i.get('exempt_phrases') or [])} 条"
              f" · 广告法报告 {'已读' if i.get('law_report_available') else '未找到'}",
              f"- warn {s.get('warn')} · info {s.get('info')}（advisory：本检不产 block）", ""]
    icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 未检出 VO 冗余/卖点复读/套话堆砌/语速超标（文案好不好仍需人判）")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    """原子写（tmp + os.replace）：报告被 gate/review 并发读时不会读到半截 JSON。"""
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    for target, payload in ((path, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                            (path.with_suffix(".md"), render_markdown(report))):
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="作品根")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ 同名 .md·原子写）")
    ap.add_argument("--json", action="store_true", help="打印 JSON 而非 markdown")
    ap.add_argument("--strict", action="store_true",
                    help="warn>0 时 exit 1（本检 advisory·恒无 block，--strict 只影响退出码）")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = build(root)
    if ns.write:
        write_report(root, report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
