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
    --start-chapter N  从第N章开始粗切（可写 48 / 第48章 / 第四十八章；中段开工仍需先补前情资产包）
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

from n2d_const import GENRE_MIN_HITS, boundary_buckets, boundary_lexicon
from n2d_contract import PROGRESS_COLUMNS
from n2d_settings import DEFAULTS, get_setting, project_setting_source
from n2d_visual_styles import (
    format_style_contract_markdown,
    format_style_recommendation_markdown,
    recommend_style,
    style_options_text,
)
from source_analyze import render_character_roster, write_analysis

try:
    from motif_detector import detect_genre
except Exception:  # 题材检测不可用时不拖垮拆集；推荐器自动退化到通用默认。
    detect_genre = None  # type: ignore


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


CHAPTER_RE = re.compile(r"^\s*第\s*([0-9零〇一二三四五六七八九十百千万两]+)\s*[章回节卷]")
CHINESE_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
CHINESE_UNITS = {"十": 10, "百": 100, "千": 1000}

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


def parse_chapter_number(value):
    """Parse Arabic or common Chinese chapter numbers."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    m = re.search(r"第\s*([0-9零〇一二三四五六七八九十百千万两]+)\s*[章回节卷]", text)
    token = m.group(1) if m else text
    token = re.sub(r"^第", "", token)
    token = re.sub(r"[章回节卷]$", "", token)
    token = re.sub(r"[\s,，_、.-]", "", token)
    if token.isdigit():
        return int(token)
    if not token or any(ch not in CHINESE_DIGITS and ch not in CHINESE_UNITS and ch != "万" for ch in token):
        return None

    total = 0
    section = 0
    number = 0
    for ch in token:
        if ch in CHINESE_DIGITS:
            number = CHINESE_DIGITS[ch]
        elif ch in CHINESE_UNITS:
            unit = CHINESE_UNITS[ch]
            section += (number or 1) * unit
            number = 0
        elif ch == "万":
            section_value = section + number
            total += (section_value or 1) * 10000
            section = 0
            number = 0
    return total + section + number


def chapter_number_from_heading(para):
    m = CHAPTER_RE.match(para or "")
    if not m:
        return None
    return parse_chapter_number(m.group(1))


def trim_before_chapter(paras, chapter_spec):
    """Return paragraphs starting at the first chapter >= requested chapter."""
    target = parse_chapter_number(chapter_spec)
    if target is None or target < 1:
        raise ValueError(f"无法解析起始章节: {chapter_spec}")

    seen_chapter = False
    for i, para in enumerate(paras):
        chapter = chapter_number_from_heading(para)
        if chapter is None:
            continue
        seen_chapter = True
        if chapter >= target:
            return paras[i:], {
                "requested": target,
                "matched": chapter,
                "skipped_paras": i,
                "exact": chapter == target,
            }
    if not seen_chapter:
        raise ValueError("未识别到「第X章」章节标题，无法使用 --start-chapter")
    raise ValueError(f"未找到第{target}章或之后的章节标题")


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


def natural_scene_break(next_para, chapter_only=False):
    """下一段是否构成自然幕界。

    chapter_only=True（章节感知粗切·--by-chapter）：只认「第X章」章界，
    不把章内的场景分隔（---、【…】、翌日…）当幕界——否则系统流爽文里满屏的
    系统面板行 `【妖化：虎山神】` 会被误判成集边界，粗切成上千个百字微集。
    """
    if not next_para:
        return False
    if CHAPTER_RE.match(next_para):
        return True
    return not chapter_only and bool(SCENE_BREAK_RE.match(next_para))


def boundary_candidate(end_para, next_para=None, chapter_only=False):
    # 章节感知模式：章是原子粗胚单元，只在章界落点；不让章内的强钩句把一章劈碎
    # （古装动作的强钩词典很宽，否则一章会被切成多个百字微集）。
    if chapter_only:
        return natural_scene_break(next_para, chapter_only=True)
    return strong_episode_end(end_para) or natural_scene_break(next_para, chapter_only)


def loop_ready(text, end_para, next_para=None, chapter_only=False):
    """粗胚闭环启发式：有冲突、有释放/反转，并落在章节/场景/强钩候选处。"""
    return (
        boundary_candidate(end_para, next_para, chapter_only)
        and has_conflict(text)
        and has_payoff_or_reversal(text)
    )


def chunk_text(paras, target=None, hi=None, lo=None, chapter_aware=False):
    """连续性优先粗切：默认不锚字数，target/hi/lo 为旧参数兼容与报告参考。

    不再因为超过 max 或低于 min 硬切/硬并，也不再等到 target 才允许切。
    只有当前窗口出现「冲突→释放/反转→章节/场景/强钩候选」，才落一个粗胚分块；
    否则继续并入后文，交给精修阶段按 P0→P6 重切。

    chapter_aware=True（--by-chapter）：只在章界/强钩处落粗胚，忽略章内场景分隔，
    避免系统流满屏 `【…】` 系统行被当幕界而过度切碎。
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
        if loop_ready(text, para, next_para, chapter_only=chapter_aware):
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
    if any(CHAPTER_RE.match(p) for p in paras):
        return chunk_text(paras, target, hi, lo, chapter_aware=True)
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


