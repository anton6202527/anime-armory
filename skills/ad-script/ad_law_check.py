#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《广告法》违禁词 / 极限词机检 —— 拍广告线相对 n2d 的核心差异化硬闸门。

扫广告文案/台词/VO/字幕/分镜，按《中华人民共和国广告法》及配套口径标出**绝对化用语**、
**虚假/误导表述**、**医疗保健极限词**、**化妆品禁用功效**、**迷信/封建**、**促销欺诈词**
等违禁/高危词，出定位报告（命中 block 即非零退出码）。**机检初筛 + 人判**：词表是确定性的，
最终是否违法仍需结合语境/资质（如已注册商标含"国"字、有依据的对比）由人复核——但默认从严。

匹配前先把文本**归一化**（NFKC + 去零宽字符 + 折叠内部空格），所以 `最 ` / `１００％` /
全角 / 中间插空格 / 常见繁体（療效→疗效、國家級→国家级）都能命中绕过手法；报告里的
snippet/line 仍用原文，便于人工定位。

报告 schema（ad-review 消费）：
    {"region":"<地区>","disabled":<bool>,"summary":{"block":N,"warn":N},
     "findings":[{"severity":"block|warn|info","term":"..","category":"..",
                  "file":"..","line":N,"snippet":".."},...]}
region=关闭 时仍写报告（disabled:true, summary 全 0, 附 reason），不只 print 退出。

自包含、纯标准库、带 pytest（不 import ad-craft/contract，作健壮独立闸门）。

用法：
    python3 ad_law_check.py 脚本/广告脚本.md 脚本/voiceover.txt --region 中国大陆 --json 脚本/广告法机检报告.json
    python3 ad_law_check.py <作品根>            # 缺文件参数时自动扫作品根下常见文案文件
