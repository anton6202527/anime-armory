#!/usr/bin/env python3
"""出图→出视频「本集视觉一致性契约」逐字段继承 Diff —— 纯函数核心（单一真值源）。

这套比对逻辑既被 `n2d-video/scripts/inherit_contract.py`（CLI + 落报告）使用，
也被 `n2d-review/scripts/gate.py` 的 video stage gate 直接调用——所以它放在 common/，
让两条线在 common 层会合，而不是 n2d-review 反向深 import n2d-video。

契约五字段单一真值源 = `n2d_contract.VISUAL_CONTRACT_FIELDS`。
"""
from __future__ import annotations

import os
import re
import sys

# 本文件已迁到 skills/n2d/_lib/；走 common 的 n2d_contract shim 取契约（单一入口，避免双载）。
_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import VISUAL_CONTRACT_FIELDS  # noqa: E402

SECTION_TITLE = "本集视觉一致性契约"

# 漂移即 block 的字段；其余字段漂移只 warn。
#   光位锚/轴线视线：焊在首帧像素里、视频改不动、写错必穿帮（越轴/光跳）。
#   角色状态演进：剧情状态锁（觉醒前不发光/受伤前无伤/变身前无变体）——视频侧改写=提前泄露
#     金瞳/伤/变身=连续性事故 + 剧透双杀，与像素层同级不可松（2026-06 由 warn 升 block）。
BLOCK_ON_DRIFT = ("场景光位锚", "场景轴线视线", "角色状态演进")

# 「超集即放行」对状态锁不安全：状态演进是剧情锁，视频侧追加内容（包含原文却多写）可能提前
#   泄露未到点的状态（如 img="Clip01-13 黑瞳常态"，vid 追加 "Clip05 闪现金瞳预兆"——含原文却早泄金瞳）。
#   故此字段不自动 pass_superset，additive 内容一律降级为 warn_drift 强制人工确认；
#   光位锚/轴线是收紧型超集（追加约束只会更稳），仍按 pass_superset 放行。
NO_AUTO_SUPERSET = ("角色状态演进",)

# 字段标签别名 → 契约 canonical 名。demo 出图总览用短标签（光位锚/轴线/状态演进），
# gate.py --stage image_preflight/image 也按短标签检——两种写法都认，比对仍按 VISUAL_CONTRACT_FIELDS 归一。
_FIELD_ALIASES = {
    "色调基线": ("色调基线",),
    "场景光位锚": ("场景光位锚", "光位锚"),
    "场景轴线视线": ("场景轴线视线", "轴线视线", "轴线"),
    "角色状态演进": ("角色状态演进表", "角色状态演进", "状态演进表", "状态演进"),
    "景别阶梯": ("景别阶梯",),
}
assert set(_FIELD_ALIASES) == set(VISUAL_CONTRACT_FIELDS), "字段别名表必须覆盖契约五字段"
# block/no-superset 名单手维护，引用字段名字符串——字段重命名时这里若 typo 会让 block 静默降级为
# warn（且无人察觉）。模块加载即断言两者都是契约字段子集，与上面的别名断言同为「字段漂移自爆」守卫。
assert set(BLOCK_ON_DRIFT) <= set(VISUAL_CONTRACT_FIELDS), \
    "BLOCK_ON_DRIFT 必须是 VISUAL_CONTRACT_FIELDS 子集（字段重命名请同步，否则 block 漂移检测静默失效）"
assert set(NO_AUTO_SUPERSET) <= set(VISUAL_CONTRACT_FIELDS), \
    "NO_AUTO_SUPERSET 必须是 VISUAL_CONTRACT_FIELDS 子集（字段重命名请同步）"

_BULLET_RE = re.compile(r"^\s*[-*•]\s*(.+?)\s*$")
_HEAD_RE = re.compile(r"^(#{1,6})\s")


def _norm(text: str) -> str:
    """归一化：只留 CJK/字母/数字，丢空白与全部标点（·、→/-> 等差异不算漂移），统一小写。"""
    return re.sub(r"[^0-9A-Za-z㐀-鿿぀-ヿ가-힯]+", "", text or "").lower()


# 别名归一化查表（标签去掉 **加粗**、·、空格后比对）
_ALIAS_LOOKUP = {_norm(a): canon for canon, aliases in _FIELD_ALIASES.items() for a in aliases}


