#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel-review 机检：对已写章节做确定性质检，输出问题清单（不做判断题，那是 LLM 的活）。

用法:
    python3 mechanical_check.py <作品根> [--pov 王敦] [--min 800] [--max 1800] \
        [--terms "金丹,道障,王敦密码,烈阳花"] [--no-auto-terms] [--no-plagiarism]

检查项：
  1. 格式：每章有 H1 标题 `# 第N章 标题`（N 可阿拉伯/中文数字，标题可带《》或裸标题）+ meta 注释头
  2. 字数：CJK 字数在项目带宽内（优先 _meta.target_wordcount_min_max / scale.min_max；
     --min/--max 可覆盖；旧项目无元数据时回退 800-1800）
  3. 视角"我"密度：引号外出现的"我"计数（第三人称限定下交 LLM 抽查）
  4. 章号连续性：与 章节/ 目录里其他章是否有缺号/重号；与 设定/章纲.md 标题是否一致
  5. 术语出现统计：自动从 设定/ 抽术语，也可用 --terms 追加（供人工看漂移）
  6. 原文照搬：24 字滑窗与 原作.txt 比对，命中即报（续写/外传用；--no-plagiarism 关闭）
  7. 模板化行文候选（兼容维度名 AI腔）：议论文连接词=🟡、万能套话密度=🟢、句长过于均匀=🟡
     （advisory；不得用来判断作者身份、平台审核结论或真实读者反应；--no-ai-tell 关闭）

