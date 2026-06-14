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
  - 出图侧本来就缺 → 提示但不拦（上游问题，应回 n2d-image 补，image_preflight/image gate 会拦）。

用法：python3 inherit_contract.py <作品根> <第N集>
产出：生产数据/contract_inheritance_第N集.json + .md（逐字段 pass/warn/block 与两侧原文摘录）。

纯 stdlib；契约字段单一真值源 = skills/n2d/_lib/n2d_contract.VISUAL_CONTRACT_FIELDS。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import CONTRACT_INHERITANCE_KIND, VISUAL_CONTRACT_FIELDS, production_dir  # noqa: E402
# 比对核心已上移到 n2d/_lib/n2d_contract_diff.py（单一真值源），让 gate.py 也能在 common 层调用，
# 而非 n2d-review 反向 import n2d-video。此处 re-export 以保持本模块/测试的既有 API。
from n2d_contract_diff import (  # noqa: E402,F401
    BLOCK_ON_DRIFT,
    SECTION_TITLE,
    compare_field,
    diff_contracts,
    extract_section,
    parse_contract_fields,
)

KIND = CONTRACT_INHERITANCE_KIND

# ── 身份交接契约（②：把「出图首帧脸 → 出视频脸」也纳入继承 Diff） ──────────────────
# 视觉契约五字段管色调/光位/轴线/状态/景别，**不含脸**。脸的跨阶段交接此前没有任何契约级
# 机检：n2d-model-router 已为每个命名角色镜算出 identity_requirement（reference_group /
# character_id_or_reference_group / face_lock_or_reference_group），但没人核验逐镜视频 prompt
# 是否真把身份锁住。本检查读 video_model_routes.json + 01_clips.md，对每个命名角色镜
# （identity_requirement != none）要求其逐镜 prompt 写了身份锁定声明 + 具体锚点，否则 block
# （首帧脸→视频脸无契约锚，出视频必脸漂）。
ROUTE_IDENTITY_NONE = "none"
# 逐镜 video prompt 里「声明了身份锁定」的字段名（中/英两套写法都认）。
IDENTITY_DECL_MARKERS = ("身份锁定", "身份注册层", "identity lock", "identity adapter", "identity_requirement")
# 声明必须落到可执行锚点，不能只是空喊「锁身份」。
IDENTITY_ANCHOR_RE = re.compile(
    r"CHAR_[A-Za-z0-9_]+|定妆_|reference_group|character_id|face_lock|reference[ _]controls|脸部特写|主体库|cameo",
    re.IGNORECASE,
)


def _clip_num(text: str):
    """从 'Clip_03' / '## Clip 03（…' / 'EP01_CLIP03' 提镜号 → int；提不出 → None。纯函数·可测。"""
    m = re.search(r"(\d+)", str(text or ""))
    return int(m.group(1)) if m else None


def parse_named_character_routes(routes_json_text: str):
    """video_model_routes.json 文本 → 命名角色镜路由 [{clip_id, clip_num, identity_requirement}]。

    只保留 identity_requirement != none 的镜（= 有命名角色、需要锁脸）；解析失败返回 None。纯函数·可测。
    """
    try:
        data = json.loads(routes_json_text)
    except Exception:
        return None
    out = []
    for r in data.get("routes") or []:
        if not isinstance(r, dict):
            continue
        req = str(r.get("identity_requirement") or ROUTE_IDENTITY_NONE).strip()
        if req == ROUTE_IDENTITY_NONE or not req:
            continue
        cid = str(r.get("clip_id") or "").strip()
        out.append({"clip_id": cid, "clip_num": _clip_num(cid), "identity_requirement": req})
    return out


def split_video_clip_blocks(clips_md: str):
    """01_clips.md → {clip_num: block_text}，按 '## Clip NN' 标题切。纯函数·可测。"""
    blocks = {}
    cur_num = None
    cur = []
    for line in str(clips_md or "").splitlines():
        if line.startswith("## ") and ("Clip" in line or "clip" in line):
            if cur_num is not None:
                blocks[cur_num] = "\n".join(cur)
            cur_num = _clip_num(line)
            cur = [line]
        elif cur_num is not None:
            cur.append(line)
    if cur_num is not None:
        blocks[cur_num] = "\n".join(cur)
    return blocks