def extract_section(text: str, title: str = SECTION_TITLE):
    """取 markdown 中标题含 title 的整节正文（到下一个同级/更高级标题为止）；无该节返回 None。"""
    lines = text.splitlines()
    start = level = None
    for i, ln in enumerate(lines):
        m = _HEAD_RE.match(ln)
        if m and title in ln:
            start, level = i + 1, len(m.group(1))
            break
    if start is None:
        return None
    body = []
    for ln in lines[start:]:
        m = _HEAD_RE.match(ln)
        if m and len(m.group(1)) <= level:
            break
        body.append(ln)
    return "\n".join(body)


def parse_contract_fields(section_text: str) -> dict:
    """契约节 → {canonical字段: 原文值}。bullet 格式 `- 标签：值`；非 bullet 续行并入当前字段。"""
    fields: dict = {}
    current = None
    for ln in (section_text or "").splitlines():
        m = _BULLET_RE.match(ln)
        if m:
            body = m.group(1)
            parts = re.split(r"[：:]", body, maxsplit=1)
            label = parts[0]
            value = parts[1] if len(parts) > 1 else ""
            canon = _ALIAS_LOOKUP.get(_norm(label))
            if canon:
                current = canon
                fields[canon] = value.strip()
            else:
                current = None  # 未知 bullet：不并入上一字段
        elif current and ln.strip():
            fields[current] = (fields[current] + " " + ln.strip()).strip()
    return fields


def compare_field(field: str, img_val, vid_val) -> dict:
    """单字段比对 → {field, status, severity, image_text, video_text, note}。

    规则（按 demo 单行要点式契约校准）：
      - 出图侧缺/空 → upstream_missing（warn·提示但不拦，上游问题）；
      - 视频侧缺/空 → block_missing_in_video；
      - 归一化后相等 → pass；视频侧包含出图侧（有意细化/收紧的超集）→ pass_superset；
      - 否则 → 漂移：光位/轴线 block_drift，其余 warn_drift。
    """
    item = {"field": field, "image_text": img_val or "", "video_text": vid_val or ""}
    img_n, vid_n = _norm(img_val or ""), _norm(vid_val or "")
    if not img_n:
        item.update(status="upstream_missing", severity="warn",
                    note="出图侧契约缺此字段（上游问题，不拦本步）：回 n2d-image 补 00_总览 视觉契约，image_preflight/image gate 会阻断")
    elif not vid_n:
        item.update(status="block_missing_in_video", severity="block",
                    note="视频侧契约缺此字段：誊抄丢失，必须把出图侧原文补进 出视频/prompt/00_总览.md 再出视频")
    elif img_n == vid_n:
        item.update(status="pass", severity="pass", note="逐字一致")
    elif img_n in vid_n and field not in NO_AUTO_SUPERSET:
        item.update(status="pass_superset", severity="pass", note="视频侧为出图侧的细化/收紧超集（包含原文），放行")
    elif img_n in vid_n:  # 状态锁字段：含原文但有追加 → 不自动放行（追加内容可能提前泄露未到点状态）
        item.update(status="warn_drift", severity="warn",
                    note="状态锁追加内容：视频侧虽含出图侧原文但另有追加，可能提前泄露未到点的觉醒/伤/变身——"
                         "人工确认追加内容不早泄状态，确属有意细化才放行，否则以出图侧为准")
    else:
        if field in BLOCK_ON_DRIFT:
            why = ("剧情状态锁：视频侧改写=提前泄露 觉醒/伤/变身 等状态（连续性事故+剧透）"
                   if field == "角色状态演进"
                   else "该字段焊在首帧像素里，视频侧改写=与首帧打架（越轴/光跳穿帮）")
            item.update(status="block_drift", severity="block",
                        note=f"漂移：{why}；以出图侧为准改回")
        else:
            item.update(status="warn_drift", severity="warn",
                        note="漂移：与出图侧不一致（非光位/轴线，先警告）；确认是否有意改写，无理由则以出图侧为准")
    return item


CINEMATIC_SECTION_TITLE = "本集真实电影感契约"  # 电影光学契约（opt-in·含镜头焦段）


def _extract_focal(text: str):
    """从「本集真实电影感契约」节取 `镜头焦段` 原文值；无该节/字段 → None。"""
    sec = extract_section(text, CINEMATIC_SECTION_TITLE)
    if sec is None:
        return None
    for ln in sec.splitlines():
        m = _BULLET_RE.match(ln)
        if not m:
            continue
        parts = re.split(r"[：:]", m.group(1), maxsplit=1)
        if len(parts) > 1 and _norm(parts[0]) == _norm("镜头焦段"):
            return parts[1].strip()
    return None


