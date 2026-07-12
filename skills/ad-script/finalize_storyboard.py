#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分镜定稿闸门（配音后回跑）：用 配音/时长清单.json 的实测 VO 时长对账 storyboard.json，
算每镜/总时长，校验是否贴合主片目标时长（如 30s），查强制项落镜，标接缝缺尾帧。
自包含纯标准库 + 单测。

广告用 VO 实测时长驱动镜头时长；广告**总时长是硬约束**（30s 就得 30s，超了投
不出去），所以这里多一条「总时长 vs 主片目标」对账，超/欠都报。

广告专有硬闸：
- **占位 VO 默认硬拦**：时长清单.json 顶层 `has_placeholder`（= 任一句占位）是单一真值源；
  占位时长是估算值，定稿后会污染镜头时长 → 出视频按错时长生成 → 返工。默认 sys.exit 非零，
  仅 `--allow-placeholder` / 环境变量 `FINALIZE_ALLOW_PLACEHOLDER=1` 可放行 rough preview。
- **强制项落镜**：brief `需求/brief.json` 的 mandatories（logo/slogan/法律声明/CTA）必须在
  storyboard 有对应镜头/字幕/legal_lines，缺一即 block。
- **单镜 VO 溢出**：单个镜头的 VO 秒数超过该镜 duration（旁白会被截断）也单独报，不只看总时长。

用法：
    python3 finalize_storyboard.py <作品根> --master 30s --json 脚本/镜头时长.json [--allow-placeholder]