输出：人类可读清单 + 末尾机器可读 JSON（FINDINGS=[...]）。
"""
import argparse, json, os, re, sys, glob
from datetime import date

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from text_utils import cjk_count, strip_quotes  # noqa: E402  vendored 进 novel/_lib
from novel_contract import scale_profile, wordcount_band_for_words_per_chapter  # noqa: E402
# 跨章重复率/机械文风：单一真值源在 novel/_lib/repetition.py（novel-score 也消费同一套）
from repetition import (  # noqa: E402
    adjacent_chapter_jaccard, cross_chapter_repetition,
    REP_ADJ_JACCARD_YELLOW, REP_ADJ_JACCARD_GREEN, REP_OPENER_PREFIX,
)

# 章号数字：阿拉伯 / 全角 / 中文数字都接受（# 第1章 / # 第一章 / # 第 12 章 均合规）
CH_NUM = r"[0-9０-９一二三四五六七八九十百千零〇两]+"


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _int_pair(value):
    try:
        lo, hi = [int(x) for x in value[:2]]
    except (TypeError, ValueError):
        return None
    if lo <= 0 or hi <= 0:
        return None
    return [min(lo, hi), max(lo, hi)]


def resolve_wordcount_band(root, explicit_min=None, explicit_max=None):
    """Resolve review word-count band from project metadata, then CLI overrides."""
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    band = _int_pair(meta.get("target_wordcount_min_max"))
    source = "_meta.target_wordcount_min_max"
    if band is None and meta.get("scale"):
        try:
            band = scale_profile(meta.get("scale")).get("min_max")
            source = f"scale:{meta.get('scale')}.min_max"
        except Exception:
            band = None
    if band is None and meta.get("target_words_per_chapter"):
        band = wordcount_band_for_words_per_chapter(meta.get("target_words_per_chapter"))
        source = "_meta.target_words_per_chapter→derived"
    if band is None:
        band = [800, 1800]
        source = "fallback:legacy_manga"
    if explicit_min is not None:
        band[0] = int(explicit_min)
        source += "+cli_min"
    if explicit_max is not None:
        band[1] = int(explicit_max)
        source += "+cli_max"
    if band[0] > band[1]:
        band[0], band[1] = band[1], band[0]
    return band[0], band[1], source


def body_of(md):
    """去掉 H1 标题行与 meta 注释，取正文。"""
    lines = md.split("\n")
    body = [l for l in lines if not l.startswith("# 第") and not l.strip().startswith("<!--")]
    return "\n".join(body).strip()


# ── 模板化行文 / 同质化启发式（兼容 API 名 ai_tell_scan；advisory）──
# 这些信号只定位可能出戏、套话或节奏单调的文本，绝不用于作者身份归因或模拟平台检测器。
# 写时由 trio-pipeline 的 Senior Editor「去AI味」滤网兜，这里是 QA 侧确定性兜底，把主观项降成可机检线索。
# 2026-06-25 扩展至 15 类检测（P2-⑩），对标 ProseForge ANTI-SLOP / autonovel 行业基准。
AI_EXPOSITORY = ("综上所述", "总而言之", "总的来说", "归根结底", "众所周知", "不可否认",
                 "值得一提的是", "值得注意的是", "由此可见", "显而易见", "换言之", "不仅如此")
AI_CLICHE = ("命运的齿轮", "仿佛整个世界", "空气仿佛凝固", "时间仿佛静止", "或许这就是",
             "也许这就是", "不为人知的秘密", "在这个瞬间", "心中五味杂陈", "心中百感交集")
# 新增 2026-06-25：15 类扩展
AI_WEAK_ADVERBS = ("微微", "淡淡", "缓缓", "轻轻", "默默", "悄悄", "渐渐", "慢慢", "深深", "浅浅")
AI_X_NOT_X = ("不是", "而是")  # "不是X而是Y" 双关键词共现
AI_EMDASH = "——"              # 破折号滥用：每千字 > 5 个
AI_SENSORY_TRICOLON = ("视觉", "听觉", "触觉", "嗅觉", "味觉")  # 感官三连：一段内 3+ 感官
AI_FILTER_WORDS = ("看到", "听到", "感到", "注意到", "发现", "觉得", "意识到", "察觉到")
AI_BUJIN = ("不禁", "仿佛", "映入眼帘", "嘴角微扬", "心中一动", "不由得", "忍不住", "下意识地")
AI_INFLATION = ("意义深远", "前所未有", "史无前例", "震撼人心", "永恒的", "不朽的", "流传千古")
AI_CONCLUSION = ("未来可期", "充满希望", "一切才刚刚开始", "这才只是开始", "更好的明天", "新的篇章")
AI_FORMAL_INVASION = ("于是乎", "与此同时", "从而", "故而", "是以", "故此", "因而", "由此可见")
AI_PARALLEL_TRIAD = 3  # 段落内连续 3 个 "、/，" 分隔的三连以上排比
AI_SUMMARY_ENDING = ("总之", "总的来说", "综上所述", "归根到底", "简而言之", "一言以蔽之")
AI_IN_THAT_MOMENT = ("在那一刻", "在这一刻", "在这一瞬间", "就在此时", "此时此刻")


def sentence_lengths(text):
    """按句末标点切句，返回每个非空句的 CJK 字数列表（纯函数·可测）。"""
    parts = re.split(r"[。！？!?…\n]+", text or "")
    return [n for n in (cjk_count(p) for p in parts) if n >= 2]


def sentence_burstiness(text, min_sentences=8):
    """句长突变度（burstiness）的可机检代理。返回 (cv, n)。

    CV（句长标准差/均值）只衡量当前样本的句长变化，不是写作质量、作者身份或平台算法代理。
    句数不足 `min_sentences` 时返回 (None, n)。"""
    lens = sentence_lengths(text)
    n = len(lens)
    if n < min_sentences:
        return None, n
    mean = sum(lens) / n
    if mean <= 0:
        return None, n
    var = sum((x - mean) ** 2 for x in lens) / n
    return (var ** 0.5) / mean, n


def _count_cjk_words(text, words):
    """统计一组词在文本中的总出现次数。"""
    return sum(text.count(w) for w in words)


def _per_k(count, cjk_chars):
    """每千 CJK 字的密度。"""
    return count / max(1, cjk_chars) * 1000.0


def ai_tell_scan(body, cliche_per_k=3.0, burstiness_cv_floor=0.35):
    """模板化行文/同质化启发式（兼容旧函数名；纯函数·advisory）。

    扩展至 15 类检测（2026-06-25 P2-⑩）：
    ① 议论文式连接词 → 🟡  ② 万能金句/套话密度 → 🟢
    ③ 句长 burstiness 低 → 🟡  ④ 弱化副词泛滥 → 🟢
    ⑤ "不是X而是Y" 句式 → 🟡  ⑥ 破折号滥用 → 🟢
    ⑦ 感官三连 → 🟢          ⑧ 过滤词密度 → 🟡
    ⑨ "不禁/仿佛" 类高频 → 🟡  ⑩ 意义膨胀套话 → 🟢
    ⑪ 通用结论套话 → 🟢        ⑫ 正式语体入侵 → 🟡
    ⑬ 排比三连过多 → 🟢        ⑭ 总结式收尾 → 🟡
    ⑮ "在那一刻" 模式 → 🟡
    绝不 🔴（容错铁律）；线索非定论，仍需人判结合语境。"""
    text = body or ""
    cc = max(1, cjk_count(text))
    out = []

    # ① 议论文式连接词
    expo = [w for w in AI_EXPOSITORY if w in text]
    if expo:
        out.append(("🟡", f"叙事中出现议论文式连接词，复核是否出戏：{'、'.join(expo[:5])}", "、".join(expo[:5])))

    # ② 万能金句/套话密度
    n = _count_cjk_words(text, AI_CLICHE)
    if _per_k(n, cc) >= cliche_per_k:
        top = sorted({w for w in AI_CLICHE if w in text}, key=lambda w: -text.count(w))[:5]
        out.append(("🟢", f"AI 套话/万能金句密度偏高（{_per_k(n, cc):.1f}/千字）：{'、'.join(top)}", "、".join(top)))

    # ③ Burstiness
    cv, sent_n = sentence_burstiness(text)
    if cv is not None and cv < burstiness_cv_floor:
        out.append(("🟡", f"句长过于均匀（burstiness 低·CV={cv:.2f}/{sent_n}句）；建议长短句交错、插入碎句/短促对白破匀", f"CV={cv:.2f}"))

    # ④ 弱化副词泛滥（每千字 > 8 个）
    weak_n = _count_cjk_words(text, AI_WEAK_ADVERBS)
    if _per_k(weak_n, cc) > 8:
        top = sorted({w for w in AI_WEAK_ADVERBS if w in text}, key=lambda w: -text.count(w))[:5]
        out.append(("🟢", f"弱化副词过多（{_per_k(weak_n, cc):.1f}/千字）：{'、'.join(top)}。建议复核是否可用具体动作替代", "、".join(top)))

    # ⑤ "不是X而是Y" 句式（高频时容易形成机械化二元对比）
    if AI_X_NOT_X[0] in text and AI_X_NOT_X[1] in text:
        count = min(text.count(AI_X_NOT_X[0]), text.count(AI_X_NOT_X[1]))
        if _per_k(count, cc) > 1.5:
            out.append(("🟡", f"「不是…而是…」二元对比句式偏多（{count} 处）；复核是否改为单侧重、并置或动作展开", f"{count}处"))

    # ⑥ 破折号滥用（每千字 > 5 个）
    em_count = text.count(AI_EMDASH)
    if _per_k(em_count, cc) > 5:
        out.append(("🟢", f"破折号「——」密度偏高（{_per_k(em_count, cc):.1f}/千字）；复核是否有万能停顿或补充语过载", f"{em_count}个"))

    # ⑦ 感官三连（一段内出现 3+ 感官词密集堆砌）
    para_sensory = 0
    for para in text.split("\n"):
        if sum(1 for s in AI_SENSORY_TRICOLON if s in para) >= 3:
            para_sensory += 1
    if para_sensory > 0:
        out.append(("🟢", f"感官标签堆叠候选——段落内同时出现 3+ 感官词（{para_sensory} 段）；回正文判断是否具体有效", f"{para_sensory}段"))

    # ⑧ 过滤词密度（每千字 > 5 个）——提示是否可把感知结果直接写出
    filter_n = _count_cjk_words(text, AI_FILTER_WORDS)
    if _per_k(filter_n, cc) > 5:
        top = sorted({w for w in AI_FILTER_WORDS if w in text}, key=lambda w: -text.count(w))[:5]
        out.append(("🟡", f"过滤词密度偏高（{_per_k(filter_n, cc):.1f}/千字）：{'、'.join(top)}。复核是否删滤镜、直接写感知结果", "、".join(top)))

    # ⑨ "不禁/仿佛/映入眼帘" 类——高频套语候选
    bujin_hits = [w for w in AI_BUJIN if w in text]
    if _per_k(len(bujin_hits), cc) > 2:
        out.append(("🟡", f"「不禁/仿佛/映入眼帘」类 AI 高频腔（{len(bujin_hits)} 种词）：{'、'.join(bujin_hits[:5])}。替换为身体微反应/环境映衬", "、".join(bujin_hits[:5])))

    # ⑩ 意义膨胀套话——强行拔高（每千字 > 1）
    infl_hits = [w for w in AI_INFLATION if w in text]
    if infl_hits:
        out.append(("🟢", f"意义膨胀套话：{'、'.join(infl_hits[:4])}。删除标签式拔高，用具体影响替代", "、".join(infl_hits[:4])))

    # ⑪ 通用结论套话——AI 偏爱积极收束
    concl_hits = [w for w in AI_CONCLUSION if w in text]
    if concl_hits:
        out.append(("🟢", f"通用结论套话：{'、'.join(concl_hits[:4])}。用具体悬念/未解决的冲突结尾", "、".join(concl_hits[:4])))

    # ⑫ 正式语体入侵——AI 在叙事中误用议论文/公文体连接词
    formal_hits = [w for w in AI_FORMAL_INVASION if w in text]
    if formal_hits:
        out.append(("🟡", f"正式语体入侵——叙事中出现公文/论文连接词：{'、'.join(formal_hits[:4])}。改为口语化/行动化表达", "、".join(formal_hits[:4])))

    # ⑬ 排比三连过多（> 3 段出现连续 3+ "、" 分隔的短语）
    triad_paras = 0
    for para in text.split("\n"):
        if para.count("、") >= 2 and len(para) > 30:
            # 简单代理：一段内顿号 ≥ 2 + 段落足够长 → 疑似三连排比
            triad_paras += 1
    if triad_paras > 3:
        out.append(("🟢", f"排比三连段落偏多（{triad_paras} 段疑似）；精简装饰性排比，保留有节奏功能的修辞", f"{triad_paras}段"))

    # ⑭ 总结式收尾——章节末段出现 AI 总结口吻
    last_para = text.split("\n")[-1] if text else ""
    summary_hits = [w for w in AI_SUMMARY_ENDING if w in last_para]
    if summary_hits:
        out.append(("🟡", f"章节末段总结式收尾：{'、'.join(summary_hits)}。复核是否改为行动、钩子或情绪余韵", "、".join(summary_hits)))

    # ⑮ "在那一刻/此时此刻" 模式——AI 情绪高点万能模板
    moment_hits = [w for w in AI_IN_THAT_MOMENT if w in text]
    if moment_hits:
        out.append(("🟡", f"「在那一刻」模式——AI 情绪高潮万能模板（{len(moment_hits)} 处）。替换为角色微动作/环境异常/具体感受", "、".join(moment_hits[:3])))

    return out


def load_outline_titles(root):
    """从 设定/章纲.md 抽 {章号: 标题}（匹配 '第 N 章 《标题》'）。"""
    f = os.path.join(root, "设定", "章纲.md")
    titles = {}
    if os.path.exists(f):
        for m in re.finditer(r"第\s*0*(\d+)\s*章\s*[《<]([^》>]+)[》>]", read(f)):
            titles.setdefault(int(m.group(1)), m.group(2))
    return titles


def extract_terms_from_settings(root):
    """Best-effort canonical term extraction from setting-bible files."""
    terms = set()
    setting_dir = os.path.join(root, "设定")
    # 人物.md 是派生线（continue/expand）的角色卡命名，与 角色卡.md 同义并列读取。
    md_files = ["设定圣经.md", "角色卡.md", "人物.md", "世界观.md", "作者口吻.md", "创作蓝图.md"]
    for fname in md_files:
        path = os.path.join(setting_dir, fname)
        if not os.path.exists(path):
            continue
        text = read(path)
        for m in re.finditer(r"[《「『`“]([^》」』`”]{2,24})[》」』`”]", text):
            cand = _strip_md(m.group(1).strip())
            if _term_like(cand):  # 「」里多是对白/口吻样本，过 _term_like 滤掉句子片段
                terms.add(cand)
        for line in text.splitlines():
            raw = line.strip()
            if not raw or raw.startswith(("---", "|---")):
                continue
            if raw.startswith("|"):
                cols = [c.strip() for c in raw.strip("|").split("|")]
                if cols and cols[0] not in ("字段", "项目", "术语", "名称", "角色", "锚点 ID"):
                    maybe = _strip_md(re.sub(r"\s+", "", cols[0]))
                    if _term_like(maybe):
                        terms.add(maybe)
            elif raw.startswith(("- ", "* ")):
                head = _strip_md(re.split(r"[:：—-]", raw[2:].strip(), maxsplit=1)[0].strip())
                if _term_like(head):
                    terms.add(head)
    anchor_path = os.path.join(setting_dir, "锚点表.json")
    if os.path.exists(anchor_path):
        try:
            data = json.loads(read(anchor_path))
            _collect_json_terms(data, terms)
        except json.JSONDecodeError:
            pass
    return sorted(terms, key=lambda x: (len(x), x))


def load_confirmed_entity_terms(root):
    """读 设定/角色别名.json（status==confirmed）→ 人工**已确认**的实体名集合（规范名 + 别名）。

    这是术语漂移统计的**权威源**：人确认过的角色名/别名直接采信，绕过 `_term_like` 正则启发式
    （正则会漏掉或切坏含中点/单字/带「的之」的合法专名）。缺文件/未确认（draft）→ 空集，
    退化为纯正则抽取（完全向后兼容）。文件由 novel-wiki/alias_scaffold.py 生成候选、人确认，
    与 graph_sentry/load_curated_alias_map 同一真值源（闭合"抽取→人确认→消费"环）。"""
    data = load_json(os.path.join(root, "设定", "角色别名.json"))
    if not isinstance(data, dict) or str(data.get("status") or "").strip().lower() != "confirmed":
        return set()
    terms = set()
    ca = data.get("character_aliases")
    if isinstance(ca, dict):  # {别名: 规范名}
        for alias, canon in ca.items():
            terms.add(str(alias).strip())
            terms.add(str(canon).strip())
    chars = data.get("characters")
    if isinstance(chars, list):  # [{name/canonical, aliases/别名/also_known_as: [...]}]
        for c in chars:
            if not isinstance(c, dict):
                continue
            name = c.get("name") or c.get("canonical") or c.get("规范名")
            if name:
                terms.add(str(name).strip())
            al = c.get("aliases") or c.get("别名") or c.get("also_known_as") or []
            if isinstance(al, list):
                terms.update(str(a).strip() for a in al)
    al = data.get("aliases")
    if isinstance(al, dict):  # {规范名: [别名...]}
        for canon, lst in al.items():
            terms.add(str(canon).strip())
            if isinstance(lst, list):
                terms.update(str(a).strip() for a in lst)
    return {t for t in terms if t}


def _strip_md(value):
    """剥掉 markdown 强调标记与首部清单/编号/复选框记号，露出可能的术语本体。

    设定文件常把术语写成 `- **烈阳花**：…` 或 `- [ ] 2. 家世…`；不剥这些前缀，
    抽出来的就是 `**烈阳花**` / `[ ] 2. 家世…` 这类带标记的脏串（术语表噪声根因）。
    """
    value = (value or "").strip()
    value = re.sub(r"^[-*+]\s*", "", value)        # 列表符
    value = re.sub(r"^\[[ xX]?\]\s*", "", value)   # 复选框 [ ] [x]
    value = re.sub(r"^\d+\s*[.、)]\s*", "", value)  # 编号 1. 2、 3)
    return value.strip("`*_~ ").strip()


# 术语本体里出现这些字符 → 句子片段/带标记标题/短语标签，不是规范术语
_NON_TERM_CHARS = re.compile(r"[\s*`_~\[\](){}（）【】《》「」：:；;，,。.！!？?、…—\-#|/\\\"'“”·•]")
# 含这些功能词 → 描述性短语而非名词术语（如 “气运即金手指即催命符”）
_PHRASE_WORDS = re.compile(r"[的即是和与或把被让之者]")
_CONFIG_TERM_DENYLIST = {
    "meta", "manual-evidence", "目标平台", "目标用途", "小说用途", "输出格式",
    "市场基准", "题材类型", "规模档", "人称视角", "文本主创模式", "目标语言",
    "本书差异化", "常用策略", "样本素材", "规范写法", "漫剧转制待办",
}


def _term_like(value):
    value = (value or "").strip()
    if not (2 <= len(value) <= 18):
        return False
    if value in {"首现章", "复用范围", "代价或约束", "说明", "状态", "标题"} | _CONFIG_TERM_DENYLIST:
        return False
    if _NON_TERM_CHARS.search(value) or _PHRASE_WORDS.search(value):
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]", value))


def _collect_json_terms(value, terms):
    if isinstance(value, dict):
        # 只从「实体/在场人」类字段抽术语（多是人名/地名列表）；event/known/time 等是散文，
        # 拆出来全是句子片段，污染术语表——这些字段的字符串值不当术语，仅在其为 dict/list 时递归。
        entity_keys = {"present_with", "在场人", "在场", "characters", "角色", "named", "names"}
        for key, val in value.items():
            if key in entity_keys:
                _collect_json_terms(val, terms)
            elif isinstance(val, (dict, list)):
                _collect_json_terms(val, terms)
    elif isinstance(value, list):
        for item in value:
            _collect_json_terms(item, terms)
    elif isinstance(value, str):
        for part in re.split(r"[，,、/\s]+", value):
            part = part.strip()
            if _term_like(part):
                terms.add(part)


def build_shingles(text, n=24):
    text = re.sub(r"\s+", "", text)
    return {text[i:i + n] for i in range(0, max(0, len(text) - n + 1))}


def plagiarism_check_policy(root):
    """Return (enabled, reason) for source-copy checks.

    `原作.txt` is an external-source plagiarism baseline for derivative projects,
    but an imported/canonical manuscript may also be split into `章节/`. In that
    case every chapter naturally matches the canonical source, so the project
    must opt out explicitly via metadata.
    """
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    review = meta.get("review") if isinstance(meta.get("review"), dict) else {}
    mode = str(
        review.get("plagiarism_check")
        or meta.get("plagiarism_check")
        or ""
    ).strip().lower()
    if mode in {"skip_canonical_source", "canonical_source", "off", "disabled"}:
        return False, f"_meta.review.plagiarism_check={mode}"
    if str(meta.get("kind") or "").strip().lower() == "import":
        return False, "_meta.kind=import（章节为规范源拆分稿）"
    return True, "enabled"


def chapter_number_from_path(path):
    match = re.search(r"第0*(\d+)章", os.path.basename(path))
    return int(match.group(1)) if match else None


def chapter_sort_key(path):
    number = chapter_number_from_path(path)
    return (number is None, number or 0, os.path.basename(path))


def parse_range(value):
    if not value:
        return None
    text = str(value).strip()
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
    elif text.isdigit():
        start = end = int(text)
    else:
        raise ValueError("--range 应为 N 或 N-M")
    if end < start:
        raise ValueError("--range 结束章不能小于开始章")
    return start, end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--range", dest="chapter_range", default=None,
                    help="只检查指定章节范围，如 1-5；缺省检查全部章节")
    ap.add_argument("--pov", default=None, help="第三人称限定的 POV 角色名（用于'我'泄漏提示）")
    ap.add_argument("--min", type=int, default=None,
                    help="覆盖字数下限；缺省自动读取项目 _meta")
    ap.add_argument("--max", type=int, default=None,
                    help="覆盖字数上限；缺省自动读取项目 _meta")
    ap.add_argument("--terms", default="", help="逗号分隔的规范术语，统计各章出现次数")
    ap.add_argument("--no-auto-terms", action="store_true",
                    help="不从 设定/ 自动抽取术语，只使用 --terms")
    ap.add_argument("--no-plagiarism", action="store_true")
    ap.add_argument("--no-ai-tell", action="store_true",
                    help="关闭模板化行文/同质化启发式（兼容名 AI腔；默认开，advisory）")
    ap.add_argument("--no-repetition", action="store_true",
                    help="关闭跨章重复率/机械文风机检（默认开；advisory，治平台连续章节重复率检测）")
    ap.add_argument("--json-out", default=None,
                    help="可选：把机检结果写成 JSON，供 review_report.json 汇总")
    args = ap.parse_args()

    chdir = os.path.join(args.root, "章节")
    if not os.path.isdir(chdir):
        sys.exit(f"找不到章节目录：{chdir}")
    min_words, max_words, wordcount_source = resolve_wordcount_band(args.root, args.min, args.max)

    try:
        rng = parse_range(args.chapter_range)
    except ValueError as exc:
        sys.exit(f"[err] {exc}")
    files = sorted(glob.glob(os.path.join(chdir, "第*章*.md")), key=chapter_sort_key)  # 第N章.md 或 第N章_标题.md
    if rng:
        start, end = rng
        files = [
            path for path in files
            if (chapter_number_from_path(path) is not None and start <= chapter_number_from_path(path) <= end)
        ]
    nums = []
    for f in files:
        m = re.search(r"第0*(\d+)章", os.path.basename(f))
        if m:
            nums.append(int(m.group(1)))
    outline = load_outline_titles(args.root)
    manual_terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    # 权威源优先：人确认的实体表（角色别名.json·confirmed）直接采信，绕过 _term_like 正则启发式；
    # 正则抽取退化为补充（覆盖法宝/地名/功法等非角色术语）。缺确认表则纯正则，向后兼容。
    confirmed_terms = [] if args.no_auto_terms else sorted(load_confirmed_entity_terms(args.root))
    auto_terms = [] if args.no_auto_terms else extract_terms_from_settings(args.root)
    terms = sorted(set(manual_terms + confirmed_terms + auto_terms), key=lambda x: (len(x), x))

    # 原文照搬：预载原作滑窗集
    src_shingles = None
    plagiarism_enabled, plagiarism_reason = plagiarism_check_policy(args.root)
    src_path = os.path.join(args.root, "原作.txt")
    if not args.no_plagiarism and plagiarism_enabled and os.path.exists(src_path):
        src_shingles = build_shingles(read(src_path), 24)
    elif args.no_plagiarism:
        plagiarism_reason = "cli --no-plagiarism"

    findings = []
    pov_density = {}
    chapter_bodies = []  # [(章号, 正文)]，供跨章重复率机检（需全章一起看）

    def add(ch, sev, dim, msg, ev=""):
        findings.append({"chapter": ch, "severity": sev, "dim": dim, "msg": msg, "evidence": ev[:40]})

    # 章号连续性
    if nums:
        full = set(range(rng[0], rng[1] + 1)) if rng else set(range(min(nums), max(nums) + 1))
        miss = sorted(full - set(nums))
        dup = sorted({n for n in nums if nums.count(n) > 1})
        if miss:
            add(0, "🟡", "章号", f"缺号：{miss}")
        if dup:
            add(0, "🔴", "章号", f"重号：{dup}")

    for f in files:
        m = re.search(r"第0*(\d+)章", os.path.basename(f))
        ch = int(m.group(1)) if m else 0
        md = read(f)
        # 1 格式：H1 需是 `# 第N章 …`，N 可为阿拉伯或中文数字，标题可带《》或裸标题
        if not re.search(r"^#\s*第\s*" + CH_NUM + r"\s*章", md, re.M):
            add(ch, "🔴", "格式", "缺规范 H1 标题 `# 第N章 标题`（N 可中文/阿拉伯数字）")
        if "<!--" not in md:
            add(ch, "🟢", "格式", "缺 meta 注释头")
        # 标题与章纲一致（兼容《…》与裸标题两种写法）
        mt = re.search(r"^#\s*第\s*" + CH_NUM + r"\s*章\s*(?:[《<]([^》>]+)[》>]|([^\n]*))$", md, re.M)
        title = (mt.group(1) or mt.group(2) or "").strip() if mt else ""
        if mt and ch in outline and title != outline[ch].strip():
            add(ch, "🟡", "标题", f"标题与章纲不符：正文「{title}」 vs 章纲「{outline[ch]}」")
        is_demo = "demo=true" in md
        body = body_of(md)
        chapter_bodies.append((ch, body))
        # 2 字数（demo 特长开篇豁免带宽）
        wc = cjk_count(body)
        if not is_demo:
            if wc < min_words:
                add(ch, "🟡", "字数", f"偏短 {wc} 字（<{min_words}；带宽来源 {wordcount_source}）")
            elif wc > max_words:
                add(ch, "🟡", "字数", f"偏长 {wc} 字（>{max_words}；带宽来源 {wordcount_source}）")
        # 3 钩子 = 判断题，交 LLM（见 checklist.md 维度5）；机检不报，避免误判好钩子。
        # 4 视角"我"密度：内心独白（——我…/自由直接引语）在第三人称限定里合法，机检无法
        #    可靠区分"合法独白"与"真串视角"——这是判断题，交 LLM。机检只收集密度，末尾给一条
        #    抽查建议（指向密度最高的章），不当 🟡 噪声刷屏。
        if args.pov:
            outside = strip_quotes(body)
            mono_removed = re.sub(r"[—－]{1,2}[^\n。！？!?…]*", "", outside)
            pov_density[ch] = mono_removed.count("我")
        # 5 术语统计（仅记录，供人看漂移）
        # 6 原文照搬
        if src_shingles is not None:
            bsh = re.sub(r"\s+", "", body)
            hit = None
            for i in range(0, max(0, len(bsh) - 24 + 1), 6):
                w = bsh[i:i + 24]
                if w in src_shingles:
                    hit = w
                    break
            if hit:
                add(ch, "🔴", "原文照搬", "发现与原作连续雷同片段（≥24字）", hit)
        # 7 模板化行文/同质化（兼容维度名 AI腔；advisory，不能做作者身份归因）
        if not args.no_ai_tell:
            for sev, msg, ev in ai_tell_scan(body):
                add(ch, sev, "AI腔", msg, ev)

    # 跨章重复率/机械文风（需全章一起看·advisory·绝不 🔴）
    repetition_summary = None
    if not args.no_repetition and len(chapter_bodies) >= 2:
        rep_findings, repetition_summary = cross_chapter_repetition(
            sorted(chapter_bodies, key=lambda kv: kv[0]))
        for ch, sev, dim, msg, ev in rep_findings:
            add(ch, sev, dim, msg, ev)

    # 术语出现矩阵（单列打印，不进 findings）
    term_matrix = {}
    if terms:
        for f in files:
            ch = int(re.search(r"第0*(\d+)章", os.path.basename(f)).group(1))
            md = read(f)
            term_matrix[ch] = {t: md.count(t) for t in terms}

    # ---- 输出 ----
    print(f"# 机检报告 — {args.root}")
    if rng:
        print(f"范围：第{rng[0]}-{rng[1]}章")
    print(f"章节数：{len(files)}（{min(nums) if nums else '-'}–{max(nums) if nums else '-'}）"
          f" | POV：{args.pov or '未指定'} | 原文照搬检查：{'开' if src_shingles is not None else '关'}")
    if src_shingles is None and os.path.exists(src_path):
        print(f"原文照搬检查关闭原因：{plagiarism_reason}")
    print(f"字数带宽：{min_words}-{max_words}（{wordcount_source}）")
    order = {"🔴": 0, "🟡": 1, "🟢": 2}
    findings.sort(key=lambda x: (order.get(x["severity"], 9), x["chapter"]))
    print(f"\n确定性问题 {len(findings)} 条：")
    for x in findings:
        loc = "全局" if x["chapter"] == 0 else f"第{x['chapter']}章"
        ev = f" ｜证据「{x['evidence']}」" if x["evidence"] else ""
        print(f"  {x['severity']} [{loc}·{x['dim']}] {x['msg']}{ev}")
    if args.pov and pov_density:
        top = sorted(pov_density.items(), key=lambda kv: -kv[1])[:8]
        top = [(c, n) for c, n in top if n > 0]
        if top:
            print(f"\n视角抽查建议（POV={args.pov} 第三人称限定）：以下章叙述中第一人称『我』密度较高，"
                  f"多为内心独白（合法），但**请 LLM 优先抽查这几章是否有真串视角**：")
            print("  " + "、".join(f"第{c}章({n})" for c, n in top))
    if term_matrix:
        src_parts = []
        if manual_terms:
            src_parts.append("手动")
        if confirmed_terms:
            src_parts.append("已确认实体表(权威)")
        if auto_terms:
            src_parts.append("设定正则")
        source = "+".join(src_parts) or "无"
        print(f"\n术语出现次数（{source}；看跨章漂移，0 与突变值得注意）：")
        print("  章 | " + " | ".join(terms))
        for ch in sorted(term_matrix):
            print(f"  {ch:>2} | " + " | ".join(str(term_matrix[ch][t]) for t in terms))
    if repetition_summary:
        rs = repetition_summary
        cr = rs.get("compression_ratio")
        cr_txt = f"{cr:.0%}" if isinstance(cr, (int, float)) else "n/a"
        print(f"\n跨章重复率/机械文风（advisory·内部启发式·绝不 🔴）：相邻章最高近重复 "
              f"{rs['adjacent_max_jaccard']:.0%}（🟡阈 {REP_ADJ_JACCARD_YELLOW:.0%}）；"
              f"机械开篇组 {rs['mechanical_opener_groups']}；跨章复用整句 {rs['repeated_sentences']}；"
              f"机械句式模板 {rs.get('sentence_opener_templates', 0)}；"
              f"句首词高频 {rs.get('sentence_start_token_groups', 0)}；"
              f"短句式模板 {rs.get('short_sentence_templates', 0)}；"
              f"全书压缩比 {cr_txt}；低压缩章节 {rs.get('low_chapter_compression_count', 0)}（多样性代理）")
    counts = {s: sum(1 for x in findings if x["severity"] == s) for s in ("🔴", "🟡", "🟢")}
    print(f"\n小结：🔴 {counts['🔴']}  🟡 {counts['🟡']}  🟢 {counts['🟢']}")
    payload = {
        "schema_version": 1,
        "kind": "novel_mechanical_findings",
        "project_root": args.root,
        "generated_at": date.today().isoformat(),
        "chapter_range": list(rng) if rng else None,
        "wordcount_band": [min_words, max_words],
        "wordcount_band_source": wordcount_source,
        "findings": findings,
        "counts": counts,
        "plagiarism_check": {
            "enabled": src_shingles is not None,
            "reason": plagiarism_reason,
            "source_path": "原作.txt" if os.path.exists(src_path) else "",
        },
        "pov_density": pov_density,
        "repetition": repetition_summary,
        "term_matrix": term_matrix,
        "terms_source": {
            "manual": manual_terms,
            "confirmed_entities": confirmed_terms,  # 权威源：角色别名.json(confirmed)
            "auto": auto_terms,
        },
    }
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    print("\n<!-- FINDINGS_JSON")
    print(json.dumps(findings, ensure_ascii=False))
    print("FINDINGS_JSON -->")


if __name__ == "__main__":
    main()
