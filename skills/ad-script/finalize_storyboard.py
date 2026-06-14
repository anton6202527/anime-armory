#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分镜定稿闸门（配音后回跑）：用 配音/时长清单.json 的实测 VO 时长对账 storyboard.json，
算每镜/总时长，校验是否贴合主片目标时长（如 30s），查强制项落镜，标接缝缺尾帧。
自包含纯标准库 + 单测。

广告与 n2d 同构：VO 实测时长驱动镜头时长；但广告**总时长是硬约束**（30s 就得 30s，超了投
不出去），所以这里多一条「总时长 vs 主片目标」对账，超/欠都报。

广告专有硬闸（相对 n2d）：
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

    findings = fit_check(master_sec, sb_total, vo_sec, tol)
    findings += shot_vo_overflow_check(sb, dl)
    findings += forced_asset_check(brief, sb)
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
        "schema_version": 1, "kind": "ad_storyboard_finalize",
        "master_seconds": master_sec, "storyboard_total": sb_total,
        "vo_seconds": vo_sec, "vo_placeholder": placeholder,
        "allow_placeholder": allow_ph,
        "shots": [{"shot_id": s, "duration": d} for s, d in shots],
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
    if not findings:
        print("✅ 时长对账通过")
    if placeholder and allow_ph:
        print("⚠️ 已放行占位 VO（rough preview）；正式定稿前需用真 VO 复跑（音画才准）")
    sys.exit(1 if any(f["severity"] == "block" for f in findings) else 0)


if __name__ == "__main__":
    main()
