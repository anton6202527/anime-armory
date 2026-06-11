#!/usr/bin/env python3
"""出图→出视频「本集视觉一致性契约」继承 Diff（机器检出人工誊抄漂移）。

背景：契约五字段（色调基线/场景光位锚/场景轴线视线/角色状态演进/景别阶梯）由
`出图/第N集/prompt/00_总览.md` 人工誊抄到 `出视频/第N集/prompt/00_总览.md`。
誊抄时改错轴线/光位没有任何机器检出——而这两项焊在首帧像素里，视频侧写错
prompt 就会跟首帧打架（闪烁/越轴穿帮）。本脚本逐字段归一化比对两侧契约：

  - 视频侧允许「有意收紧/细化」：归一化后**包含**出图侧原文即 pass（超集容忍），
    只拦「改写/丢失」（demo 出图侧契约为单行要点式 bullet，按此校准）；
  - 「场景光位锚」「场景轴线视线」漂移 → block（exit 1）；其余字段漂移 → warn（exit 0）；
  - 视频侧缺字段/缺契约段 → block；
  - 出图侧本来就缺 → 提示但不拦（上游问题，应回 /n2d-image 补，image gate 会拦）。

用法：python3 inherit_contract.py <作品根> <第N集>
产出：生产数据/contract_inheritance_第N集.json + .md（逐字段 pass/warn/block 与两侧原文摘录）。

纯 stdlib；契约字段单一真值源 = skills/common/n2d_contract.VISUAL_CONTRACT_FIELDS。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import CONTRACT_INHERITANCE_KIND, VISUAL_CONTRACT_FIELDS, production_dir  # noqa: E402

KIND = CONTRACT_INHERITANCE_KIND
SECTION_TITLE = "本集视觉一致性契约"

# 漂移即 block 的字段（焊在像素里、视频改不动、写错必穿帮）；其余字段漂移只 warn。
BLOCK_ON_DRIFT = ("场景光位锚", "场景轴线视线")

# 字段标签别名 → 契约 canonical 名。demo 出图总览实际用短标签
# （光位锚/轴线/状态演进，见 制漫剧/本宫才是这皇宫最大的妖/出图/第1集/prompt/00_总览.md），
# gate.py --stage image 也按短标签检——两种写法都认，比对仍按 VISUAL_CONTRACT_FIELDS 归一。
_FIELD_ALIASES = {
    "色调基线": ("色调基线",),
    "场景光位锚": ("场景光位锚", "光位锚"),
    "场景轴线视线": ("场景轴线视线", "轴线视线", "轴线"),
    "角色状态演进": ("角色状态演进表", "角色状态演进", "状态演进表", "状态演进"),
    "景别阶梯": ("景别阶梯",),
}
assert set(_FIELD_ALIASES) == set(VISUAL_CONTRACT_FIELDS), "字段别名表必须覆盖契约五字段"

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
                    note="出图侧契约缺此字段（上游问题，不拦本步）：回 /n2d-image 补 00_总览 视觉契约，image gate 会阻断")
    elif not vid_n:
        item.update(status="block_missing_in_video", severity="block",
                    note="视频侧契约缺此字段：誊抄丢失，必须把出图侧原文补进 出视频/prompt/00_总览.md 再出视频")
    elif img_n == vid_n:
        item.update(status="pass", severity="pass", note="逐字一致")
    elif img_n in vid_n:
        item.update(status="pass_superset", severity="pass", note="视频侧为出图侧的细化/收紧超集（包含原文），放行")
    else:
        if field in BLOCK_ON_DRIFT:
            item.update(status="block_drift", severity="block",
                        note="漂移：该字段焊在首帧像素里，视频侧改写=与首帧打架（越轴/光跳穿帮）；以出图侧为准改回")
        else:
            item.update(status="warn_drift", severity="warn",
                        note="漂移：与出图侧不一致（非光位/轴线，先警告）；确认是否有意改写，无理由则以出图侧为准")
    return item


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


def _render_md(ep: str, results: list, img_rel: str, vid_rel: str, verdict: str) -> str:
    sev_icon = {"pass": "✅", "warn": "⚠️", "block": "⛔"}
    lines = [
        f"# 契约继承 Diff · {ep}（出图 → 出视频）",
        "",
        f"- 出图侧：`{img_rel}`",
        f"- 视频侧：`{vid_rel}`",
        f"- 判定：**{verdict}**（block=修复后才可出视频；warn=确认是否有意改写；规则：视频侧可细化为超集，不许改写/丢失）",
        "",
        "| 字段 | 判定 | 说明 |",
        "|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['field']} | {sev_icon[r['severity']]} {r['status']} | {r['note']} |")
    lines.append("")
    for r in results:
        if r["severity"] == "pass" and r["status"] == "pass":
            continue
        lines += [f"## {r['field']} — {r['status']}",
                  f"- 出图侧原文：{r['image_text'] or '（缺）'}",
                  f"- 视频侧原文：{r['video_text'] or '（缺）'}",
                  f"- 说明：{r['note']}", ""]
    return "\n".join(lines)


def run(root: str, ep: str) -> int:
    img_rel = os.path.join("出图", ep, "prompt", "00_总览.md")
    vid_rel = os.path.join("出视频", ep, "prompt", "00_总览.md")
    img_path = os.path.join(root, img_rel)
    vid_path = os.path.join(root, vid_rel)
    if not os.path.isfile(img_path):
        print(f"⛔ 缺 {img_path} —— 出图总览未生成，先 /n2d-image（上游前置，无从比对契约）。", file=sys.stderr)
        return 2
    if not os.path.isfile(vid_path):
        print(f"⛔ 缺 {vid_path} —— 视频 prompt 总览未生成，先跑 /n2d-video 阶段A 再校验契约继承。", file=sys.stderr)
        return 2

    results = diff_contracts(open(img_path, encoding="utf-8").read(),
                             open(vid_path, encoding="utf-8").read())
    summary = {sev: sum(1 for r in results if r["severity"] == sev) for sev in ("pass", "warn", "block")}
    verdict = "block" if summary["block"] else ("warn" if summary["warn"] else "pass")

    out_dir = production_dir(root)
    os.makedirs(out_dir, exist_ok=True)
    report = {
        "kind": KIND,
        "episode": ep,
        "image_overview": img_rel,
        "video_overview": vid_rel,
        "fields": results,
        "summary": summary,
        "verdict": verdict,
        "rule": "视频侧契约可有意收紧/细化（归一化后包含出图侧原文即 pass）；只拦改写/丢失；光位锚+轴线视线漂移=block",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    json_path = os.path.join(out_dir, f"contract_inheritance_{ep}.json")
    md_path = os.path.join(out_dir, f"contract_inheritance_{ep}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    open(md_path, "w", encoding="utf-8").write(_render_md(ep, results, img_rel, vid_rel, verdict) + "\n")

    icon = {"pass": "✅", "warn": "⚠️", "block": "⛔"}[verdict]
    print(f"{icon} 契约继承 {ep}: {verdict}（pass={summary['pass']} warn={summary['warn']} block={summary['block']}）→ {json_path}")
    for r in results:
        if r["severity"] != "pass":
            print(f"  - [{r['severity']}] {r['field']}: {r['status']} — {r['note']}")
    if verdict == "block":
        print("⛔ 有 block：先按出图侧原文修 出视频/prompt/00_总览.md 的视觉契约，再出视频。", file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print("usage: python3 inherit_contract.py <作品根> <第N集>", file=sys.stderr)
        return 2
    return run(argv[0], argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