def clip_block_locks_identity(block_text: str) -> bool:
    """命名角色镜的逐镜 video prompt 是否真锁了身份：既要有身份锁定声明，又要落到具体锚点
    （CHAR_xx / 定妆_ / reference_group / character_id / face_lock / 脸部特写 / 主体库 / cameo）。纯函数·可测。"""
    text = str(block_text or "")
    has_decl = any(m in text for m in IDENTITY_DECL_MARKERS)
    has_anchor = bool(IDENTITY_ANCHOR_RE.search(text))
    return has_decl and has_anchor


def check_identity_handoff(root: str, ep: str) -> dict:
    """对每个命名角色镜核验逐镜 video prompt 写了身份锁定 + 具体锚点（②）。

    缺 routes / 缺 01_clips.md → available=False、无 finding（上游未到位，不在本检查拦，
    由 router/video 阶段各自的 gate 负责）；只在两文件都在时做硬核验。
    """
    routes_rel = os.path.join("出视频", ep, "prompt", "video_model_routes.json")
    clips_rel = os.path.join("出视频", ep, "prompt", "01_clips.md")
    routes_path = os.path.join(root, routes_rel)
    clips_path = os.path.join(root, clips_rel)
    res = {"available": False, "findings": [], "checked": 0, "notes": [],
           "routes_file": routes_rel, "clips_file": clips_rel}
    if not os.path.isfile(routes_path):
        res["notes"].append("无 video_model_routes.json——跳过身份交接校验（先跑 n2d-model-router）。")
        return res
    named = parse_named_character_routes(open(routes_path, encoding="utf-8").read())
    if named is None:
        res["notes"].append("video_model_routes.json 解析失败——跳过身份交接校验。")
        return res
    if not os.path.isfile(clips_path):
        res["notes"].append("无 01_clips.md——跳过身份交接校验（先跑 n2d-video 阶段A 写逐镜 prompt）。")
        return res
    blocks = split_video_clip_blocks(open(clips_path, encoding="utf-8").read())
    res["available"] = True
    for nr in named:
        res["checked"] += 1
        blk = blocks.get(nr["clip_num"])
        if blk is None:
            res["findings"].append({
                "clip_id": nr["clip_id"], "severity": "block", "code": "identity_clip_prompt_missing",
                "note": (f"{nr['clip_id']}：identity_requirement={nr['identity_requirement']} 命名角色镜，"
                         "但 01_clips.md 无对应逐镜 prompt——脸交接无锚，出视频必脸漂。"),
            })
            continue
        if not clip_block_locks_identity(blk):
            res["findings"].append({
                "clip_id": nr["clip_id"], "severity": "block", "code": "identity_lock_missing",
                "note": (f"{nr['clip_id']}：identity_requirement={nr['identity_requirement']}，但逐镜 prompt 未锁身份"
                         "（缺『身份锁定/身份注册层』声明或缺具体锚 CHAR_xx/定妆_/reference_group/character_id/face_lock/脸部特写）"
                         "——出图首帧脸→出视频脸无契约锚，易脸漂。"),
            })
    return res


def _render_identity_md(identity: dict) -> list:
    """身份交接段（追加到契约继承 MD 末尾）。"""
    if not identity.get("available"):
        note = "；".join(identity.get("notes", [])) or "未执行"
        return ["", "## 身份交接契约（出图首帧脸 → 出视频脸）", f"- ⏭ 跳过：{note}"]
    blocks = [f for f in identity.get("findings", []) if f.get("severity") == "block"]
    flag = "⛔" if blocks else "✅"
    lines = ["", "## 身份交接契约（出图首帧脸 → 出视频脸）",
             f"- {flag} 命名角色镜 {identity.get('checked', 0)} 个已核验 · 身份未锁 block {len(blocks)}"]
    for f in identity.get("findings", []):
        lines.append(f"  - ⛔ [{f.get('code')}] {f.get('note')}")
    return lines


# ── 物料约束继承（C：场景/道具/服装/特效的逐镜资产交接 Diff） ────────────────────────
# 视觉契约五字段在 episode 级管场景光位锚/轴线（已 block），但**逐镜**绑定的具体资产
# （LOC_xx 场景 / PROP_xx 道具 / OUTFIT_xx 服装 / VFX_xx 特效）有没有从出图诚实交接到出视频，
# 此前无机检。出图逐镜 `资产引用注册层` 绑了 PROP_01，出视频该镜若把它丢了 → 该道具在视频侧无
# reference_group/constraints/drift_forbidden 锚 → 道具/特效跨镜漂移。本检查逐镜 Diff 资产 id 集合，
# 出图绑定的资产在出视频对应镜丢失 = block（资产无锚漂移）。
ASSET_HANDOFF_ID_RE = re.compile(r"(?:LOC|PROP|OUTFIT|VFX)_[A-Za-z0-9]+")


