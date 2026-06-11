#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《广告法》违禁词 / 极限词机检 —— 拍广告线相对 n2d 的核心差异化硬闸门。

扫广告文案/台词/VO/字幕，按《中华人民共和国广告法》及配套口径标出**绝对化用语**、
**虚假/误导表述**、**医疗保健极限词**、**迷信/封建**、**促销欺诈词**等违禁/高危词，
出定位报告（命中 block 即非零退出码）。**机检初筛 + 人判**：词表是确定性的，最终是否
违法仍需结合语境/资质（如已注册商标含"国"字、有依据的对比）由人复核——但默认从严。

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

# ── 词库（分类 + 严重度）。block=明确违禁；warn=高危/语境相关，需人判 ──────────
# 绝对化用语：广告法第九条明令禁止「国家级/最高级/最佳」等表示最高级、绝对化的用语。
ABSOLUTE_TERMS = [
    "国家级", "最高级", "最佳", "最好", "最大", "最强", "最优", "最新", "最先进",
    "最低", "最便宜", "最高", "最受欢迎", "第一品牌", "全国第一", "全球第一", "世界第一",
    "行业第一", "排名第一", "销量第一", "唯一", "独一无二", "顶级", "顶尖", "极致",
    "极品", "终极", "绝无仅有", "无与伦比", "史无前例", "空前绝后", "万能", "100%",
    "百分之百", "全网最低", "全场最低", "王牌", "之最", "冠军品牌", "领袖品牌", "宇宙级",
]
# 单字"第一/最X"高危打底（用边界规则减少误杀，见 _ABSOLUTE_LOOSE / WHITELIST）。
ABSOLUTE_LOOSE = ["第一", "最"]

# 医疗 / 保健 / 功效极限词：保健食品不得宣称疾病预防治疗功能；普通食品/化妆品禁医疗用语。
MEDICAL_TERMS = [
    "治愈", "根治", "痊愈", "药到病除", "包治", "speedy cure", "无毒副作用", "无副作用",
    "百分百有效", "100%有效", "疗效", "治疗", "防癌", "抗癌", "防病", "祛病", "消炎",
    "杀菌率", "抑菌率", "促进康复", "壮阳", "减肥神器", "一针见效", "一次根除", "永不复发",
    "三天见效", "七天美白", "立竿见影", "彻底解决", "纯天然无添加",
]
# 虚假 / 误导 / 夸大：含未证实承诺、绝对承诺。
FALSE_TERMS = [
    "稳赚不赔", "零风险", "无风险", "保本保息", "包过", "包就业", "包治百病",
    "永久", "终身免费", "绝对安全", "绝对有效", "百分百安全", "假一赔万",
]
# 迷信 / 封建：广告不得含妨碍社会公共秩序或违背社会良好风尚的内容。
SUPERSTITION_TERMS = ["开光", "辟邪", "转运", "招财进宝符", "改运", "风水宝地保佑"]
# 促销欺诈 / 时限欺诈：虚构原价、虚假优惠、诱导紧迫。
PROMO_TERMS = ["全网最低价", "史上最低价", "原价虚构", "仅此一天", "最后一天", "清仓甩卖最后机会"]

# 白名单：这些"最X/第一"是时间/序数/固定词，非最高级广告承诺，降噪不误杀。
WHITELIST = [
    "最后", "最初", "最近", "最终", "最早", "第一时间", "第一步", "第一次",
    "第一人称", "第一章", "第一集", "第一季", "最好不过",
]

CATEGORIES = [
    ("绝对化用语", ABSOLUTE_TERMS, "block"),
    ("医疗保健极限词", MEDICAL_TERMS, "block"),
    ("虚假/绝对承诺", FALSE_TERMS, "block"),
    ("迷信封建", SUPERSTITION_TERMS, "block"),
    ("促销欺诈", PROMO_TERMS, "warn"),
]

