#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建【改写】项目骨架；docx → txt 抽取；判版权。
与 novel-spinoff 的 init 镜像：**不扫锚点**，改为生成 改动spec + 新设定圣经 骨架。

用法:
    python3 init_project.py <原作路径> \\
        --rewrite-type "<一句话改动方向>" \\
        --scale short|medium|long|微短剧|漫剧 \\
        [--target-chapters N]  [--person first|third-limited] \\
        [--out <输出根>] [--outputs txt,docx,outline] \\
        [--target-platform 跨平台] [--i-have-rights]

依赖: python-docx（仅当原作是 .docx 时）
"""
import argparse
import json
import os
import shutil
import sys
from datetime import date

# Standardized imports from novel/_lib
LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from novel_contract import (base_meta, build_progress_markdown, routing_stages,
                            SCALE_CHOICES, scale_profile, detect_rights_status,
                            docx_to_txt, write_project_settings, demo_chapters_for,
                            normalize_scale, parse_outputs, parse_regions, rights_metadata,
                            SCALE_PROFILES, NOVEL_DRAFT_MODES, CHAPTER_GRANULARITY,
                            DRAFT_WORKFLOWS, AI_TEXT_USAGE_MODES,
                            infer_novel_purpose, normalize_novel_purpose,
                            resolve_novel_draft_mode, resolve_novel_draft_workflow)
from source_language import classify_register, scaffold as source_scaffold

SCALE_PROFILE = SCALE_PROFILES  # scale-band 契约：test_scale_contract 校验其与规模档一致


def load_score_report(path):
    """读 novel-score 的 评分/score_report.json。容错：任何问题只告警不阻断 init
    （评分是改写的【建议输入】，不是前置门）。返回 dict 或 None。"""
    try:
        with open(path, encoding="utf-8") as f:
            report = json.load(f)
    except FileNotFoundError:
        print(f"[warn] --score-source 找不到：{path}（跳过评分诊断，改动spec 用空骨架）", file=sys.stderr)
        return None
    except (json.JSONDecodeError, OSError) as e:
        print(f"[warn] --score-source 读取失败：{e}（跳过评分诊断）", file=sys.stderr)
        return None
    if report.get("kind") != "novel_score_report":
        print(f"[warn] --score-source 不是 novel-score 报告（kind={report.get('kind')}），跳过诊断",
              file=sys.stderr)
        return None
    return report


def build_score_diagnosis(report):
    """把 score_report.json 的弱项/扣分/结论压成一段【建议·待对账】，注入 改动spec ② 栏。
    诊断是参考不是指令——与用户要求冲突时以用户要求为准。"""
    verdict = report.get("verdict", "?")
    total = report.get("total_score")
    tier = report.get("tier", "?")
    roi = report.get("rewrite_roi", "?")
    gen = report.get("generated_at", "?")
    weak = sorted((s for s in report.get("scores", []) if s.get("raw_score", 10) < 6),
                  key=lambda s: s.get("raw_score", 10))
    deductions = report.get("deductions", [])

    total_s = f"{total:.0f}" if isinstance(total, (int, float)) else "?"
    lines = [
        f"> ⟦评分诊断·建议待对账⟧ 来源 评分/score_report.json（{gen}）"
        f"｜总分 {total_s}（{tier}）｜结论 **{verdict}**｜改写ROI {roi}",
        "> 以下是机器评分点出的弱项，**仅供改写参考**：与用户要求冲突时以用户要求为准，"
        "采纳的并入下方对应栏、保留的请显式标注。",
    ]
    if str(verdict) == "弃稿重立":
        lines.append("> ⚠ 评分判「弃稿重立」：改写未必是对的工具——先与用户确认是否该走 novel-create 另起。")
    if weak:
        lines += [">", "> **建议优先改的弱项：**"]
        for s in weak:
            label = s.get("dimension_label") or s.get("dimension")
            hint = (s.get("improve_by") or s.get("comment") or "").strip()
            lines.append(f"> - {label}（{s.get('raw_score')}/10）{(' → ' + hint) if hint else ''}")
    if deductions:
        lines += [">", "> **触发的扣分雷点（改写应规避）：**"]
        for d in deductions:
            lines.append(f"> - {d.get('item', '?')}（{d.get('points')}）：{(d.get('reason') or '').strip()}")
    return "\n".join(lines) + "\n\n"


def build_change_spec(source_title, diagnosis=""):
    return f"""# 改动spec — 《{source_title}》→《<新书名待定>》

