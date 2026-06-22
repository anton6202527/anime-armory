#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_novel.py — 把长篇小说自动拆分成粗胚分块，并搭好 AI漫剧/短剧 生产目录骨架。
（注意：拆分只是脚手架，最终「集」边界由导演按戏剧节拍重切，一章≠一集。）

用法:
    python3 split_novel.py <小说路径> [选项]

常用选项:
    --by-chapter       按「第X章」+ 强钩候选切（更贴戏剧节拍）
    --per-chapter      每章独立成一集（最贴节拍；长章保持整章，精修时再拆）
    --keep-frontmatter 保留开头简介/标签/看点（默认自动剥离）
    --out 目录          作品根（默认=小说同级；小说在 …/小说/ 下时自动取其父）
    --target 高级参数：粗胚字数参考（仅用于报告/人工复核，不参与默认切点决策）
    --min/--max 旧参数兼容（仅作历史命令占位，不再作为硬性上下限）
    --name 标题         素材文件头用的标题（默认取小说文件名）

支持 .txt / .docx 输入。默认输出布局：
    <作品根>/_进度.md
    <作品根>/设定库/global_style.md
    <作品根>/设定库/characters/_角色总表.md
    <作品根>/设定库/locations/_场景总表.md
    <作品根>/小说/<剧名>.txt 规范源副本（供 source_check.py --record）
    <作品根>/脚本/第N集/{raw.txt 分镜剧本.md 故事板.md 素材清单.md
                         voiceover.txt bgm.txt 封面.md 字幕_中文.srt}
