#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_project.py — 建【原创从零】小说项目骨架（无源文本·访谈蓝图驱动）。

与 novel-rewrite 的 init 镜像，但：
  - 不吃原作、不判版权（原创=用户自有，天然合法）；
  - 第一生产资料是【创作蓝图】（从用户"几个字+碎片"经立项访谈补全），不是改动spec；
  - 可选 --ingest 把用户给的碎片（风格样本 / 零散笔记 / 半成品片段）收进 素材/ 作参考。

用法:
    python3 init_project.py --title "<书名或'待定'>" --genre "<题材类型>" \\
        --premise "<一句话故事>" --scale short|medium|long|微短剧|漫剧 \\
        [--platform 起点|番茄|晋江|抖音漫剧|红果|历史向|跨平台] \\
        [--person first|third-limited] [--target-chapters N] \\
        [--ingest <碎片路径>]...  [--out <根>] [--outputs txt,docx,outline]
        [--draft-mode 极速初稿|稳妥初稿|商业连载|漫剧源书]
        [--chapter-granularity 逐章|小批|全书草稿]

无依赖（纯文本骨架；导出 docx 在后续 export 步骤再装 python-docx）。
"""
import argparse
import json
import os
import shutil
import sys
import re
from datetime import date

# Standardized imports from novel/_lib
LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "novel", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from novel_contract import (base_meta, build_progress_markdown, routing_stages,
                            SCALE_CHOICES, scale_profile, NOVEL_DEFAULTS,
                            NOVEL_STAGES, normalize_scale)
from settings import write_settings

# Simple fallback for missing constants in novel_contract
NOVEL_DRAFT_MODES = ("极速初稿", "稳妥初稿", "商业连载", "漫剧源书")
CHAPTER_GRANULARITY = ("逐章", "小批", "全书草稿")
AI_TEXT_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI文本")

def parse_outputs(value):
    return [s.strip() for s in value.split(",") if s.strip()]


def demo_chapters_for(target_chapters):
    if target_chapters <= 3:
        return 0
    if target_chapters <= 20:
        return 2
    return 3

def slug(s):
    s = re.sub(r"[^\w一-鿿-]+", "", (s or "").strip())
    return s or "新书待定"

# ... (keep blueprint, bible, character_card, worldview, outline builders as they are)



def build_blueprint(title, genre, platform, premise, scale, n, wpc, person):
    return f"""# 创作蓝图 — 《{title}》

> 这部原创小说的"宪法"。动笔前与用户敲定，每条**具体可判定**，别写空话。
> 来源：从用户的"几个字 + 碎片"经【立项访谈】补全（见 novel-create 第 0 步 / references/interview.md）。

## 一句话故事（logline）
{premise}
（标准式：谁，在什么处境，靠什么金手指，去对抗什么，最终要得到什么）

## 题材 / 平台 / 基调
- 题材类型：{genre}
- 目标平台：{platform}（决定篇幅档 / 爽点节奏 / 开篇钩；起名按平台见 novel-title）
- 基调：（热血/爽/虐/治愈/暗黑/诙谐…）

## 主角
- 是谁 / 出身 / 性格底色：
- **金手指 / 核心能力（必须有代价/限制）**：
- 动机 / 心结 / 渴望：

## 核心爽点（这本"爽"在哪，按平台密度铺）
-

## 主线冲突（主角要对抗的最大阻力 / 反派 / 困局）
-

## 目标读者
-

## 规模 / 视角
- 规模档：{scale}（约 {n} 章 × {wpc[0]}-{wpc[1]} 字 target）
- 人称视角：{person}

## 风格卡（有样本就此刻填；没有则 Demo 后回填锚定）
- 文风关键词：
- 句子节奏 / 叙述密度：
- 对白比 vs 内心戏比：
- 禁忌（不要的腔调 / 词 / 套路）：
- 样本素材：见 `素材/`（若 --ingest 收了用户的风格样本 / 笔记 / 半成品）
"""


def build_settings_bible(title):
    return f"""# 设定圣经 — 《{title}》

> 本作**所有原创设定**：金手指 / 力量 / 势力 / 人物 / 地理 / 物品。逐章写作硬约束，回扫逐条核。
> **铁律**：内部不许自相矛盾；**金手指必须有代价**；设定一旦定下，跨章复用同一值。

## 体系（金手指 / 力量 / 修炼）
### <名称>　是什么 / 规则边界 / **代价·限制** / 首现章 / 不可违反点

## 势力 / 组织
### <名称>　立场·目的·与主角关系·首现章

## 人物（主角之外）
### <名称>　身份·外貌锚定·性格·动机·说话习惯·首现章·复用范围

## 地理 / 秘境 / 物品
### <名称>　描述·规则·首现章

## 一致性约束清单（回扫逐条核）
- [ ]
"""


def build_character_card(title):
    return f"""# 角色卡 — 主角 ·《{title}》