> 这部改写的"宪法"。动笔前与用户敲定。每条要具体可判定，别写空话。

## 一句话改动方向
（把"X 的故事"改成"Y 的故事"——一句话说清灵魂）

## ① 保留的内核（魂，不许丢）
- 主角人设内核：
- 情感主线：
- 世界观底色 / 基调：
- 必须保留的标志性桥段/意象：

## ② 改的部分（事件 / 设定 / 结局）
{diagnosis}- 改主线走向：原作是… → 改成…
- 改/删的事件：
- 改的设定（改了的要在 新设定.md 登记新值）：
- 改的结局：

## ③ 加的新料（清单；详细体系进 新设定.md）
- 新金手指/系统：
- 新势力/组织：
- 新人物：
- 新地理/秘境/物品：
"""


def build_new_settings(source_title):
    return f"""# 新设定圣经 — 《<新书名待定>》（改写自《{source_title}》）

> 本作相对原作【新增/改写】的所有设定。逐章写作硬约束，回扫逐条核。
> 与原作旧设定冲突的以本表为准；本表内部不许自相矛盾。新金手指必须有代价。

## 体系（金手指/力量/修炼）
### <名称>
- 是什么 / 规则边界 / **代价限制** / 首现章·复用 / 不可违反点

## 势力 / 组织
### <名称>　立场·目的·与主角关系·首现章

## 新人物
### <名称>　身份·外貌锚定·性格·动机·说话习惯·首现章·复用范围

## 地理 / 秘境 / 物品
### <名称>　描述·规则·首现章

## 改写后的旧设定（覆盖原作）
| 原作设定 | 改成 | 影响范围 |
|---|---|---|
"""


def build_character_card(source_title):
    return f"""# 角色卡 — 主角（改写自《{source_title}》）

> 第 3 步填。改写常重塑主角——内核可承原作（见 改动spec ①），事件/能力按新设定。

## 姓名 / 年龄 / 性别
## 外观（锚定）
## 出身
## 能力体系（依 新设定.md）
## 性格底色（保留的内核 + 新增）
## 动机 / 心结 / 渴望
## 关键关系
## 说话习惯
"""


def build_worldview(source_title):
    return f"""# 世界观 — 《<新书名待定>》（改写自《{source_title}》）

> 第 3 步填。= 原作保留的底色 + 新设定圣经覆盖/新增后的"现行"世界规则总览。
> 注意：这里写的是**改写后**的现行世界，不是原作世界。

## 力量 / 修炼 / 魔法体系（现行）
## 政治 / 势力格局（现行）
## 地理
## 时间线（关键节点）
## 术语表（新旧混合，以现行为准）
"""


def build_outline(n, rewrite_type):
    if n >= 6:
        a1, a2 = max(1, n // 4), n * 3 // 4
        acts = (f"## 三幕结构（自由编织，不受原作章节束缚）\n"
                f"- 第一幕（约 1-{a1}）：立新世界 + 新主角处境 + 抛改动钩子\n"
                f"- 第二幕（约 {a1+1}-{a2}）：新设定展开 + 大势推进 + 中段反转\n"
                f"- 第三幕（约 {a2+1}-{n}）：高潮 + 新结局\n")
    else:
        acts = "## 结构\n（短篇——围绕单一改动核心推进）\n"
    chapters = "\n".join(f"- 第 {i:02d} 章 《》 — 主线事件 / 涉及的新设定 / 钩子" for i in range(1, n + 1))
    return f"""# 章纲 — 《<新书名待定>》改写