def extract_asset_ids(text: str) -> set:
    """逐镜块文本 → 资产 id 集合（LOC/PROP/OUTFIT/VFX_xx）。纯函数·可测。"""
    return set(ASSET_HANDOFF_ID_RE.findall(str(text or "")))


def asset_id_to_name(root: str) -> dict:
    """asset_registry.json → {asset_id: name}，用于区分『id 丢但名字还在』(warn) 与『整个资产没了』(block)。"""
    try:
        data = json.loads(open(os.path.join(root, "出图", "共享", "asset_registry.json"), encoding="utf-8").read())
    except Exception:
        return {}
    out = {}
    for a in (data.get("assets") or []):
        aid = str(a.get("id") or "").strip()
        name = str(a.get("name") or "").strip()
        if aid and name:
            out[aid] = name
    return out


def check_asset_handoff(root: str, ep: str) -> dict:
    """逐镜资产约束继承 Diff（C）：出图 01_分镜出图.md 绑定的资产，出视频 01_clips.md 对应镜不得丢失。

    缺任一逐镜文件 → available=False、无 finding（上游未到位，各自 gate 负责）。
    """
    img_rel = os.path.join("出图", ep, "prompt", "01_分镜出图.md")
    vid_rel = os.path.join("出视频", ep, "prompt", "01_clips.md")
    img_path = os.path.join(root, img_rel)
    vid_path = os.path.join(root, vid_rel)
    res = {"available": False, "findings": [], "checked": 0, "notes": [],
           "image_clips_file": img_rel, "video_clips_file": vid_rel}
    if not os.path.isfile(img_path):
        res["notes"].append("无 出图/01_分镜出图.md——跳过资产约束继承校验。")
        return res
    if not os.path.isfile(vid_path):
        res["notes"].append("无 出视频/01_clips.md——跳过资产约束继承校验（先跑 n2d-video 阶段A）。")
        return res
    img_blocks = split_video_clip_blocks(open(img_path, encoding="utf-8").read())
    vid_blocks = split_video_clip_blocks(open(vid_path, encoding="utf-8").read())
    id2name = asset_id_to_name(root)
    res["available"] = True
    for num in sorted(img_blocks):
        img_assets = extract_asset_ids(img_blocks[num])
        if not img_assets:
            continue
        res["checked"] += 1
        clip_id = f"Clip_{num:02d}"
        vblk = vid_blocks.get(num)
        if vblk is None:
            # 整个逐镜 prompt 缺失（结构性、高精度）= block，同 identity_clip_prompt_missing。
            res["findings"].append({
                "clip_id": clip_id, "severity": "block", "code": "asset_clip_prompt_missing",
                "note": (f"{clip_id}：出图绑定资产 {sorted(img_assets)}，但 01_clips.md 无对应逐镜 prompt"
                         "——资产在视频侧无锚，易场景/道具/特效漂移。"),
            })
            continue
        dropped = sorted(img_assets - extract_asset_ids(vblk))
        if dropped:
            # 资产 id 丢失（可能是有意的松引用，如记忆遮罩/转场只提名字）= warn，交人确认；
            # 不 block（不像人脸交接那样必然崩），但每个丢失都要醒目入账，避免执行端默默取不到 constraints。
            names = "、".join(f"{aid}({id2name.get(aid, '?')})" for aid in dropped)
            res["findings"].append({
                "clip_id": clip_id, "severity": "warn", "code": "asset_handoff_dropped",
                "note": (f"{clip_id}：出图绑定的资产 {names} 在出视频逐镜 prompt 丢了 id"
                         "——执行端取不到其 reference_group/constraints/drift_forbidden，若非有意松引用，"
                         "补回 LOC/PROP/VFX_xx 让结构/颜色/光位锚自动继承（防场景/道具/特效跨镜漂移）。"),
            })
    return res