> 第 3 步填。原创主角从【创作蓝图】展开；能力依【设定圣经】。

## 姓名 / 年龄 / 性别
## 外观（锚定 3-5 个不可漂特征）
## 出身 / 处境
## 能力体系（依 设定圣经.md，含代价）
## 性格底色
## 动机 / 心结 / 渴望（驱动主线）
## 关键关系
## 说话习惯（口头禅 / 句式 / 语气）
## 成长弧线（起点 → 终点）
"""


def build_worldview(title):
    return f"""# 世界观 — 《{title}》

> 第 3 步填。原创世界的现行规则总览（与 设定圣经 互为表里：圣经记"条目"，本卡记"全局规则"）。

## 力量 / 修炼 / 魔法体系
## 政治 / 势力格局
## 地理 / 地图
## 时间线（关键节点）
## 术语表
## 世界基调 / 视觉底色
"""


def build_outline(title, n, premise):
    if n >= 6:
        a1, a2 = max(1, n // 4), n * 3 // 4
        acts = (f"## 三幕结构（原创自由编织）\n"
                f"- 第一幕（约 1-{a1}）：立世界 + 主角处境 + 金手指登场 + 开篇钩（黄金前 3 章立住爽点/悬念）\n"
                f"- 第二幕（约 {a1+1}-{a2}）：设定展开 + 大势推进 + 多次小爽点 + 中段大反转\n"
                f"- 第三幕（约 {a2+1}-{n}）：高潮对决 + 主线收束 + 结局（留续作钩可选）\n")
    else:
        acts = "## 结构\n（短篇——围绕单一核心爽点/反转推进）\n"
    chapters = "\n".join(
        f"- 第 {i:02d} 章 《》 — 本章戏剧节拍 / 涉及的设定 / 爽点或钩子" for i in range(1, n + 1))
    return f"""# 章纲 — 《{title}》

> logline：{premise}
> 第 5 步填。**章纲未敲定不进 Demo。** 节拍优先、字数兜底（见 novel-craft/references/split.md）。
> 每章一个戏剧节拍 + 至少一个钩子；爽点按平台密度铺。

## 总体弧线
{acts}
## 逐章
{chapters}
"""


def build_progress(title, meta):
    n = meta["target_chapters"]
    rows = "\n".join(f"| {i:02d} |  | - | [ ] |" for i in range(1, n + 1))
    packets = "\n".join(
        f"- [ ] 写作任务包（第 {a}-{min(a+4, n)} 章）"
        for a in range(1, n + 1, 5))
    scans = "\n".join(
        f"- [ ] 轻量扫描（第 {a}-{min(a+4, n)} 章）" for a in range(1, n + 1, 5))
    outs = "\n".join(f"- [ ] {fmt}" for fmt in meta["outputs"])
    return f"""# 进度 — 《{title}》（原创）

{create_stage_markdown()}

> {meta['scale']} 档：约 {n} 章 × {meta['target_words_per_chapter'][0]}-{meta['target_words_per_chapter'][1]} 字。平台={meta['target_platform']}。

## 准备阶段
- [x] 项目骨架
- [ ] 创作蓝图（用户已确认）★最重要
- [ ] 设定圣经
- [ ] 角色卡 / 世界观卡
- [ ] 书名（用户已选）
- [ ] 章纲（用户已确认）

## 写作阶段
### 任务包
{packets}

| 章 | 标题 | 字数 | 状态 |
|---|---|---|---|
{rows}

## 状态账本
- [ ] `审稿/state_ledger.json`
- [ ] 逐章 `审稿/state_delta_第NN章.json`

## 回扫阶段（novel-review）
{scans}
- [ ] 全量一致性扫描（设定圣经一致 / 人设不崩 / 钩子回收 / 文风不漂）

## 导出
{outs}