def global_style_scaffold(title, root, recommendation=None):
    # 私有选择优先：_设置.md/全局默认里任何「非裸默认」的明确选择都尊重，不被推荐覆盖。
    # 只有「没人选过」（解析值 == 裸默认 且项目无 source）时，才用题材感知推荐填这个预选。
    resolved = get_setting(root, "基础视觉风格", DEFAULTS["基础视觉风格"])
    explicit = bool(project_setting_source(root, "基础视觉风格")) or resolved != DEFAULTS["基础视觉风格"]
    if explicit:
        base_style, origin = resolved, "来自 _设置.md/全局默认"
    elif recommendation and recommendation.get("recommended"):
        base_style, origin = recommendation["recommended"], "题材感知推荐（预选·可改）"
    else:
        base_style, origin = resolved, "全局默认"
    style_note = f"{base_style}（{origin}；可选 {style_options_text()}）"
    rec_block = ""
    if recommendation:
        rec_block = (
            "## 风格推荐依据\n"
            f"{format_style_recommendation_markdown(recommendation)}\n\n"
        )
    return (
        f"# {title} — 全局画风与世界观\n\n"
        "## 视频模型路由\n自动按镜头路由（首跑不选择具体生视频后端；n2d-video 阶段按 `video_model_routes.json` + CLI/API 探测决定 primary/fallback）\n\n"
        "## 生视频后端决策\n延后到 n2d-video 出视频前；若用户明确固定后端或账号/交付只能单后端，再写 `_设置.md` 的 `视频模型路由/生视频模型/生视频渠道`。\n\n"
        f"## 基础视觉风格\n{style_note}\n\n"
        f"{rec_block}"
        "## 画风\n高质量AI漫剧风格，统一色调，高细节；具体提示词随「基础视觉风格」派生。\n\n"
        "## 基础视觉风格契约（style_contract 源头）\n"
        f"{format_style_contract_markdown(base_style)}\n\n"
        "## 世界观\n（待精修）\n\n"
        "## 统一负面词\n（画风漂移、多余文字水印、多指错手、脸/妆造漂移；其余禁忌按「基础视觉风格」派生，例如未选Q版才禁低幼Q版，写实电影感才禁插画化）\n"
    )