# 海外口径只保留普适性强的（虚假/绝对承诺、医疗夸大），绝对化用语按平台政策松一档→warn。
REGION_OVERRIDES = {
    "海外": {"绝对化用语": "warn", "促销欺诈": "warn"},
}

DEFAULT_SCAN_FILES = [
    "脚本/广告脚本.md", "脚本/voiceover.txt", "脚本/字幕_zh.srt",
    "创意/创意脚本.md", "创意/concept.md",
]


def _whitelisted_at(text, idx, term):
    """命中 ABSOLUTE_LOOSE（最/第一）时，若落在白名单复合词里则跳过。"""
    for w in WHITELIST:
        pos = text.find(w)
        while pos != -1:
            if pos <= idx < pos + len(w):
                return True
            pos = text.find(w, pos + 1)
    return False


def scan_text(text, region="中国大陆"):
    """返回 findings: [{category, term, severity, line, col, context}]。"""
    findings = []
    overrides = REGION_OVERRIDES.get(region, {})
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        for category, terms, base_sev in CATEGORIES:
            sev = overrides.get(category, base_sev)
            for term in terms:
                start = 0
                while True:
                    idx = line.find(term, start)
                    if idx == -1:
                        break
                    findings.append(_finding(category, term, sev, lineno, idx, line))
                    start = idx + len(term)
        # 单字"最/第一"松规则：命中且不在白名单 → warn（人判）
        sev_loose = overrides.get("绝对化用语", "block")
        sev_loose = "warn" if sev_loose == "block" else sev_loose  # 松规则一律降一档到 warn
        for term in ABSOLUTE_LOOSE:
            start = 0
            while True:
                idx = line.find(term, start)
                if idx == -1:
                    break
                start = idx + len(term)
                if _whitelisted_at(line, idx, term):
                    continue
                # 若已被严格词表（如"最低/最佳"）覆盖，避免重复
                if any(f["line"] == lineno and f["col"] == idx for f in findings):
                    continue
                findings.append(_finding("绝对化用语(疑似)", term, sev_loose, lineno, idx, line))
    return findings


def _finding(category, term, sev, lineno, col, line):
    lo, hi = max(0, col - 12), min(len(line), col + len(term) + 12)
    return {
        "category": category, "term": term, "severity": sev,
        "line": lineno, "col": col, "context": ("…" if lo > 0 else "") + line[lo:hi] + ("…" if hi < len(line) else ""),
    }


def scan_files(paths, region="中国大陆"):
    report = {"region": region, "files": [], "summary": {"block": 0, "warn": 0}, "findings": []}
    for path in paths:
        if not os.path.isfile(path):
            report["files"].append({"path": path, "exists": False})
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        fnds = scan_text(text, region)
        for fnd in fnds:
            fnd["file"] = path
            report["findings"].append(fnd)
            report["summary"][fnd["severity"]] += 1
        report["files"].append({"path": path, "exists": True, "hits": len(fnds)})
    return report


def resolve_targets(args):
    if args.paths:
        # 单一目录 → 展开默认扫描文件
        if len(args.paths) == 1 and os.path.isdir(args.paths[0]):
            root = args.paths[0]
            return [os.path.join(root, p) for p in DEFAULT_SCAN_FILES]
        return args.paths
    return DEFAULT_SCAN_FILES


def main():
    ap = argparse.ArgumentParser(description="《广告法》违禁词/极限词机检")
    ap.add_argument("paths", nargs="*", help="文案文件，或单个作品根目录（自动展开常见文案文件）")
    ap.add_argument("--region", default="中国大陆", choices=["中国大陆", "海外", "关闭"])
    ap.add_argument("--json", default=None, help="把报告写到该 JSON 路径")
    args = ap.parse_args()

    if args.region == "关闭":
        print("[skip] 广告法机检已按 _设置.md 关闭（不建议用于中国大陆投放）")
        return

    report = scan_files(resolve_targets(args), args.region)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

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