> 改动方向：{rewrite_type}
> 第 5 步填。**章纲未敲定不进 Demo。** 改写自由重排，不必对齐原作章节顺序。

## 总体弧线

{acts}
## 逐章
{chapters}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_novel", help="原作 .txt 或 .docx")
    ap.add_argument("--rewrite-type", required=True, help="一句话改动方向（如：换主角+加任务系统魔改）")
    ap.add_argument("--scale", required=True, choices=list(SCALE_CHOICES))
    ap.add_argument("--target-chapters", type=int, default=None, help="覆盖规模档的章数")
    ap.add_argument("--person", default="third-limited", choices=["first", "third-limited"])
    ap.add_argument("--genre", default=None,
                    help="改写后题材；命中力量题材（穿越/系统流/修仙/玄幻…）时 seed power_system_registry 脚手架。"
                         "缺省时回落 --rewrite-type 文本（魔改常在改动方向里点名机制）")
    ap.add_argument("--out", default=None, help="输出根，缺省 创作区/写小说/<原作名>-改写/")
    ap.add_argument("--outputs", default="txt,docx,outline")
    ap.add_argument("--target-platform", default="跨平台")
    ap.add_argument("--purpose", default=None,
                    help="小说用途：传统小说/漫剧源书/微短剧源书/短读/短篇/出海译制底稿/自定义")
    ap.add_argument("--draft-mode", default=None, choices=NOVEL_DRAFT_MODES,
                    help="小说生成模式：决定速度/质量 gate 密度")
    ap.add_argument("--draft-workflow", default=None, choices=DRAFT_WORKFLOWS,
                    help="小说生成工作流：默认单步/三步迭代/边写边自检")
    ap.add_argument("--batch-review-interval", default="5章",
                    help="小批回扫间隔；默认 5章，可填 3章/5章/关闭")
    ap.add_argument("--chapter-granularity", default="逐章", choices=CHAPTER_GRANULARITY,
                    help="章节生成粒度：逐章/小批/全书草稿")
    ap.add_argument("--ai-text-usage", default=None, choices=AI_TEXT_USAGE_MODES,
                    help="发布披露用：AI-generated / AI-assisted / 未使用AI文本")
    ap.add_argument("--score-source", default=None,
                    help="可选：novel-score 的 评分/score_report.json；读 scores/verdict/deductions "
                         "预填 改动spec② 弱项（建议·待对账）")
    ap.add_argument("--i-have-rights", action="store_true")
    ap.add_argument("--rights-jurisdiction", default=None,
                    help="公版/授权依据适用辖区，如 US/CN/GLOBAL；缺省按来源推断")
    ap.add_argument("--distribution-regions", default=None,
                    help="计划发行/交付地区，逗号分隔，如 CN,US；公版跨区时必须复核")
    args = ap.parse_args()

    source_path = os.path.abspath(args.source_novel)
    if not os.path.exists(source_path):
        print(f"[err] 找不到原作：{source_path}", file=sys.stderr)
        sys.exit(2)

    source_title = os.path.splitext(os.path.basename(source_path))[0]
    out_root = os.path.abspath(args.out or os.path.join("创作区", "写小说", f"{source_title}-改写"))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（备份/删除后重试）", file=sys.stderr)
        sys.exit(2)

    for sub in ("设定", "章节", "导出", "写作任务", "合规"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    novel_txt = os.path.join(out_root, "原作.txt")
    ext = os.path.splitext(source_path)[1].lower()
    if ext == ".txt":
        shutil.copy(source_path, novel_txt)
    elif ext == ".docx":
        docx_to_txt(source_path, novel_txt)
    else:
        print(f"[err] 不支持的格式：{ext}（请 .txt/.docx）", file=sys.stderr)
        shutil.rmtree(out_root); sys.exit(2)

    rights = detect_rights_status(novel_txt, args.i_have_rights)
    if rights == "unknown":
        print("[err] 无法判定原作版权。公版来源请在 txt 头加 `# copyright: public-domain`；"
              "自有/已授权重跑加 --i-have-rights。", file=sys.stderr)
        shutil.rmtree(out_root); sys.exit(2)

    # 源语言/文体体检：默认假设原作是现代中文白话文；真遇文言文/外文要先建源理解层再改写成白话文。
    try:
        with open(novel_txt, encoding="utf-8") as _f:
            _lang = classify_register(_f.read())
    except Exception:
        _lang = {"register": "modern_zh", "signals": []}
    source_register = _lang.get("register", "modern_zh")
    source_comprehension_status = "not_required"
    if source_register != "modern_zh":
        source_comprehension_status = "draft"
        try:
            source_scaffold(out_root)  # 写 设定/source_comprehension.{md,json}(status=draft)
        except Exception as _e:  # pragma: no cover - defensive
            print(f"[warn] 源理解层脚手架生成失败：{_e}", file=sys.stderr)
        _label = "文言文/古文" if source_register == "classical_zh" else "外文"
        print("", file=sys.stderr)
        print(f"⚠️ 原作疑似 **{_label}**（{source_register}）。默认假设原作是现代中文白话文，",
              file=sys.stderr)
        print("   按白话直接改写会理解错术语/典故/称谓。已生成源理解层脚手架 设定/source_comprehension.md：",
              file=sys.stderr)
        for _s in _lang.get("signals", [])[:2]:
            print(f"     - {_s}", file=sys.stderr)
        print("   ▶ 先补全理解层（现代白话理解 + 古今词/术语对照 + 文化注释 + 改写边界），", file=sys.stderr)
        print("     把 设定/source_comprehension.json 的 status 置 confirmed，再改写成白话文。", file=sys.stderr)
        print("     （未确认前 qa_gate / 导出会阻断；下游从理解层改写，保留 curated 古语/术语。）", file=sys.stderr)
        print("", file=sys.stderr)

    score_report = load_score_report(os.path.abspath(args.score_source)) if args.score_source else None
    diagnosis = build_score_diagnosis(score_report) if score_report else ""

    scale = normalize_scale(args.scale)
    profile = scale_profile(scale)
    n = args.target_chapters or profile["target_chapters"]
    outputs = parse_outputs(args.outputs)
    purpose = normalize_novel_purpose(args.purpose) or infer_novel_purpose(
        platform=args.target_platform, scale=scale, target=args.draft_mode
    )
    draft_mode = resolve_novel_draft_mode(args.draft_mode, purpose=purpose, platform=args.target_platform, scale=scale)
    draft_workflow = resolve_novel_draft_workflow(
        args.draft_workflow,
        draft_mode=draft_mode,
        purpose=purpose,
        scale=scale,
        target_chapters=n,
    )
    meta = base_meta("rewrite", outputs=outputs, rights_status=rights)
    # 派生权利字段（rights_covered_regions / requires_region_rights_review 等）统一由
    # rights_metadata 计算，使公版改写也能触发 qa_gate 的发行地区复核。
    meta.update(rights_metadata(
        rights,
        rights_declared=args.i_have_rights or rights in ("original", "user-owned", "user-declared"),
        rights_jurisdiction=args.rights_jurisdiction,
        distribution_regions=args.distribution_regions,
    ))
    meta.update({
        "source_novel": source_path,
        "source_title": source_title,
        "source_register": source_register,
        "source_comprehension_status": source_comprehension_status,
        # 桥接标记：公版/经典 IP 改写 → 一旦下游改编成漫剧/微短剧，须按广电2026-04新规复核
        # （禁颠覆性魔改经典/英雄/历史人物·真人肖像授权·三级备案）。结构化字段，供改编环节合规接力。
        "classic_ip_adaptation": rights in ("public-domain", "public_domain"),
        "rewrite_type": args.rewrite_type,
        "scale": scale,
        "purpose": purpose,
        "target_chapters": n,
        "target_words_per_chapter": profile["words_per_chapter"],
        "target_wordcount_min_max": profile["min_max"],
        "person": args.person,
        "rights_declared_at": date.today().isoformat() if args.i_have_rights else None,
        "title": None,
        "target_platform": args.target_platform,
        "demo_chapters": demo_chapters_for(n),
        "draft_mode": draft_mode,
        "draft_workflow": draft_workflow,
        "batch_review_interval": args.batch_review_interval,
        "chapter_granularity": args.chapter_granularity,
        "ai_text_usage": args.ai_text_usage,
        "score_source": os.path.abspath(args.score_source) if args.score_source else None,
        "score_verdict": score_report.get("verdict") if score_report else None,
        "score_total": score_report.get("total_score") if score_report else None,
    })
    W = lambda rel, txt: open(os.path.join(out_root, rel), "w", encoding="utf-8").write(txt)
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    write_project_settings(out_root, {
        "目标平台": args.target_platform,
        "小说用途": purpose,
        "权利来源": rights,
        "权利辖区": meta.get("rights_jurisdiction", ""),
        "发行地区": ",".join(meta.get("distribution_regions") or []) or "未定",
        "篇幅档": f"{scale}（{n}章×{profile['words_per_chapter'][0]}-{profile['words_per_chapter'][1]}字）",
        "改动方向": args.rewrite_type,
        "输出格式": ",".join(outputs) + "（novel-craft/scripts/export.py）",
        "小说生成模式": draft_mode,
        "小说生成工作流": draft_workflow,
        "小批回扫间隔": args.batch_review_interval,
        "章节生成粒度": args.chapter_granularity,
        "AI使用披露": args.ai_text_usage or "（发布前用 ai_usage.py 确认）",
        "评分诊断": (f"评分/score_report.json（verdict={score_report.get('verdict')}）"
                   if score_report else "（未提供 --score-source）"),
    }, note="改写：改主线/换设定/加原创料，新设定圣经为准。")
    W("设定/改动spec.md", build_change_spec(source_title, diagnosis))
    W("设定/新设定.md", build_new_settings(source_title))
    W("设定/角色卡.md", build_character_card(source_title))
    W("设定/世界观.md", build_worldview(source_title))
    W("设定/章纲.md", build_outline(n, args.rewrite_type))
    # 一致性注册表脚手架（B1）：改写作品（尤其换设定/加系统的魔改）也要有 character_guardrails /
    # power_system_registry，否则 novel-wiki 的护栏 / 力量体系机检在改写作品上静默 no-op。
    from consistency_scaffold import consistency_registry_files
    for rel, content in consistency_registry_files(args.genre or args.rewrite_type):
        W(rel, content)
    W("_进度.md", build_progress_markdown("<新书名待定>", "rewrite", n))

    print(f"[ok] 改写项目骨架 → {out_root}")
    print(f"     原作.txt        ← {ext} 抽取（参考素材，非底稿）")
    if score_report:
        print(f"     设定/改动spec.md ← 骨架 + 评分诊断已预填②栏"
              f"（verdict={score_report.get('verdict')}，建议·待与用户要求对账）★最重要")
    else:
        print(f"     设定/改动spec.md ← 骨架（第 2 步填：保留/改/加 三栏）★最重要")
    print(f"     设定/新设定.md   ← 骨架（第 3 步填：新增/覆盖设定 + 一致性约束）")
    print(f"     设定/角色卡.md / 世界观.md / 章纲.md ← 骨架")
    print(f"     _meta: kind=rewrite type=\"{args.rewrite_type}\" 章数={n} 版权={rights}")
    print(f"[next] 第 2 步填改动spec（先定'保留内核'）→ 第 3 步新设定圣经 → 书名 → 章纲 → Demo gate → 续写+回扫。")


if __name__ == "__main__":
    main()