def build_style_recommendation(paras, title, genre_setting):
    """题材感知风格推荐：detect_genre(正文) + 书名/题材自由文本 → 一个预选默认。

    纯产物用于 global_style_scaffold；检测器缺失时退化到通用默认（不阻断拆集）。
    """
    body = "\n".join(paras)
    genres = []
    if detect_genre is not None:
        try:
            gd = detect_genre(body)
            genres = [r["genre"] for r in gd.get("by_genre", []) if r.get("hits", 0) >= GENRE_MIN_HITS]
        except Exception:
            genres = []
    genre_text = " ".join([title or "", genre_setting or "", body[:20000]])
    return recommend_style(genres, genre_text)

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
    ap.add_argument("--start-chapter", default=None,
                    help="从第N章开始粗切（可写 48 / 第48章 / 第四十八章）。仅裁本次 raw 脚手架；中段开工仍需先补 设定库/中段开工前情资产包.md")
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
            # n2d 产物应落 创作区/制漫剧/<剧名>/：向上找最近的归属锚，
            # 避免把作品根误建在输入文件同级。区分两类锚，别把 创作区/ 当仓库根再拼一层：
            #   - d 含 创作区/制漫剧 或 skills → d 是仓库根 → root = d/创作区/制漫剧/title
            #   - d 直接含 制漫剧（即 d 本身就是 创作区/ 目录）→ root = d/制漫剧/title
            d, root = novel_dir, None
            while True:
                if (
                    os.path.isdir(os.path.join(d, "创作区", "制漫剧"))
                    or os.path.isdir(os.path.join(d, "skills"))
                ):
                    root = os.path.join(d, "创作区", "制漫剧", title)
                    break
                if os.path.isdir(os.path.join(d, "制漫剧")):
                    root = os.path.join(d, "制漫剧", title)
                    break
                parent = os.path.dirname(d)
                if parent == d:
                    break
                d = parent
            if root is None:
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

    start_info = None
    if args.start_chapter:
        try:
            paras, start_info = trim_before_chapter(paras, args.start_chapter)
        except ValueError as exc:
            sys.exit(str(exc))

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
    source_analysis = write_analysis(root, title, "\n".join(paras), episodes)

    style_rec = build_style_recommendation(paras, title, genre)
    write_if_absent(
        os.path.join(settings, "global_style.md"),
        global_style_scaffold(title, root, recommendation=style_rec),
    )
    write_if_absent(
        os.path.join(settings, "characters", "_角色总表.md"),
        render_character_roster(title, source_analysis),
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
            # 奇观连续性默认 —（na·不挡 flow）：拆集时未知本集有无奇观镜，image_prompt prework
            # 生成序列总账后回写 ✅（有奇观且覆盖）或保持 —（无奇观）。
            if "奇观连续性" in PROGRESS_COLUMNS:
                cells[PROGRESS_COLUMNS.index("奇观连续性")] = "—"
            fresh[i] = "| " + " | ".join(cells) + " |"
        rows = {**fresh, **existing_rows}  # 旧勾选优先，保留人工进度
        made = max(rows) if rows else n_make
        start_header = ""
        if start_info:
            start_header = f"（从第{start_info['matched']}章起）"
        est_scope = "本窗口" if start_info else "全本"
        header = (f"# {title} — 生产进度\n",
                  f"已粗切 **{made}** 集{start_header}"
                  + (f"（{est_scope}约估 {total_est} 集；部分先切，精修验证后重跑 split 加大 --limit 续切）。\n"
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
    if start_info:
        approx_note = "" if start_info["exact"] else f"（未找到精确章号，使用之后最近的第{start_info['matched']}章）"
        print(f"起始章节：请求第{start_info['requested']}章，实际从第{start_info['matched']}章开始，跳过 {start_info['skipped_paras']} 段{approx_note}。")
    if partial:
        est_scope = "本窗口" if start_info else "全本"
        print(f"部分先切：已落地前 {n_make} 集（{est_scope}按候选断点约估 {total_est} 集）。"
              f"字数范围 {min(lengths)}~{max(lengths)}{target_note}；无硬上下限")
        print(f"下一步：精修第1集验证节拍/画风/角色卡；满意后重跑 split 加大 --limit 续切（旧集与进度勾选保留）。")
    else:
        scope_note = "本窗口共" if start_info else "共"
        print(f"{scope_note} {n_make} 集，字数范围 {min(lengths)}~{max(lengths)}{target_note}；无硬上下限")
        print("目录骨架已生成。下一步：精修每集素材。")
    hints = [f"第{i}集 {length_hint(n)}" for i, n in enumerate(lengths, 1) if length_hint(n)]
    if hints:
        tail = "；…" if len(hints) > 8 else ""
        print("字数提示（仅复核，不参与切点）： " + "；".join(hints[:8]) + tail)


if __name__ == "__main__":
    main()
