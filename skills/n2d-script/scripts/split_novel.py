#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_novel.py — 把长篇小说自动拆分成粗胚分块，并搭好 AI漫剧/短剧 生产目录骨架。
（注意：拆分只是脚手架，最终「集」边界由导演按戏剧节拍重切，一章≠一集。）

用法:
    python3 split_novel.py <小说路径> [选项]

常用选项:
    --by-chapter       按「第X章」边界+字数双约束切（更贴戏剧节拍）
    --per-chapter      每章独立成一集（最贴节拍；长章保持整章，精修时再拆）
    --keep-frontmatter 保留开头简介/标签/看点（默认自动剥离）
    --out 目录          作品根（默认=小说同级；小说在 …/小说/ 下时自动取其父）
    --target/--min/--max 每集目标/最小(尾段并入阈值)/最大 字数（默认 1000/800/1400）
    --name 标题         素材文件头用的标题（默认取小说文件名）

支持 .txt / .docx 输入。默认输出布局：
    <作品根>/_进度.md
    <作品根>/设定库/global_style.md
    <作品根>/设定库/characters/_角色总表.md
    <作品根>/设定库/locations/_场景总表.md
    <作品根>/脚本/第N集/{raw.txt 分镜剧本.md 故事板.md 素材清单.md
                         voiceover.txt bgm.txt 封面.md
                         字幕_中文.srt 字幕_英文.srt}
（出图/ 与 出视频/ 由 n2d-image 与 n2d-video 在后续阶段创建。）
开头的简介/标签/看点等元数据默认自动剥离（见 strip_frontmatter）。
"""
import argparse
import os
import re
import sys
import zipfile


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


def chunk_text(paras, target, hi, lo=None):
    """把段落列表合并成若干集，每集尽量接近 target 字，不超过 hi 太多，在段/句边界切。
    末尾残料若不足 lo 字（默认 target*0.5）则并入上一集。"""
    if lo is None:
        lo = target * 0.5
    episodes = []
    buf = []
    buf_len = 0
    for para in paras:
        # 超长段落先按句拆
        units = [para] if len(para) <= hi else split_sentences(para)
        for u in units:
            if buf and buf_len + len(u) > hi:
                episodes.append("\n".join(buf))
                buf, buf_len = [], 0
            buf.append(u)
            buf_len += len(u)
            if buf_len >= target:
                episodes.append("\n".join(buf))
                buf, buf_len = [], 0
    if buf:
        # 末尾残料并入上一集（若不足 lo）或独立成集
        tail = "\n".join(buf)
        if episodes and buf_len < lo:
            episodes[-1] = episodes[-1] + "\n" + tail
        else:
            episodes.append(tail)
    return episodes


def split_by_chapter(paras, target, hi, lo=None):
    """按「第X章」边界 + 字数双约束切集：

    - 在章节标题处优先断集，让分集贴近戏剧节拍；
    - 累积到 target 字才出一集；单章过长则用 chunk_text 再按句/段细拆；
    - 末尾过短的残料并入上一集。
    无章节标题时退回纯字数切分。
    """
    if lo is None:
        lo = target * 0.5
    chapters = []
    cur = []
    for p in paras:
        if CHAPTER_RE.match(p) and cur:
            chapters.append(cur)
            cur = [p]
        else:
            cur.append(p)
    if cur:
        chapters.append(cur)
    if len(chapters) <= 1:
        return chunk_text(paras, target, hi, lo)

    episodes = []
    buf, buf_len = [], 0
    for ch in chapters:
        ch_len = sum(len(p) for p in ch)
        if buf and buf_len + ch_len > hi:
            episodes.append("\n".join(buf))
            buf, buf_len = [], 0
        buf.extend(ch)
        buf_len += ch_len
        if buf_len >= target:
            if buf_len > hi:
                episodes.extend(chunk_text(buf, target, hi, lo))
            else:
                episodes.append("\n".join(buf))
            buf, buf_len = [], 0
    if buf:
        tail = "\n".join(buf)
        if episodes and buf_len < lo:
            episodes[-1] = episodes[-1] + "\n" + tail
        else:
            episodes.append(tail)
    return episodes


def split_per_chapter(paras, min_chars=100):
    """每章独立成一集（最贴戏剧节拍）；过短章节（疑似误判的标题行）并入上一集。

    无「第X章」标题时返回 None（由调用方退回字数切分）。
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


PLACEHOLDERS = {
    "分镜剧本.md": "# {title}_第{n}集_分镜剧本\n\n> 待精修：参考 references/formats.md「分镜剧本」格式逐镜头填写。\n",
    "故事板.md": "# {title}_第{n}集_故事板\n\n> 待精修：参考 references/formats.md「故事板 Clip 表」格式，供 AI 视频生成（平台档案见 references/platforms.md，默认即梦）。\n",
    "素材清单.md": "# {title}_第{n}集_素材清单\n\n> 待精修：参考 references/formats.md「素材清单」格式，供 AI 图片生成（中文为主+英文备用；平台档案见 references/platforms.md）。\n",
    "voiceover.txt": "# {title}_第{n}集_配音文案\n# 待精修：按镜头顺序填写旁白/台词，标注角色与情绪。\n",
    "bgm.txt": "# {title}_第{n}集_BGM与音效\n# 待精修：填写整体情绪、BGM风格、关键音效点。\n",
    "封面.md": "# {title}_第{n}集_封面/首图\n\n> 待精修：一张高点击率封面 prompt（中文+英文），含本集最大爽点/钩子。\n",
    "字幕_中文.srt": "1\n00:00:00,000 --> 00:00:03,000\n（待精修：依据 voiceover.txt 台词 + 故事板.md 镜头时长生成带时间码的中文字幕）\n",
    "字幕_英文.srt": "1\n00:00:00,000 --> 00:00:03,000\n(TODO: English subtitles for overseas platforms — TikTok / ReelShort / YouTube, timed to the storyboard)\n",
}