def diff_cinematic_focal(img_text: str, vid_text: str) -> list:
    """镜头焦段 img→video 继承（电影光学契约·opt-in·warn-only，不入 BLOCK_ON_DRIFT）。

    `景别阶梯` 管景别(CU/LS)，不管**焦段压缩感**——同场景长焦↔广角畸变/压缩不同=换镜头感。
    两侧都声明真实电影感契约的镜头焦段且不一致 → warn；任一侧无该契约/字段 → 跳过（焦段不强求）。
    纯函数·可测。"""
    img_f, vid_f = _extract_focal(img_text), _extract_focal(vid_text)
    if not img_f or not vid_f:
        return []
    item = {"field": "镜头焦段", "image_text": img_f, "video_text": vid_f}
    in_, vn = _norm(img_f), _norm(vid_f)
    if in_ == vn or in_ in vn or vn in in_:
        item.update(status="pass", severity="pass", note="焦段一致/超集")
    else:
        item.update(status="warn_drift", severity="warn",
                    note="镜头焦段 img→video 漂移：长焦↔广角压缩感/畸变不同=换镜头感；"
                         "确认是否有意改写，否则以出图侧焦段为准")
    return [item]


def diff_contracts(img_text: str, vid_text: str) -> list:
    """两份 00_总览 全文 → 逐字段比对结果列表（按 VISUAL_CONTRACT_FIELDS 顺序）。"""
    img_sec = extract_section(img_text)
    vid_sec = extract_section(vid_text)
    img_fields = parse_contract_fields(img_sec) if img_sec is not None else {}
    vid_fields = parse_contract_fields(vid_sec) if vid_sec is not None else {}
    results = []
    for field in VISUAL_CONTRACT_FIELDS:
        item = compare_field(field, img_fields.get(field), vid_fields.get(field))
        if vid_sec is None and item["severity"] == "block":
            item["note"] = ("视频侧 00_总览 缺「" + SECTION_TITLE + "」整节：须从出图总览原样誊抄五字段"
                            "（允许细化为超集；「本集导演一致性契约」是运动层、不可替代像素层契约）")
        results.append(item)
    return results


# storyboard(阶段2分镜) → 出图 00_总览 的**上游种子**契约继承。此前 script→image 接缝只查
# 出图/storyboard 各自「字段在不在」（check_storyboard_visual_contract / check_image_prompt_overview），
# **没有跨接缝的内容 diff**——出图 00_总览 一旦把 storyboard 的光位/轴线种子誊抄改写，就成了下游
# 全部忠实继承的"错误权威源"，却无人拦。本函数补这道机检，与 diff_contracts(出图→出视频) 对称。
#
# 只对**焊进首帧像素**的 场景光位锚 / 场景轴线视线 判 block（改写=与像素打架/越轴/光跳）；
# 角色状态演进在出图侧常按"以 storyboard 分段状态为上游契约"的**指针式**写法承接（不逐字誊抄，
# 避免提前泄露后镜状态），故只 warn；色调基线/景别阶梯 warn。storyboard 字段值可为 dict/list，
# 统一 JSON 串化后归一比对（出图侧本就把种子串化落文，正常继承=超集 pass）。
STORYBOARD_IMAGE_BLOCK_FIELDS = ("场景光位锚", "场景轴线视线")


def _stringify_seed(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def diff_storyboard_image_contract(storyboard_vc: dict, image_text: str) -> list:
    """storyboard.json.visual_contract → 出图 00_总览 逐字段继承 diff。

    返回列表元素同 compare_field，另加 `seam_block`（bool，仅光位/轴线漂移为真，供 gate 判 block）。
    纯函数·可测。storyboard 侧种子缺失=上游问题（由 check_storyboard_visual_contract 负责），此处 warn 不重复 block。"""
    img_sec = extract_section(image_text)
    img_fields = parse_contract_fields(img_sec) if img_sec is not None else {}
    vc = storyboard_vc if isinstance(storyboard_vc, dict) else {}
    results = []
    for field in VISUAL_CONTRACT_FIELDS:
        item = compare_field(field, _stringify_seed(vc.get(field)), img_fields.get(field))
        # 接缝语义：storyboard 是上游种子，出图应继承为超集；出图侧缺整节时 img=空由上游检查负责。
        item["seam"] = "storyboard->image"
        item["seam_block"] = bool(item["status"] == "block_drift" and field in STORYBOARD_IMAGE_BLOCK_FIELDS)
        results.append(item)
    return results