（出图/ 与 出视频/ 由 n2d-image 与 n2d-video 在后续阶段创建。）
开头的简介/标签/看点等元数据默认自动剥离（见 strip_frontmatter）。
"""
import argparse
import os
import re
import sys
import zipfile

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_const import boundary_buckets, boundary_lexicon
from n2d_contract import PROGRESS_COLUMNS
from n2d_settings import DEFAULTS, get_setting
from n2d_visual_styles import format_style_contract_markdown, style_options_text


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return read_docx(path)
    # 纯文本，尝试多种编码
    raw = open(path, "rb").read()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    # 段落 </w:p> 转换为换行，去掉所有标签
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    # 还原常见 XML 实体
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        xml = xml.replace(a, b)
    return xml


def normalize_paragraphs(text):
    paras = [p.strip() for p in re.split(r"\r?\n+", text)]
    return [p for p in paras if p]


CHAPTER_RE = re.compile(r"^\s*第\s*[0-9零一二三四五六七八九十百千两]+\s*[章回节卷]")

# 开头常见的"非正文"元数据行（简介/标签/看点等），自动剥离
META_PREFIX = ("【", "✅", "☑", "★", "#", "—")
META_LABELS = {
    "简介", "内容简介", "作品简介", "标准简介", "一句话简介",
    "标签", "作品标签", "主要看点", "看点", "一句话剧透", "剧透", "作者", "字数",
}


def strip_frontmatter(paras):
    """剥离开头的简介/标签/看点/书名等非正文块。

    优先：若开头 40 段内出现首个章节标题，则从该标题起算正文（丢弃之前所有元数据）。
    退化：无章节标题时，逐行丢弃开头的元数据行（书名《…》、【…】、✅…、纯标签词等）。
    """
    if not paras:
        return paras
    head = paras[:40]
    first_ch = next((i for i, p in enumerate(head) if CHAPTER_RE.match(p)), None)
    if first_ch is not None:
        return paras[first_ch:]
    start = 0
    while start < len(paras) and start < 40:
        p = paras[start]
        pn = re.sub(r"[《》【】\s]", "", p)
        is_title = bool(re.match(r"^《.+》$", p))
        is_meta = (
            p.startswith(META_PREFIX)
            or pn in META_LABELS
            or any(pn.startswith(lbl) for lbl in ("一句话简介", "标准简介", "内容简介", "一句话剧透"))
        )
        if is_title or is_meta:
            start += 1
        else:
            break
    return paras[start:] or paras


def split_sentences(para):
    # 在句末标点后切句，保留标点
    parts = re.split(r"(?<=[。！？!?…”])", para)
    return [s for s in (p.strip() for p in parts) if s]


def build_boundary_res(genre_text=None):
    """按题材构建 (强钩收尾, 冲突, 爽点/反转) 三条正则。

    词面来自 `n2d_const.boundary_lexicon`（base ∪ 命中题材桶），治"古言爽文词典对
    女频情感/悬疑/都市退化成无闭环"。未识别题材时复刻历史覆盖（base ∪ 古装动作）。
    """
    strong, conflict, payoff = boundary_lexicon(genre_text)
    strong_re = re.compile(r"(" + "|".join(re.escape(t) for t in strong) + r")\s*$")
    conflict_re = re.compile(r"(" + "|".join(re.escape(t) for t in conflict) + r")")
    payoff_re = re.compile(r"(" + "|".join(re.escape(t) for t in payoff) + r")")
    return strong_re, conflict_re, payoff_re


# 模块级默认（题材=None：复刻历史古言/修仙覆盖）。main() 解析 _设置.md `题材` 后按题材重建。
STRONG_EPISODE_END_RE, CONFLICT_RE, PAYOFF_OR_REVERSAL_RE = build_boundary_res(None)

SCENE_BREAK_RE = re.compile(
    r"^\s*(?:[-—*]{3,}|[一二三四五六七八九十0-9]+[、.．]\s*|【[^】]{1,24}】|"
    r"(?:翌日|次日|当夜|与此同时|另一边|片刻后|三日后|半个时辰后))"
)


def strong_episode_end(text):
    """启发式识别可作为粗胚右边界的强钩。

    这不是最终剧情判断；它只避免 split 阶段在普通段落末尾按字数硬切。
    """
    return bool(STRONG_EPISODE_END_RE.search((text or "")[-180:]))


def has_conflict(text):
    return bool(CONFLICT_RE.search(text or ""))


def has_payoff_or_reversal(text):
    return bool(PAYOFF_OR_REVERSAL_RE.search(text or ""))


def natural_scene_break(next_para):
    return bool(next_para and (CHAPTER_RE.match(next_para) or SCENE_BREAK_RE.match(next_para)))


def boundary_candidate(end_para, next_para=None):
    return strong_episode_end(end_para) or natural_scene_break(next_para)


def loop_ready(text, end_para, next_para=None):
    """粗胚闭环启发式：有冲突、有释放/反转，并落在章节/场景/强钩候选处。"""
    return boundary_candidate(end_para, next_para) and has_conflict(text) and has_payoff_or_reversal(text)


def chunk_text(paras, target=None, hi=None, lo=None):
    """连续性优先粗切：默认不锚字数，target/hi/lo 为旧参数兼容与报告参考。

    不再因为超过 max 或低于 min 硬切/硬并，也不再等到 target 才允许切。
    只有当前窗口出现「冲突→释放/反转→章节/场景/强钩候选」，才落一个粗胚分块；
    否则继续并入后文，交给精修阶段按 P0→P6 重切。
    """
    episodes = []
    buf = []

    def flush():
        nonlocal buf
        if buf:
            episodes.append("\n".join(buf))
            buf = []

    for i, para in enumerate(paras):
        buf.append(para)
        text = "\n".join(buf)
        next_para = paras[i + 1] if i + 1 < len(paras) else None
        if loop_ready(text, para, next_para):
            flush()
    flush()
    return episodes


def split_by_chapter(paras, target=None, hi=None, lo=None):
    """按「第X章」边界 + 强钩候选切粗胚：

    - 章是候选场，不等于集；章节/场景/强钩候选若形成「冲突→释放/反转」才落集；
    - target 只作报告参考，不参与默认切点决策；
    - 未形成闭环时继续并入下一章/场景。
    无章节标题时退回强钩候选切分。
    """
    return chunk_text(paras, target, hi, lo)


def split_per_chapter(paras, min_chars=100):
    """每章独立成一集（最贴戏剧节拍）；过短章节（疑似误判的标题行）并入上一集。

    无「第X章」标题时返回 None（由调用方退回强钩候选切分）。
    """
    chapters, cur = [], []
    for p in paras:
        if CHAPTER_RE.match(p) and cur:
            chapters.append(cur)
            cur = [p]
        else:
            cur.append(p)
    if cur:
        chapters.append(cur)
    if len(chapters) <= 1:
        return None
    episodes = []
    for ch in chapters:
        text = "\n".join(ch)
        body_len = sum(len(p) for p in ch)
        if episodes and body_len < min_chars:
            episodes[-1] = episodes[-1] + "\n" + text
        else:
            episodes.append(text)
    return episodes


def length_hint(chars):
    """字数只作复核提示，不参与切点决策。"""
    if chars < 650:
        return "偏短，复核闭环完整"
    if chars > 1100:
        return "偏长，复核中段钩子密度"
    return ""


PLACEHOLDERS = {
    "分镜剧本.md": "# {title}_第{n}集_分镜剧本\n\n> 待精修：参考 references/formats.md「分镜剧本」格式逐镜头填写。\n",
    "故事板.md": "# {title}_第{n}集_故事板\n\n> 待精修：参考 references/formats.md「故事板 Clip 表」格式，供 AI 视频生成（具体生视频后端在 n2d-video 阶段由 router/probe 决定；平台档案见 references/platforms.md）。\n",
    "素材清单.md": "# {title}_第{n}集_素材清单\n\n> 待精修：参考 references/formats.md「素材清单」格式，供 AI 图片生成（中文为主+英文备用；平台档案见 references/platforms.md）。\n",
    "voiceover.txt": "# {title}_第{n}集_配音文案\n# 待精修：按镜头顺序填写旁白/台词，标注角色与情绪。\n",
    "bgm.txt": "# {title}_第{n}集_BGM与音效\n# 待精修：填写整体情绪、BGM风格、关键音效点。\n",
    "封面.md": "# {title}_第{n}集_封面/首图\n\n> 待精修：一张高点击率封面 prompt（中文+英文），含本集最大爽点/钩子。\n",
    "字幕_中文.srt": "1\n00:00:00,000 --> 00:00:03,000\n（待精修：依据 voiceover.txt 台词 + 故事板.md 镜头时长生成带时间码的中文字幕）\n",
}


def write_if_absent(path, content):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def write_source_snapshot(root, title, source_text):
    """Keep a canonical txt copy under 小说/ so source_check can baseline it."""
    novel_dir = os.path.join(root, "小说")
    os.makedirs(novel_dir, exist_ok=True)
    path = os.path.join(novel_dir, f"{title}.txt")
    if not os.path.exists(path) or open(path, encoding="utf-8", errors="replace").read() != source_text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(source_text.rstrip() + "\n")
    return path


def global_style_scaffold(title, root):
    base_style = get_setting(root, "基础视觉风格", DEFAULTS["基础视觉风格"])
    style_note = f"{base_style}（来自 _设置.md 或全局默认；可选 {style_options_text()}）"
    return (
        f"# {title} — 全局画风与世界观\n\n"
        "## 视频模型路由\n自动按镜头路由（首跑不选择具体生视频后端；n2d-video 阶段按 `video_model_routes.json` + CLI/API 探测决定 primary/fallback）\n\n"
        "## 生视频后端决策\n延后到 n2d-video 出视频前；若用户明确固定后端或账号/交付只能单后端，再写 `_设置.md` 的 `视频模型路由/生视频模型/生视频渠道`。\n\n"
        f"## 基础视觉风格\n{style_note}\n\n"
        "## 画风\n高质量AI漫剧风格，统一色调，高细节；具体提示词随「基础视觉风格」派生。\n\n"
        "## 基础视觉风格契约（style_contract 源头）\n"
        f"{format_style_contract_markdown(base_style)}\n\n"
        "## 世界观\n（待精修）\n\n"
        "## 统一负面词\n（画风漂移、多余文字水印、多指错手、脸/妆造漂移；其余禁忌按「基础视觉风格」派生，例如未选Q版才禁低幼Q版，写实电影感才禁插画化）\n"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("novel")
    ap.add_argument("--out", default=None,
                    help="作品根（直接包含 脚本/ 出图/ 出视频/ + 全局文件）。缺省：小说在 .../小说/<X> 下→取其父；否则落到最近仓库根的 创作区/制漫剧/<剧名>/（找不到才回退小说同级并告警）")
    ap.add_argument("--target", type=int, default=None, help="高级参数：粗胚字数参考（仅用于报告/人工复核，不参与默认切点决策）")
    ap.add_argument("--min", type=int, default=None, help="旧参数兼容：不再作为硬性下限")
    ap.add_argument("--max", type=int, default=None, help="旧参数兼容：不再作为硬性上限")
    ap.add_argument("--name", default=None, help="标题（用于各素材文件头），默认取小说文件名")
    ap.add_argument("--by-chapter", action="store_true",
                    help="优先按「第X章」+ 强钩候选切集（更贴戏剧节拍）；无章节标题时自动退回强钩候选切")
    ap.add_argument("--per-chapter", action="store_true",
                    help="每章独立成一集（最贴戏剧节拍，一章=一集；长章保持整章，精修时按上/下集再拆）；无章节标题时自动退回强钩候选切")
    ap.add_argument("--keep-frontmatter", action="store_true",
                    help="保留开头的简介/标签/看点等元数据（默认自动剥离）")
    ap.add_argument("--limit", type=int, default=None,
                    help="部分先切：只粗切并落地前 N 集（仍按全本估总集数，便于先精修第1集验证后再续切）；缺省=全篇一次粗切。续切=重跑本脚本加大 --limit（已存在的集与进度勾选会保留）")
    args = ap.parse_args()

    if not os.path.exists(args.novel):
        sys.exit(f"找不到文件: {args.novel}")

    title = args.name or os.path.splitext(os.path.basename(args.novel))[0]
    # 新布局：作品根直接铺各阶段子文件夹（脚本/ 出图/ 出视频/）+ 全局文件。
    # 若小说位于 .../小说/<X>.docx，作品根 = 小说目录的父级；否则 = 小说同级目录。
    if args.out:
        root = args.out
    else:
        novel_dir = os.path.dirname(os.path.abspath(args.novel))
        if os.path.basename(novel_dir) == "小说":
            root = os.path.dirname(novel_dir)
        else:
            # n2d 产物应落 创作区/制漫剧/<剧名>/：向上找仓库根，
            # 避免把作品根误建在输入文件同级。
            d, repo = novel_dir, None
            while True:
                if (
                    os.path.isdir(os.path.join(d, "创作区", "制漫剧"))
                    or os.path.isdir(os.path.join(d, "制漫剧"))
                    or os.path.isdir(os.path.join(d, "skills"))
                ):
                    repo = d
                    break
                parent = os.path.dirname(d)
                if parent == d:
                    break
                d = parent
            if repo:
                root = os.path.join(repo, "创作区", "制漫剧", title)
            else:
                root = novel_dir
                print(f"[warn] 未找到含『创作区/制漫剧/』的仓库根，作品根回退到小说同级：{root}"
                      f"（建议用 --out 指定 创作区/制漫剧/<剧名>/）", file=sys.stderr)
    text = read_text(args.novel)
    write_source_snapshot(root, title, text)
    paras = normalize_paragraphs(text)
    if not paras:
        sys.exit("未读到正文内容。")

    dropped = 0
    if not args.keep_frontmatter:
        before = len(paras)
        paras = strip_frontmatter(paras)
        dropped = before - len(paras)

    # 题材感知边界词典：读 _设置.md `题材`（弱选择点；未设则 base ∪ 古装动作=历史默认）→
    # 重建模块级强钩/冲突/爽点正则，治女频情感/悬疑/都市粗切退化成无闭环。
    global STRONG_EPISODE_END_RE, CONFLICT_RE, PAYOFF_OR_REVERSAL_RE
    genre = get_setting(root, "题材", "")
    buckets = boundary_buckets(genre)
    STRONG_EPISODE_END_RE, CONFLICT_RE, PAYOFF_OR_REVERSAL_RE = build_boundary_res(genre)

    if args.per_chapter:
        episodes = split_per_chapter(paras) or chunk_text(paras, args.target, args.max, args.min)
    elif args.by_chapter:
        episodes = split_by_chapter(paras, args.target, args.max, args.min)
    else:
        episodes = chunk_text(paras, args.target, args.max, args.min)

    settings = os.path.join(root, "设定库")
    os.makedirs(os.path.join(settings, "characters"), exist_ok=True)
    os.makedirs(os.path.join(settings, "locations"), exist_ok=True)
    os.makedirs(os.path.join(root, "脚本"), exist_ok=True)

    write_if_absent(
        os.path.join(settings, "global_style.md"),
        global_style_scaffold(title, root),
    )
    write_if_absent(
        os.path.join(settings, "characters", "_角色总表.md"),
        f"# {title} — 角色卡总表\n\n> 全篇首次出现即建卡，后续所有镜头严格复用。格式见 references/formats.md。\n",
    )
    write_if_absent(
        os.path.join(settings, "locations", "_场景总表.md"),
        f"# {title} — 场景卡总表\n\n> 全篇首次出现即建卡，后续镜头保持一致。格式见 references/formats.md。\n",
    )
    write_if_absent(
        os.path.join(settings, "characters", "_生命周期.md"),
        f"# {title} — 角色形象生命周期时间线（跨集·全局产物）\n\n"
        "> 跨集造型/年龄/服装/形态里程碑的**全局产物**（Gap2）。第2步建卡后跑：\n"
        "> `python3 skills/n2d-script/scripts/lifecycle_scan.py <作品根> --write` 自动扫候选→人确认。\n"
        "> 用途：提前规划定妆库何时派生新『形态变体』；作 n2d-identity 跨集漂移的预期变化基线。\n"
        "> 格式见 references/formats.md §1.1。\n",
    )

    total_est = len(episodes)
    # 部分先切：只落地前 N 集（仍按全本估总集数）。续切=重跑加大 --limit。
    n_make = total_est if args.limit is None else max(1, min(args.limit, total_est))

    lengths = []
    for i, ep in enumerate(episodes[:n_make], 1):
        ep_dir = os.path.join(root, "脚本", f"第{i}集")
        os.makedirs(ep_dir, exist_ok=True)
        write_if_absent(os.path.join(ep_dir, "raw.txt"), ep)
        for fname, tmpl in PLACEHOLDERS.items():
            write_if_absent(os.path.join(ep_dir, fname), tmpl.format(title=title, n=i))
        lengths.append(len(ep.replace("\n", "")))

    # 进度表：部分先切 / 已存在进度时合并续写——保留已勾选的旧行，只追加新粗切的集。
    prog_path = os.path.join(root, "_进度.md")
    partial = args.limit is not None and n_make < total_est
    existing_rows = {}
    if os.path.exists(prog_path):
        for line in open(prog_path, encoding="utf-8"):
            m = re.match(r"\|\s*第(\d+)集\s*\|", line)
            if m:
                existing_rows[int(m.group(1))] = line.rstrip("\n")
    if args.limit is not None or not os.path.exists(prog_path):
        subtitle_lang = get_setting(root, "字幕语言", "中文")
        wants_en = "英" in subtitle_lang or "en" in subtitle_lang.lower()
        fresh = {}
        for i, ln in enumerate(lengths, 1):
            cells = [f"第{i}集", str(ln), "✅"] + ["⬜"] * (len(PROGRESS_COLUMNS) - 3)
            if "字幕英" in PROGRESS_COLUMNS and not wants_en:
                cells[PROGRESS_COLUMNS.index("字幕英")] = "—"
            fresh[i] = "| " + " | ".join(cells) + " |"
        rows = {**fresh, **existing_rows}  # 旧勾选优先，保留人工进度
        made = max(rows) if rows else n_make
        header = (f"# {title} — 生产进度\n",
                  f"已粗切 **{made}** 集"
                  + (f"（全本约估 {total_est} 集；部分先切，精修验证后重跑 split 加大 --limit 续切）。\n"
                     if partial else f"。\n"))
        prog_lines = [*header,
            "| " + " | ".join(PROGRESS_COLUMNS) + " |",
            "|" + "|".join("---" for _ in PROGRESS_COLUMNS) + "|"]
        prog_lines += [rows[i] for i in sorted(rows)]
        with open(prog_path, "w", encoding="utf-8") as f:
            f.write("\n".join(prog_lines) + "\n")

    print(f"作品根: {root}")
    mode = "每章一集" if args.per_chapter else ("按章节+强钩候选" if args.by_chapter else "按强钩候选")
    target_note = f"；字数参考 {args.target}（仅报告，不参与切点）" if args.target else "；未设置字数参考"
    genre_note = f"{genre}→{'/'.join(buckets)}" if genre else f"未设题材→{'/'.join(buckets)}(默认)"
    print(f"切分方式：{mode}；边界词典题材：{genre_note}；剥离开头元数据 {dropped} 段。")
    if partial:
        print(f"部分先切：已落地前 {n_make} 集（全本按候选断点约估 {total_est} 集）。"
              f"字数范围 {min(lengths)}~{max(lengths)}{target_note}；无硬上下限")
        print(f"下一步：精修第1集验证节拍/画风/角色卡；满意后重跑 split 加大 --limit 续切（旧集与进度勾选保留）。")
    else:
        print(f"共 {n_make} 集，字数范围 {min(lengths)}~{max(lengths)}{target_note}；无硬上下限")
        print("目录骨架已生成。下一步：精修每集素材。")
    hints = [f"第{i}集 {length_hint(n)}" for i, n in enumerate(lengths, 1) if length_hint(n)]
    if hints:
        tail = "；…" if len(hints) > 8 else ""
        print("字数提示（仅复核，不参与切点）： " + "；".join(hints[:8]) + tail)


if __name__ == "__main__":
    main()