"""
import argparse
import json
import os
import re
import sys
import unicodedata

# ── 词库（分类 + 严重度）。block=明确违禁；warn=高危/语境相关，需人判 ──────────
# 绝对化用语：广告法第九条明令禁止「国家级/最高级/最佳」等表示最高级、绝对化的用语。
# 监管补充（市场监管总局《广告绝对化用语执法指南》及处罚案例）：首选/领先/领导者/
# 遥遥领先/销量遥遥领先/绝版/独家/填补国内空白/央视上榜/国宴 等亦被认定为绝对化或不可证。
ABSOLUTE_TERMS = [
    "国家级", "最高级", "最佳", "最好", "最大", "最强", "最优", "最新", "最先进",
    "最低", "最便宜", "最高", "最受欢迎", "第一品牌", "全国第一", "全球第一", "世界第一",
    "行业第一", "排名第一", "销量第一", "唯一", "独一无二", "顶级", "顶尖", "极致",
    "极品", "终极", "绝无仅有", "无与伦比", "史无前例", "空前绝后", "万能", "100%",
    "百分之百", "全网最低", "全场最低", "王牌", "之最", "冠军品牌", "领袖品牌", "宇宙级",
    # —— 监管案例补充（绝对化/不可证） ——
    "首选", "领先", "领导者", "遥遥领先", "销量遥遥领先", "绝版", "独家",
    "填补国内空白", "央视上榜", "国宴",
]
# 单字"第一/最X"高危打底（用边界规则减少误杀，见 _ABSOLUTE_LOOSE / WHITELIST）。
ABSOLUTE_LOOSE = ["第一", "最"]

# 医疗 / 保健 / 功效极限词：保健食品不得宣称疾病预防治疗功能；普通食品禁医疗用语。
# 注：100% 已并入 ABSOLUTE_TERMS，这里不再重复（去重，避免一处文本两类命中）。
MEDICAL_TERMS = [
    "治愈", "根治", "痊愈", "药到病除", "包治", "speedy cure", "无毒副作用", "无副作用",
    "百分百有效", "100%有效", "疗效", "治疗", "防癌", "抗癌", "防病", "祛病", "消炎",
    "杀菌率", "抑菌率", "促进康复", "壮阳", "减肥神器", "一针见效", "一次根除", "永不复发",
    "三天见效", "七天美白", "立竿见影", "彻底解决", "纯天然无添加",
    # —— 监管补充：医疗用语 / 处方资质暗示（普通食品·器械·药品混淆） ——
    "刺激细胞再生", "修复受损", "医院同款", "处方级", "械字号", "OTC",
]
# 化妆品禁用功效宣称（《化妆品监督管理条例》《化妆品分类规则》明确普通化妆品不得宣称）：
# 抗衰/祛斑(非特证)/生发/丰胸/瘦身/排毒 等属医疗或特殊用途越界宣称，单列 block 类别。
COSMETICS_TERMS = [
    "抗衰", "祛斑", "生发", "丰胸", "瘦身", "排毒",
]
# 虚假 / 误导 / 夸大：含未证实承诺、绝对承诺。
FALSE_TERMS = [
    "稳赚不赔", "零风险", "无风险", "保本保息", "包过", "包就业", "包治百病",
    "永久", "终身免费", "绝对安全", "绝对有效", "百分百安全", "假一赔万",
    # —— 金融 / 教育监管补充（保收益/包录取类不可证承诺） ——
    "保本", "保收益", "稳健高回报", "包offer", "保录取", "名师押题",
]
# 迷信 / 封建：广告不得含妨碍社会公共秩序或违背社会良好风尚的内容。
SUPERSTITION_TERMS = ["开光", "辟邪", "转运", "招财进宝符", "改运", "风水宝地保佑"]
# 促销欺诈 / 时限欺诈：虚构原价、虚假优惠、诱导紧迫（FTC/EU 海外亦硬禁，不降级）。
PROMO_TERMS = ["全网最低价", "史上最低价", "原价虚构", "仅此一天", "最后一天", "清仓甩卖最后机会"]

# 白名单：这些"最X/第一"是时间/序数/固定词，非最高级广告承诺，降噪不误杀。
WHITELIST = [
    "最后", "最初", "最近", "最终", "最早", "第一时间", "第一步", "第一次",
    "第一人称", "第一章", "第一集", "第一季", "最好不过",
]

# 常见繁体 → 简体变体映射（按 banned 词补充；归一化阶段统一成简体再匹配）。
# stdlib 无繁简转换库，这里仅覆盖词库里的高频字，并在文档注明该局限性。
_TRAD_SIMP = {
    "療": "疗", "國": "国", "級": "级", "癒": "愈", "藥": "药",
    "獨": "独", "頂": "顶", "極": "极", "終": "终", "領": "领",
    "億": "亿", "賠": "赔", "萬": "万", "費": "费",
    "嚴": "严", "畫": "画", "腦": "脑", "點": "点", "風": "风", "寶": "宝",
}

CATEGORIES = [
    ("绝对化用语", ABSOLUTE_TERMS, "block"),
    ("医疗保健极限词", MEDICAL_TERMS, "block"),
    ("化妆品禁用功效", COSMETICS_TERMS, "block"),
    ("虚假/绝对承诺", FALSE_TERMS, "block"),
    ("迷信封建", SUPERSTITION_TERMS, "block"),
    # 促销欺诈（虚构原价/虚假优惠/诱导紧迫）属虚假宣传，国内《广告法》第二十八条、海外 FTC/EU
    # 均硬禁——base=block，且海外不降级。
    ("促销欺诈", PROMO_TERMS, "block"),
]

# 海外口径：绝对化用语按平台政策松一档→warn；但促销欺诈（FTC/EU 仍硬禁）**不降级**。
REGION_OVERRIDES = {
    "海外": {"绝对化用语": "warn"},
}

DEFAULT_SCAN_FILES = [
    "脚本/广告脚本.md", "脚本/voiceover.txt", "脚本/字幕_zh.srt",
    "脚本/字幕_英文.srt", "脚本/storyboard.json",
    "创意/创意脚本.md", "创意/concept.md",
]

_ZERO_WIDTH = "​‌‍﻿"


def normalize(text):
    """归一化用于匹配的并行文本：NFKC（全角→半角/兼容字符）+ 去零宽 + 繁→简（词库覆盖字）
    + 折叠内部空白。返回与匹配等价的标准化串（snippet/line 仍用原文）。"""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate({ord(c): None for c in _ZERO_WIDTH})
    text = "".join(_TRAD_SIMP.get(ch, ch) for ch in text)
    # 折叠所有空白（含 NFKC 后残留空格）为空——绝对化/极限词内不应有空格，去之防"最 好"绕过
    text = re.sub(r"\s+", "", text)
    return text


def _whitelisted_at(norm_text, idx, term):
    """命中 ABSOLUTE_LOOSE（最/第一）时，若落在白名单复合词里则跳过。基于归一化文本定位。"""
    for w in WHITELIST:
        wn = normalize(w)
        pos = norm_text.find(wn)
        while pos != -1:
            if pos <= idx < pos + len(wn):
                return True
            pos = norm_text.find(wn, pos + 1)
    return False


def scan_text(text, region="中国大陆"):
    """返回 findings: [{category, term, severity, line, col, context}]。

    逐行匹配在**归一化文本**上做（去空格/全角/零宽/繁体），命中后映射回原行的近似列做
    snippet（原文保留，便于人工定位）。"""
    findings = []
    overrides = REGION_OVERRIDES.get(region, {})
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        norm = normalize(line)
        for category, terms, base_sev in CATEGORIES:
            sev = overrides.get(category, base_sev)
            for term in terms:
                nterm = normalize(term)
                if not nterm:
                    continue
                start = 0
                while True:
                    idx = norm.find(nterm, start)
                    if idx == -1:
                        break
                    findings.append(_finding(category, term, sev, lineno, idx, line, norm, nterm))
                    start = idx + len(nterm)
        # 单字"最/第一"松规则：命中且不在白名单 → warn（人判）
        sev_loose = overrides.get("绝对化用语", "block")
        sev_loose = "warn" if sev_loose == "block" else sev_loose  # 松规则一律降一档到 warn
        for term in ABSOLUTE_LOOSE:
            nterm = normalize(term)
            start = 0
            while True:
                idx = norm.find(nterm, start)
                if idx == -1:
                    break
                start = idx + len(nterm)
                if _whitelisted_at(norm, idx, term):
                    continue
                # 若该位置已被严格词表（如"最低/最佳"）覆盖，避免重复
                if any(f["line"] == lineno and f["col"] == idx for f in findings):
                    continue
                findings.append(_finding("绝对化用语(疑似)", term, sev_loose, lineno, idx, line, norm, nterm))
    return _dedup_overlapping(findings)


def _dedup_overlapping(findings):
    """同一 (line, col) 起点上多类命中（如 "100%有效" 同时命中 绝对化"100%" 与 医疗"100%有效"），
    只保留覆盖更长/更具体的那条，避免一处文本被双计。block 优先于 warn，长词优先于短词。"""
    best = {}
    order = []
    for f in findings:
        key = (f["line"], f["col"])
        cur = best.get(key)
        if cur is None:
            best[key] = f
            order.append(key)
            continue
        # 选 severity 更重 → 词更长 的那条
        sev_rank = {"block": 2, "warn": 1, "info": 0}
        better = (sev_rank.get(f["severity"], 0), len(f["term"])) > \
                 (sev_rank.get(cur["severity"], 0), len(cur["term"]))
        if better:
            best[key] = f
    return [best[k] for k in order]


def _orig_col(line, norm, idx):
    """把归一化文本里的命中下标 idx 近似映射回原始行的列号（用于人工定位）。
    逐字符重建 normalize 时保留的字符序，找到第 idx 个被保留字符在原行里的位置。"""
    kept = 0
    for orig_i, ch in enumerate(line):
        n = normalize(ch)
        if not n:  # 该字符在归一化后被去掉（空白/零宽）
            continue
        if kept >= idx:
            return orig_i
        kept += len(n)
    return min(idx, max(0, len(line) - 1))


def _finding(category, term, sev, lineno, idx, line, norm=None, nterm=None):
    """idx 是归一化文本里的列；映射回原行做 snippet。"""
    if norm is not None:
        col = _orig_col(line, norm, idx)
    else:
        col = idx
    span = len(term)
    lo, hi = max(0, col - 12), min(len(line), col + span + 12)
    snippet = ("…" if lo > 0 else "") + line[lo:hi] + ("…" if hi < len(line) else "")
    return {
        "category": category, "term": term, "severity": sev,
        "line": lineno, "col": col,
        "context": snippet, "snippet": snippet,
    }


def _extract_text_fields(node, out):
    """从 storyboard.json 这类结构里**递归**抽出所有字符串字段（frame/legal_lines/字幕/
    end_card 等），拼成可扫描的文本行，避免漏扫分镜里的违禁词。"""
    if isinstance(node, dict):
        for v in node.values():
            _extract_text_fields(v, out)
    elif isinstance(node, list):
        for v in node:
            _extract_text_fields(v, out)
    elif isinstance(node, str):
        if node.strip():
            out.append(node)


def _read_scan_text(path):
    """读文件为待扫描文本。JSON（storyboard 等）递归抽字符串字段；其余按纯文本。"""
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    if path.endswith(".json"):
        try:
            data = json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            return raw
        out = []
        _extract_text_fields(data, out)
        return "\n".join(out)
    return raw


def scan_files(paths, region="中国大陆"):
    report = {"region": region, "disabled": False, "files": [],
              "summary": {"block": 0, "warn": 0}, "findings": []}
    for path in paths:
        if not os.path.isfile(path):
            report["files"].append({"path": path, "exists": False})
            continue
        text = _read_scan_text(path)
        fnds = scan_text(text, region)
        for fnd in fnds:
            fnd["file"] = path
            report["findings"].append(fnd)
            if fnd["severity"] in report["summary"]:
                report["summary"][fnd["severity"]] += 1
        report["files"].append({"path": path, "exists": True, "hits": len(fnds)})
    return report


def disabled_report(region="关闭", reason="广告法机检已按 _设置.md 关闭（不建议用于中国大陆投放）"):
    """region=关闭：仍产出报告（ad-review 据 disabled 判定），不只 print。"""
    return {
        "region": region, "disabled": True, "reason": reason,
        "files": [], "summary": {"block": 0, "warn": 0}, "findings": [],
    }


def resolve_targets(args):
    if args.paths:
        # 单一目录 → 展开默认扫描文件
        if len(args.paths) == 1 and os.path.isdir(args.paths[0]):
            root = args.paths[0]
            return [os.path.join(root, p) for p in DEFAULT_SCAN_FILES]
        return args.paths
    return DEFAULT_SCAN_FILES


def _write_json(path, report):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="《广告法》违禁词/极限词机检")
    ap.add_argument("paths", nargs="*", help="文案文件，或单个作品根目录（自动展开常见文案文件）")
    ap.add_argument("--region", default="中国大陆", choices=["中国大陆", "海外", "关闭"])
    ap.add_argument("--json", default=None, help="把报告写到该 JSON 路径")
    args = ap.parse_args()

    if args.region == "关闭":
        report = disabled_report("关闭")
        if args.json:
            _write_json(args.json, report)
        print("[skip] 广告法机检已按 _设置.md 关闭（不建议用于中国大陆投放）——已写入 disabled 报告。")
        return

    report = scan_files(resolve_targets(args), args.region)
    if args.json:
        _write_json(args.json, report)

    b, w = report["summary"]["block"], report["summary"]["warn"]
    print(f"# 广告法机检（{args.region}）  block={b}  warn={w}")
    for fnd in report["findings"]:
        flag = "🔴" if fnd["severity"] == "block" else "🟡"
        print(f"{flag} [{fnd['category']}] “{fnd['term']}”  {os.path.basename(fnd['file'])}:{fnd['line']}  {fnd['context']}")
    if not report["findings"]:
        print("✅ 未命中违禁/极限词（仍需人工复核 claim 依据与资质）")
    print("\n说明：block=明确违禁须改；warn=高危/语境相关，结合资质与依据人判。机检是初筛，不替代法务。")
    sys.exit(1 if b > 0 else 0)


if __name__ == "__main__":
    main()