## 合规 / 发布
- [ ] `合规/AI使用说明.md`
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="待定", help="书名；未定填'待定'，后续 novel-title 选定")
    ap.add_argument("--genre", required=True, help="题材类型，如 都市异能 / 古言宅斗 / 玄幻修真")
    ap.add_argument("--premise", required=True, help="一句话故事（logline）")
    ap.add_argument("--scale", required=True, choices=list(SCALE_CHOICES))
    ap.add_argument("--platform", default="跨平台")
    ap.add_argument("--person", default="third-limited", choices=["first", "third-limited"])
    ap.add_argument("--target-chapters", type=int, default=None)
    ap.add_argument("--ingest", action="append", default=[],
                    help="用户给的碎片(风格样本/笔记/半成品)，可多次；收进 素材/")
    ap.add_argument("--out", default=None, help="输出根，缺省 写小说/<书名>/")
    ap.add_argument("--outputs", default="txt,docx,outline")
    ap.add_argument("--draft-mode", default="稳妥初稿", choices=NOVEL_DRAFT_MODES,
                    help="小说生成模式：决定速度/质量 gate 密度")
    ap.add_argument("--chapter-granularity", default="逐章", choices=CHAPTER_GRANULARITY,
                    help="章节生成粒度：逐章/小批/全书草稿")
    ap.add_argument("--ai-text-usage", default=None, choices=AI_TEXT_USAGE_MODES,
                    help="发布披露用：AI-generated / AI-assisted / 未使用AI文本")
    args = ap.parse_args()

    folder = slug(args.title) if args.title != "待定" else f"新书待定-{slug(args.genre)}"
    out_root = os.path.abspath(args.out or os.path.join("写小说", folder))
    if os.path.exists(out_root):
        print(f"[err] 目标已存在：{out_root}（备份/删除后重试，或换 --title/--out）", file=sys.stderr)
        sys.exit(2)

    for sub in ("设定", "章节", "素材", "审稿", "导出", "写作任务", "合规"):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)

    # 吃碎片：把用户给的风格样本/笔记/半成品复制进 素材/
    ingested = []
    for p in args.ingest:
        ap_ = os.path.abspath(p)
        if not os.path.exists(ap_):
            print(f"[warn] --ingest 找不到：{ap_}（跳过）", file=sys.stderr)
            continue
        dst = os.path.join(out_root, "素材", os.path.basename(ap_))
        (shutil.copytree if os.path.isdir(ap_) else shutil.copy)(ap_, dst)
        ingested.append(os.path.basename(ap_))

    scale = normalize_scale(args.scale)
    profile = scale_profile(scale)
    n = args.target_chapters or profile["target_chapters"]
    wpc = profile["words_per_chapter"]
    outputs = parse_outputs(args.outputs)
    title = args.title
    meta = base_meta("create", outputs=outputs, rights_status="original",
                     title=None if title == "待定" else title)
    meta.update({
        "title": None if title == "待定" else title,
        "genre": args.genre,
        "premise": args.premise,
        "scale": scale,
        "target_chapters": n,
        "target_words_per_chapter": wpc,
        "person": args.person,
        "target_platform": args.platform,
        "ingested": ingested,
        "demo_chapters": demo_chapters_for(n),
        "demo_passed_at": None,
        "title_chosen_at": None,
        "draft_mode": args.draft_mode,
        "chapter_granularity": args.chapter_granularity,
        "ai_text_usage": args.ai_text_usage,
        "split_standard": "novel-craft/references/split.md",
    })
    W = lambda rel, txt: open(os.path.join(out_root, rel), "w", encoding="utf-8").write(txt)
    json.dump(meta, open(os.path.join(out_root, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    write_settings(out_root, {
        "目标平台": args.platform,
        "题材": args.genre,
        "权利辖区": meta.get("rights_jurisdiction", ""),
        "发行地区": ",".join(meta.get("distribution_regions") or []) or "GLOBAL",
        "篇幅档": f"{scale}（{n}章×{wpc[0]}-{wpc[1]}字）",
        "权利来源": "original（原创自有）",
        "输出格式": ",".join(outputs) + "（novel-craft/scripts/export.py；漫剧线加 n2d）",
        "小说生成模式": args.draft_mode,
        "章节生成粒度": args.chapter_granularity,
        "AI使用披露": args.ai_text_usage or "（发布前用 ai_usage.py 确认）",
    }, note="原创从零：创作蓝图+设定圣经为宪法。")
    W("设定/创作蓝图.md", build_blueprint(title, args.genre, args.platform, args.premise, scale, n, wpc, args.person))
    W("设定/设定圣经.md", build_settings_bible(title))
    W("设定/角色卡.md", build_character_card(title))
    W("设定/世界观.md", build_worldview(title))
    W("设定/章纲.md", build_outline(title, n, args.premise))
    # ... (inside main)
    n = args.target_chapters or profile["target_chapters"]
    wpc = profile["words_per_chapter"]
    
    # ... (around line 210)
    W("_进度.md", build_progress_markdown(title, "create", n))

    print(f"[ok] 原创项目骨架 → {out_root}")
    print(f"     设定/创作蓝图.md ← 骨架（第 2 步填：logline/主角/金手指/爽点/冲突/风格卡）★最重要")
    print(f"     设定/设定圣经.md ← 骨架（第 3 步填：金手指代价 + 一致性约束）")
    print(f"     设定/角色卡.md / 世界观.md / 章纲.md ← 骨架")
    print(f"     写作任务/ ← draft_packets.py 生成逐章任务包；合规/ ← ai_usage.py 生成披露文件")
    if ingested:
        print(f"     素材/ ← 已收碎片：{', '.join(ingested)}")
    print(f"     _meta: kind=create 题材=\"{args.genre}\" 档={scale}({n}章×{wpc[0]}-{wpc[1]}字) 平台={args.platform}")
    print(f"[next] 第 2 步填创作蓝图（用户审）→ 第 3 步设定圣经+卡 → 书名(novel-title) → 章纲 → Demo gate → draft_packets 写章+回扫 → AI披露+导出。")


if __name__ == "__main__":
    main()