"""
import argparse
import json
import os
import re
import sys


def parse_seconds(label):
    """'30s'/'15'/'1:30' → float 秒。"""
    s = str(label).strip().lower().replace("s", "")
    if ":" in s:
        m, sec = s.split(":", 1)
        return int(m) * 60 + float(sec)
    return float(s)


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_text(path):
    """读纯文本文件（缺失/不可读 → 空串）；供 USP 宣称扫描读 广告脚本.md / voiceover.txt。"""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def has_placeholder(duration_list):
    """占位单一真值源：优先取时长清单**顶层** `has_placeholder`（其他 skill 写入的权威值），
    缺失时回退按逐句 占位/placeholder 推断。"""
    if isinstance(duration_list, dict) and "has_placeholder" in duration_list:
        return bool(duration_list["has_placeholder"])
    items = _lines(duration_list)
    return any(it.get("占位") or it.get("placeholder") for it in items)


def _lines(duration_list):
    if isinstance(duration_list, dict):
        return duration_list.get("lines", []) or []
    return duration_list or []


def _line_seconds(it):
    return float(it.get("seconds", it.get("时长", it.get("duration", 0))) or 0)


def vo_total(duration_list):
    """时长清单.json（{lines:[..]} 或 [..]）→ 总 VO 秒数 + 是否有占位（顶层优先）。"""
    items = _lines(duration_list)
    total = 0.0
    for it in items:
        total += _line_seconds(it)
        total += float(it.get("gap_after", 0) or 0)
    return round(total, 3), has_placeholder(duration_list)


def shot_durations(storyboard):
    """storyboard.json → [(shot_id, duration)]。容忍 shots/clips 两种键。"""
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    out = []
    for i, sh in enumerate(shots, 1):
        sid = sh.get("shot_id") or sh.get("clip_id") or f"镜头{i}"
        dur = float(sh.get("duration", sh.get("时长", 0)) or 0)
        out.append((sid, dur))
    return out


def _shot_vo_seconds(storyboard, duration_list):
    """聚合每镜 VO 秒数：storyboard 每镜 vo_lines=[idx..] 指向时长清单的句子下标（1-based）。
    返回 {shot_id: vo_seconds}（仅对显式声明了 vo_lines 的镜头）。"""
    items = _lines(duration_list)
    # idx 字段权威；否则用清单顺序（1-based）兜底
    by_idx = {}
    for pos, it in enumerate(items, 1):
        key = it.get("idx", pos)
        by_idx[key] = _line_seconds(it)
    out = {}
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    for i, sh in enumerate(shots, 1):
        sid = sh.get("shot_id") or sh.get("clip_id") or f"镜头{i}"
        vo_lines = sh.get("vo_lines")
        if not vo_lines:
            continue
        sec = sum(by_idx.get(n, 0.0) for n in vo_lines)
        out[sid] = round(sec, 3)
    return out


def fit_check(master_seconds, sb_total, vo_seconds, tol=None):
    """对账总时长。返回 findings 列表（block/warn）。

    tol 随主片长度缩放（默认 max(0.5, master*0.03)），不再固定 0.5——长片绝对误差容忍要更大。
    master_seconds 为 None（未传 --master 且 _设置.md 无主片时长）时不硬约束总时长，但调用方
    会改发一条 warn（见 main），这里只跳过总时长比对。"""
    findings = []
    if master_seconds:
        if tol is None:
            tol = max(0.5, master_seconds * 0.03)
        if abs(sb_total - master_seconds) > tol:
            sev = "block" if abs(sb_total - master_seconds) > max(1.0, master_seconds * 0.1) else "warn"
            findings.append({
                "severity": sev, "kind": "master_duration_mismatch",
                "msg": f"分镜总时长 {sb_total:.2f}s ≠ 主片目标 {master_seconds:.0f}s（差 {sb_total - master_seconds:+.2f}s，容差 {tol:.2f}s）",
            })
    base_tol = tol if tol is not None else 0.5
    if vo_seconds and sb_total + base_tol < vo_seconds:
        findings.append({
            "severity": "block", "kind": "vo_overflow",
            "msg": f"VO 实测 {vo_seconds:.2f}s 超过分镜总时长 {sb_total:.2f}s，旁白会被截断",
        })
    return findings


def shot_vo_overflow_check(storyboard, duration_list, tol=0.3):
    """单镜 VO 溢出：某镜的 VO 秒数 > 该镜 duration → 该镜旁白会被截断（block）。"""
    findings = []
    durs = dict(shot_durations(storyboard))
    vo_by_shot = _shot_vo_seconds(storyboard, duration_list)
    for sid, vo_sec in vo_by_shot.items():
        dur = durs.get(sid, 0.0)
        if dur and vo_sec > dur + tol:
            findings.append({
                "severity": "block", "kind": "shot_vo_overflow",
                "msg": f"镜头 {sid} VO {vo_sec:.2f}s 超过该镜时长 {dur:.2f}s，旁白会被截断",
            })
    return findings


def _collect_storyboard_text(storyboard):
    """把 storyboard 里所有可读文本（frame/legal_lines/字幕/end_card/section…）拼成一坨，
    供强制项落镜的"是否被某镜覆盖"判定。"""
    parts = []

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, str):
            parts.append(node)
    walk(storyboard)
    return "\n".join(parts)


def _has_asset(storyboard, needle):
    """强制项命中：某镜 assets 键、legal_lines、或任意文本字段提到该 needle。"""
    text = _collect_storyboard_text(storyboard)
    if needle and needle in text:
        return True
    # assets 键里出现（如 PROD_logo / CHAR_..），按子串宽松匹配
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    for sh in shots:
        assets = sh.get("assets") or {}
        for k in assets:
            if needle and (needle in k or k in needle):
                return True
    return False


# brief mandatories → 落镜判据关键字（按语义找"有没有任意一镜承载它"）。
_FORCED_KEYS = {
    "logo": ("logo", "LOGO", "Logo", "品牌标"),
    "slogan": ("slogan", "Slogan", "口号"),
    "legal_lines": ("legal_lines",),  # 特判：看 storyboard 是否有非空 legal_lines
    "cta": ("cta", "CTA", "行动", "立即", "扫码", "进店", "下单", "购买", "关注"),
}


def forced_asset_check(brief, storyboard):
    """读 brief mandatories（logo/slogan/法律声明/CTA），逐项确认 storyboard 有对应镜头/字幕/
    legal_lines；缺一即 block。brief 为空或 mandatories 缺失时跳过（不是本步该拦的）。"""
    findings = []
    mand = (brief or {}).get("mandatories") or {}
    if not isinstance(mand, dict):
        return findings
    label = {"logo": "logo", "slogan": "slogan", "legal_lines": "法律声明", "cta": "CTA"}
    for key, value in mand.items():
        if not value:  # 该强制项 brief 未要求/标"待补" → 不拦
            continue
        if isinstance(value, str) and value.strip().lower() in ("", "待补", "tbd"):
            continue
        covered = False
        if key == "legal_lines":
            # storyboard 任意镜有非空 legal_lines 即算覆盖
            shots = storyboard.get("shots") or storyboard.get("clips") or []
            covered = any((sh.get("legal_lines")) for sh in shots) or _has_asset(storyboard, "legal_lines")
            # 也接受 brief 给的具体法律声明文本被任意字段引用
            if not covered and isinstance(value, (list, tuple)):
                text = _collect_storyboard_text(storyboard)
                covered = any(str(v) and str(v) in text for v in value)
        else:
            needles = _FORCED_KEYS.get(key, (key,))
            covered = any(_has_asset(storyboard, n) for n in needles)
            # brief 给了具体文案（如具体 slogan 文本）也算命中
            if not covered:
                text = _collect_storyboard_text(storyboard)
                vals = value if isinstance(value, (list, tuple)) else [value]
                covered = any(str(v) and str(v) in text for v in vals)
        if not covered:
            findings.append({
                "severity": "block", "kind": "forced_asset_missing",
                "msg": f"brief 强制项「{label.get(key, key)}」在分镜里没有对应镜头/字幕/legal_lines",
            })
    return findings


# ── USP↔免责联动：做了受规管的功效/收益宣称，就必须带对应免责声明 ───────────────
# claim 在 脚本/VO/分镜 任意处命中 → 分镜 legal_lines/字幕 必须有对应免责之一，否则报。
# 金融/加盟/保健食品 的免责是**法定强制**→ block；功效类（化妆品/减肥/教育）平台强烈要求但
# 表述多变、依资质而定 → warn（人判补全，不硬拦误杀）。claim 词刻意避开 ad_law_check 已 block 的
# 违禁词（如祛斑/生发/保收益），两者互补不重叠：一个拦「不能说的词」，一个拦「说了就得配免责」。
CLAIM_DISCLAIMER_RULES = [
    {"label": "金融理财收益", "severity": "block",
     "claims": ["年化", "理财", "收益率", "投资回报", "私募", "基金定投", "稳健增值", "躺赚"],
     "disclaimers": ["投资有风险", "入市需谨慎", "市场有风险", "过往业绩", "不代表未来",
                     "理财非存款", "产品有风险", "谨慎投资"],
     "fix": "金融/理财宣称须带风险提示——在 legal_lines/字幕补「投资有风险，入市需谨慎」（或「过往业绩不代表未来表现」）。"},
    {"label": "加盟招商", "severity": "block",
     "claims": ["加盟", "招商", "0元开店", "零元开店", "小本创业", "连锁加盟", "合伙人计划"],
     "disclaimers": ["加盟有风险", "投资需谨慎", "投资有风险", "经营需谨慎", "谨慎投资"],
     "fix": "加盟/招商宣称须带风险提示——在 legal_lines/字幕补「加盟有风险，投资需谨慎」。"},
    {"label": "保健食品", "severity": "block",
     "claims": ["保健食品", "膳食补充剂", "增强免疫力", "改善睡眠", "缓解疲劳", "辅助降血脂"],
     "disclaimers": ["不能代替药物", "不能替代药物", "不是药物", "保健食品不能"],
     "fix": "保健食品须声明「本品不能代替药物」（蓝帽子标识声明）——在 legal_lines/字幕补上。"},
    {"label": "化妆品功效", "severity": "warn",
     "claims": ["美白", "祛痘", "淡化细纹", "抗皱", "紧致提拉", "去黑头", "淡纹", "去痘印"],
     "disclaimers": ["效果因人而异", "因人而异", "个体差异", "效果视个人"],
     "fix": "功效宣称建议带「效果因人而异」并避免保证性承诺；做效果展示需标注「演示/对比图，效果因人而异」。"},
    {"label": "减肥瘦身", "severity": "warn",
     "claims": ["减肥", "燃脂", "瘦下来", "月瘦", "暴瘦"],
     "disclaimers": ["效果因人而异", "因人而异", "个体差异", "需配合"],
     "fix": "减肥宣称建议带「效果因人而异，需配合饮食运动」，避免保证性减重承诺。"},
    {"label": "教育培训效果", "severity": "warn",
     "claims": ["提分", "提升成绩", "通过率", "上岸", "快速提升", "学完就会"],
     "disclaimers": ["效果因人而异", "因人而异", "个体差异", "学习效果"],
     "fix": "培训效果宣称建议带「学习效果因人而异」；升学率/通过率保证已被广告法机检拦，删除即可。"},
]

# 引证/免责呈现：字段完整是确定性交接闸；数值只作为明确标注的内部可读性快筛，
# 不是伪称法定字号/阅读速度。最终像素与实际版位仍由 delivery + 具名人审签收。
DISCLOSURE_HOUSE_PROFILE = {
    "max_cjk_chars_per_second_warn": 12.0,
    "min_font_height_ratio_warn": 0.03,
    "authority": "house_legibility_screen",
    "source": "内部快筛；法律硬要求来自适用辖区，最终以实际成片/版位人审为准",
}
CITED_EVIDENCE_TYPES = {
    "test_measurement", "statistics_survey", "scientific_literature", "comparison",
}
DISCLOSURE_RELATIONSHIPS = {"same_screen", "immediate_adjacent"}
DISCLOSURE_PROMINENCE = {"equivalent", "sufficient", "audio_read"}


def _usp_norm(text):
    """轻归一化：去全部空白（防「效果 因人而异」被空格隔开漏判）。文案非对抗，无需 NFKC。"""
    return re.sub(r"\s+", "", str(text or ""))


def usp_disclaimer_check(brief, storyboard, claim_text=""):
    """USP↔免责联动闸门：受规管的功效/收益宣称必须带对应免责声明，否则报（金融/加盟/保健=block，
    功效类=warn）。claim 扫 脚本+VO+分镜；免责须落在「会播出」的分镜 legal_lines/字幕，或 brief 已声明
    的 legal_lines（经 forced_asset_check 保证落镜）。每条命中附 suggestion（该补哪句免责）。"""
    sb_text = _collect_storyboard_text(storyboard)
    claim_corpus = _usp_norm(claim_text) + _usp_norm(sb_text)
    mand = (brief or {}).get("mandatories") or {}
    legal_decl = mand.get("legal_lines") if isinstance(mand, dict) else None
    if isinstance(legal_decl, (list, tuple)):
        legal_decl_text = " ".join(str(v) for v in legal_decl)
    else:
        legal_decl_text = str(legal_decl or "")
    disc_corpus = _usp_norm(sb_text) + _usp_norm(legal_decl_text)
    findings = []
    for rule in CLAIM_DISCLAIMER_RULES:
        hit = next((c for c in rule["claims"] if _usp_norm(c) in claim_corpus), None)
        if not hit:
            continue
        if any(_usp_norm(d) in disc_corpus for d in rule["disclaimers"]):
            continue  # 已带对应免责 → 合规，放行
        findings.append({
            "severity": rule["severity"], "kind": "usp_disclaimer_missing",
            "msg": f"宣称「{rule['label']}」（命中「{hit}」）但分镜/法律声明里缺对应免责声明",
            "suggestion": rule["fix"],
        })
    return findings


def _claim_id(claim, pos):
    return str((claim or {}).get("id") or f"claim_{pos:02d}").strip()


def _claim_ids_from_shot(shot):
    raw = shot.get("claim_ids") or []
    if isinstance(raw, str):
        raw = [raw]
    return {str(v).strip() for v in raw if str(v).strip()}


def _disclosures_from_shot(shot):
    raw = shot.get("disclosures") or []
    if isinstance(raw, dict):
        raw = [raw]
    return [row for row in raw if isinstance(row, dict)]


def _visible_chars(value):
    return len(re.sub(r"[\s\W_]+", "", str(value or ""), flags=re.UNICODE))


def claim_presentation_check(brief, storyboard):
    """Validate claim→shot→disclosure linkage and planned legibility.

    The 2026 SAMR cited-content guidance requires clear source, conditions,
    scope and validity where applicable and targets tiny-print disclaimers.
    This function machine-checks structure.  CPS/font ratios are house WARNs,
    while missing linkage/source/conditions is a deterministic BLOCK.
    """
    raw_claims = (brief or {}).get("claims") or []
    if isinstance(raw_claims, dict):
        raw_claims = [raw_claims]
    claims = [(pos, row) for pos, row in enumerate(raw_claims, 1) if isinstance(row, dict)]
    if not claims:
        return []
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    findings = []
    for pos, claim in claims:
        cid = _claim_id(claim, pos)
        claim_positions = [i for i, shot in enumerate(shots) if cid in _claim_ids_from_shot(shot)]
        if not claim_positions:
            findings.append({
                "severity": "block", "kind": "claim_shot_binding_missing", "claim_id": cid,
                "msg": f"claim {cid} 未绑定到任何 storyboard.shots[].claim_ids；无法证明哪一镜做了该宣称",
            })
            continue
        candidates = []
        for i, shot in enumerate(shots):
            for row in _disclosures_from_shot(shot):
                if str(row.get("claim_id") or "").strip() == cid:
                    candidates.append((i, shot, row))
        if not candidates:
            findings.append({
                "severity": "block", "kind": "claim_disclosure_missing", "claim_id": cid,
                "msg": f"claim {cid} 缺结构化 disclosures[]；普通 legal_lines 不能证明来源/条件/范围的呈现关系",
            })
            continue
        accepted = False
        candidate_errors = []
        citation_used = bool(claim.get("citation_used") or str(claim.get("evidence_type") or "").lower() in CITED_EVIDENCE_TYPES)
        for shot_index, shot, row in candidates:
            missing = []
            for key in ("text", "duration_sec", "font_height_ratio", "contrast_review",
                        "safe_zone_review", "relationship", "relative_prominence"):
                if row.get(key) in (None, "", []):
                    missing.append(key)
            if citation_used and not str(row.get("source_text") or "").strip():
                missing.append("source_text")
            relationship = str(row.get("relationship") or "").strip()
            if relationship and relationship not in DISCLOSURE_RELATIONSHIPS:
                missing.append("relationship_valid")
            prominence = str(row.get("relative_prominence") or "").strip()
            if prominence and prominence not in DISCLOSURE_PROMINENCE:
                missing.append("relative_prominence_valid")
            if str(row.get("contrast_review") or "").lower() != "pass":
                missing.append("contrast_review_pass")
            if str(row.get("safe_zone_review") or "").lower() != "pass":
                missing.append("safe_zone_review_pass")
            if relationship == "same_screen" and shot_index not in claim_positions:
                missing.append("same_screen_relation")
            if relationship == "immediate_adjacent" and not any(abs(shot_index - p) <= 1 for p in claim_positions):
                missing.append("immediate_adjacent_relation")
            try:
                duration = float(row.get("duration_sec") or 0)
                ratio = float(row.get("font_height_ratio") or 0)
            except (TypeError, ValueError):
                duration = ratio = 0.0
                missing.append("numeric_presentation_fields")
            if duration <= 0 or ratio <= 0:
                missing.append("positive_presentation_fields")
            if missing:
                candidate_errors.append(sorted(set(missing)))
                continue
            accepted = True
            chars = _visible_chars(row.get("text")) + _visible_chars(row.get("source_text"))
            cps = chars / duration if duration else 999.0
            if cps > DISCLOSURE_HOUSE_PROFILE["max_cjk_chars_per_second_warn"]:
                findings.append({
                    "severity": "warn", "kind": "disclosure_reading_speed_house_warn", "claim_id": cid,
                    "msg": f"claim {cid} 披露约 {cps:.1f} 字符/秒，超过内部快筛 "
                           f"{DISCLOSURE_HOUSE_PROFILE['max_cjk_chars_per_second_warn']:.0f}；请实机审读（非法律数值线）",
                })
            if ratio < DISCLOSURE_HOUSE_PROFILE["min_font_height_ratio_warn"]:
                findings.append({
                    "severity": "warn", "kind": "disclosure_font_house_warn", "claim_id": cid,
                    "msg": f"claim {cid} 计划字高占画面 {ratio:.3f}，低于内部快筛 "
                           f"{DISCLOSURE_HOUSE_PROFILE['min_font_height_ratio_warn']:.3f}；防止“大字吸睛、小字免责”",
                })
            break
        if not accepted:
            missing = sorted({v for group in candidate_errors for v in group})
            findings.append({
                "severity": "block", "kind": "claim_disclosure_contract_invalid", "claim_id": cid,
                "msg": f"claim {cid} 披露呈现合同不完整/关系不成立：{', '.join(missing)}",
            })
    return findings


def seam_check(storyboard):
    """逐接缝查：标了 need_end_frame 但无尾帧约定 → warn。"""
    findings = []
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    for i, sh in enumerate(shots, 1):
        cont = sh.get("continuity") or {}
        if cont.get("need_end_frame") and not cont.get("transition"):
            findings.append({"severity": "warn", "kind": "seam_missing_transition",
                             "msg": f"镜头{i} 标了需要尾帧但缺 transition 类型"})
    return findings


def _settings_master_seconds(root):
    """--master 缺省时，尝试从 <root>/_设置.md 读「主片时长」选择点（纯文本宽松解析）。"""
    p = os.path.join(root, "_设置.md")
    if not os.path.isfile(p):
        return None
    import re
    with open(p, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"主片时长[^\n]*?(\d+(?:\.\d+)?)\s*s", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def main():
    ap = argparse.ArgumentParser(description="拍广告分镜定稿闸门（VO 时长 × 主片目标 × 强制项落镜对账）")
    ap.add_argument("project_root")
    ap.add_argument("--master", default=None, help="主片目标时长，如 30s")
    ap.add_argument("--json", default=None, help="把镜头时长汇总写到该路径")
    ap.add_argument("--allow-placeholder", action="store_true",
                    help="放行占位 VO 定稿（rough preview 用，产物不可用于正式出视频）")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)

    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {}) or {}
    dl = load_json(os.path.join(root, "配音", "时长清单.json"), [])
    brief = load_json(os.path.join(root, "需求", "brief.json"), {}) or {}
    vo_sec, placeholder = vo_total(dl)
    shots = shot_durations(sb)
    sb_total = round(sum(d for _, d in shots), 3)

    master_sec = parse_seconds(args.master) if args.master else _settings_master_seconds(root)
    tol = max(0.5, master_sec * 0.03) if master_sec else None

    allow_ph = args.allow_placeholder or os.environ.get("FINALIZE_ALLOW_PLACEHOLDER", "") == "1"

    # USP↔免责联动：扫脚本+VO 找受规管宣称，分镜缺对应免责则报（金融/加盟/保健=block，功效类=warn）。
    claim_src = "\n".join(_read_text(os.path.join(root, "脚本", n))
                          for n in ("广告脚本.md", "voiceover.txt"))

    findings = fit_check(master_sec, sb_total, vo_sec, tol)
    findings += shot_vo_overflow_check(sb, dl)
    findings += forced_asset_check(brief, sb)
    findings += usp_disclaimer_check(brief, sb, claim_src)
    findings += claim_presentation_check(brief, sb)
    findings += seam_check(sb)

    # 主片时长缺失：不静默放过整条总时长约束，至少 warn。
    if not master_sec:
        findings.append({
            "severity": "warn", "kind": "master_unspecified",
            "msg": "未提供 --master 且 _设置.md 无「主片时长」，跳过总时长硬约束——广告总时长是硬约束，请补主片时长后复跑",
        })

    # 占位 VO 默认硬拦（顶层 has_placeholder 单一真值源），--allow-placeholder 放行。
    if placeholder and not allow_ph:
        findings.append({
            "severity": "block", "kind": "placeholder_vo",
            "msg": "配音仍是占位音色（say 应急/estimate）；占位时长是估算值，定稿后会锁进镜头时长 → 出视频按错时长返工。"
                   "换真实 VO 重跑，或 --allow-placeholder / FINALIZE_ALLOW_PLACEHOLDER=1 仅做 rough preview。",
        })

    payload = {
        "schema_version": 2, "kind": "ad_storyboard_finalize",
        "master_seconds": master_sec, "storyboard_total": sb_total,
        "vo_seconds": vo_sec, "vo_placeholder": placeholder,
        "allow_placeholder": allow_ph,
        "shots": [{"shot_id": s, "duration": d} for s, d in shots],
        "standards": {
            "cited_content": {
                "authority": "official_regulation_guidance", "checked_at": "2026-07-11",
                "source": "https://policy.mofcom.gov.cn/claw/clawContent.shtml?id=106104",
                "scope": "广告引证内容来源/条件/适用范围/有效期及显著呈现",
            },
            "disclosure_legibility": DISCLOSURE_HOUSE_PROFILE,
        },
        "findings": findings,
    }
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"# 分镜定稿对账  分镜总时长={sb_total:.2f}s  VO={vo_sec:.2f}s"
          + (f"  主片目标={master_sec:.0f}s" if master_sec else "  主片目标=未设")
          + ("  ⏳占位VO" if placeholder else ""))
    for f in findings:
        print(("🔴" if f["severity"] == "block" else "🟡") + f" {f['msg']}")
        if f.get("suggestion"):
            print(f"    ↳ 改法：{f['suggestion']}")
    if not findings:
        print("✅ 时长对账通过")
    if placeholder and allow_ph:
        print("⚠️ 已放行占位 VO（rough preview）；正式定稿前需用真 VO 复跑（音画才准）")
    sys.exit(1 if any(f["severity"] == "block" for f in findings) else 0)


if __name__ == "__main__":
    main()