def write_if_absent(path, content):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("novel")
    ap.add_argument("--out", default=None,
                    help="作品根（直接包含 脚本/ 出图/ 出视频/ + 全局文件）。缺省：小说在 .../小说/<X> 下→取其父；否则落到最近含『制漫剧/』的仓库根下的 制漫剧/<剧名>/（找不到才回退小说同级并告警）")
    ap.add_argument("--target", type=int, default=1000, help="每集目标字数")
    ap.add_argument("--min", type=int, default=800, help="末尾残料不足此字数则并入上一集")
    ap.add_argument("--max", type=int, default=1400, help="每集字数上限（超出在段/句边界断开）")
    ap.add_argument("--name", default=None, help="标题（用于各素材文件头），默认取小说文件名")
    ap.add_argument("--by-chapter", action="store_true",
                    help="优先按「第X章」边界+字数双约束切集（更贴戏剧节拍）；无章节标题时自动退回纯字数切")
    ap.add_argument("--per-chapter", action="store_true",
                    help="每章独立成一集（最贴戏剧节拍，一章=一集；长章保持整章，精修时按上/下集再拆）；无章节标题时自动退回纯字数切")
    ap.add_argument("--keep-frontmatter", action="store_true",
                    help="保留开头的简介/标签/看点等元数据（默认自动剥离）")
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
            # novel2drama 产物应落 制漫剧/<剧名>/：向上找含『制漫剧/』的仓库根，
            # 避免把作品根误建在输入文件同级（如 写小说/<X>/导出/）。
            d, repo = novel_dir, None
            while True:
                if os.path.isdir(os.path.join(d, "制漫剧")):
                    repo = d
                    break
                parent = os.path.dirname(d)
                if parent == d:
                    break
                d = parent
            if repo:
                root = os.path.join(repo, "制漫剧", title)
            else:
                root = novel_dir
                print(f"[warn] 未找到含『制漫剧/』的仓库根，作品根回退到小说同级：{root}"
                      f"（建议用 --out 指定 制漫剧/<剧名>/）", file=sys.stderr)
    text = read_text(args.novel)
    paras = normalize_paragraphs(text)
    if not paras:
        sys.exit("未读到正文内容。")

    dropped = 0
    if not args.keep_frontmatter:
        before = len(paras)
        paras = strip_frontmatter(paras)
        dropped = before - len(paras)

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
        f"# {title} — 全局画风与世界观\n\n## 目标平台\n即梦AI（默认）；可选 可灵Kling / Seedance / Veo —— 平台档案见 references/platforms.md\n\n## 画风\n高质量国风AI漫剧风格，电影级光影，统一色调，高细节，动态漫画感。\n\n## 世界观\n（待精修）\n\n## 统一负面词\n（低幼Q版、画风漂移、多余文字水印 等）\n",
    )
    write_if_absent(
        os.path.join(settings, "characters", "_角色总表.md"),
        f"# {title} — 角色卡总表\n\n> 全篇首次出现即建卡，后续所有镜头严格复用。格式见 references/formats.md。\n",
    )
    write_if_absent(
        os.path.join(settings, "locations", "_场景总表.md"),
        f"# {title} — 场景卡总表\n\n> 全篇首次出现即建卡，后续镜头保持一致。格式见 references/formats.md。\n",
    )

    lengths = []
    for i, ep in enumerate(episodes, 1):
        ep_dir = os.path.join(root, "脚本", f"第{i}集")
        os.makedirs(ep_dir, exist_ok=True)
        write_if_absent(os.path.join(ep_dir, "raw.txt"), ep)
        for fname, tmpl in PLACEHOLDERS.items():
            write_if_absent(os.path.join(ep_dir, fname), tmpl.format(title=title, n=i))
        lengths.append(len(ep.replace("\n", "")))

    prog_lines = [f"# {title} — 生产进度\n", f"共拆分 **{len(episodes)}** 集。\n",
        "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, ln in enumerate(lengths, 1):
        prog_lines.append(f"| 第{i}集 | {ln} | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |")
    write_if_absent(os.path.join(root, "_进度.md"), "\n".join(prog_lines) + "\n")

    print(f"作品根: {root}")
    mode = "每章一集" if args.per_chapter else ("按章节+字数" if args.by_chapter else "按字数")
    print(f"切分方式：{mode}；剥离开头元数据 {dropped} 段。")
    print(f"共 {len(episodes)} 集，字数范围 {min(lengths)}~{max(lengths)}（目标 {args.target}）")
    print("目录骨架已生成。下一步：精修每集素材。")


if __name__ == "__main__":
    main()