def _render_asset_md(asset: dict) -> list:
    if not asset.get("available"):
        note = "；".join(asset.get("notes", [])) or "未执行"
        return ["", "## 物料约束继承（场景/道具/服装/特效逐镜交接）", f"- ⏭ 跳过：{note}"]
    blocks = [f for f in asset.get("findings", []) if f.get("severity") == "block"]
    warns = [f for f in asset.get("findings", []) if f.get("severity") == "warn"]
    flag = "⛔" if blocks else ("⚠️" if warns else "✅")
    lines = ["", "## 物料约束继承（场景/道具/服装/特效逐镜交接）",
             f"- {flag} 带资产的镜 {asset.get('checked', 0)} 个已核验 · 资产丢失 block {len(blocks)} · id 缺 warn {len(warns)}"]
    for f in asset.get("findings", []):
        ic = "⛔" if f.get("severity") == "block" else "⚠️"
        lines.append(f"  - {ic} [{f.get('code')}] {f.get('note')}")
    return lines


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
        print(f"⛔ 缺 {img_path} —— 出图总览未生成，先 n2d-image（上游前置，无从比对契约）。", file=sys.stderr)
        return 2
    if not os.path.isfile(vid_path):
        print(f"⛔ 缺 {vid_path} —— 视频 prompt 总览未生成，先跑 n2d-video 阶段A 再校验契约继承。", file=sys.stderr)
        return 2

    results = diff_contracts(open(img_path, encoding="utf-8").read(),
                             open(vid_path, encoding="utf-8").read())
    summary = {sev: sum(1 for r in results if r["severity"] == sev) for sev in ("pass", "warn", "block")}

    # ② 身份交接：命名角色镜逐镜 video prompt 是否真锁了脸（脸的契约级 Diff）。
    identity = check_identity_handoff(root, ep)
    identity_blocks = [f for f in identity.get("findings", []) if f.get("severity") == "block"]

    # C 物料约束继承：出图逐镜绑定的场景/道具/服装/特效资产，出视频不得丢失。
    asset = check_asset_handoff(root, ep)
    asset_blocks = [f for f in asset.get("findings", []) if f.get("severity") == "block"]
    asset_warns = [f for f in asset.get("findings", []) if f.get("severity") == "warn"]

    verdict = ("block" if (summary["block"] or identity_blocks or asset_blocks)
               else ("warn" if (summary["warn"] or asset_warns) else "pass"))

    out_dir = production_dir(root)
    os.makedirs(out_dir, exist_ok=True)
    report = {
        "kind": KIND,
        "episode": ep,
        "image_overview": img_rel,
        "video_overview": vid_rel,
        "fields": results,
        "summary": summary,
        "identity_handoff": identity,
        "asset_handoff": asset,
        "verdict": verdict,
        "rule": "视频侧契约可有意收紧/细化（归一化后包含出图侧原文即 pass）；只拦改写/丢失；光位锚+轴线视线漂移=block；命名角色镜逐镜 prompt 未锁身份=block；出图绑定资产在出视频丢失=block",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    json_path = os.path.join(out_dir, f"contract_inheritance_{ep}.json")
    md_path = os.path.join(out_dir, f"contract_inheritance_{ep}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    md = (_render_md(ep, results, img_rel, vid_rel, verdict)
          + "\n".join(_render_identity_md(identity))
          + "\n".join(_render_asset_md(asset)))
    open(md_path, "w", encoding="utf-8").write(md + "\n")

    icon = {"pass": "✅", "warn": "⚠️", "block": "⛔"}[verdict]
    print(f"{icon} 契约继承 {ep}: {verdict}（pass={summary['pass']} warn={summary['warn']} block={summary['block']}"
          f" · 身份未锁 {len(identity_blocks)} · 资产丢失 {len(asset_blocks)} · 资产id缺 {len(asset_warns)}）→ {json_path}")
    for r in results:
        if r["severity"] != "pass":
            print(f"  - [{r['severity']}] {r['field']}: {r['status']} — {r['note']}")
    for f in identity_blocks:
        print(f"  - [block] 身份交接 {f.get('clip_id')}: {f.get('code')} — {f.get('note')}")
    for f in asset_blocks:
        print(f"  - [block] 物料交接 {f.get('clip_id')}: {f.get('code')} — {f.get('note')}")
    if verdict == "block":
        if summary["block"]:
            print("⛔ 有契约 block：先按出图侧原文修 出视频/prompt/00_总览.md 的视觉契约，再出视频。", file=sys.stderr)
        if identity_blocks:
            print("⛔ 有身份交接 block：先在 出视频/prompt/01_clips.md 给这些命名角色镜补『身份锁定+具体锚点』，再出视频。", file=sys.stderr)
        if asset_blocks:
            print("⛔ 有物料交接 block：出图绑定的场景/道具/特效资产在出视频逐镜 prompt 丢了，补回 LOC/PROP/VFX_xx 再出视频。", file=sys.stderr)
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
