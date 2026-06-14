#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""出图 → 出视频 视觉契约继承机检（拍广告版）。

广告里"视频改不动、要烤进首帧像素"的导演决策（**品牌色**/光位锚/轴线·视线/景别/**产品形态**）
必须从出图阶段继承到出视频，不能漂。本脚本逐字段 Diff 上游契约与每 Clip 的视频 prompt：

  - 上游契约源（单一真值源，按优先级）：
      ① `出图/分镜/prompt/00_总览.md` 的「视觉一致性契约」节 —— 品牌色 HEX / 光位锚 / 轴线
        在**出图阶段细化后**烤进首帧像素的地方（与 n2d 的 image→video 同口径）；
      ② 缺①时回退 `脚本/storyboard.json`.visual_contract（未细化的脚本种子）。
  - 品牌色/光位锚/轴线漂移 = block（广告产品色一漂就废）；画风/景别/构图 = warn。
  - **产品形态交接（PROD_*）**：出图逐镜绑定 PROD_xx 的产品镜，视频 prompt 必须重新
    携带产品的 身份锁定句/资产引用（PROD_xx 或 同一包装/同一 logo/同一品牌色），
    否则 block —— 镜像 n2d 的 check_identity_handoff（命名角色镜逐镜锁脸）。

比对不做脆弱的裸子串匹配：
  - 品牌色按 HEX 归一（去 #/空格/大小写，认 rgb()/常见别名）比对；
  - 光位/轴线按归一化超集比对（容忍 paraphrase / 标点差异），同 n2d 的 compare_field。

自包含纯标准库 + 单测，不 import n2d-* / mv-* / ad-craft。

用法：
    python3 inherit_contract.py <作品根> --json 出视频/分镜/contract_inheritance.json
"""
import argparse
import json
import os
import re
import sys

# 这些字段是像素级硬继承（视频改不动）：缺失或与上游冲突 = block。
HARD_FIELDS = ["品牌色", "光位锚", "轴线"]
SOFT_FIELDS = ["画风", "景别", "构图"]

# 出图侧契约节标题（00_总览.md 里的「视觉一致性契约」）。
CONTRACT_SECTION_TITLE = "视觉一致性契约"

# 字段标签别名 → canonical 名。出图 00_总览 可能用短/长标签或英文写法，全部归一。
_FIELD_ALIASES = {
    "品牌色": ("品牌色", "品牌主色", "主色", "brand color", "brand colour"),
    "光位锚": ("光位锚", "光位", "光位/色温", "lighting", "light anchor"),
    "轴线": ("轴线", "轴线视线", "视线", "轴线·视线", "axis", "eyeline"),
    "画风": ("画风", "基础视觉风格", "视觉风格", "风格", "style"),
    "景别": ("景别", "景别阶梯", "shot size"),
    "构图": ("构图", "构图策略", "镜头与构图", "composition"),
}

# 产品资产 id（逐镜绑定，出图/视频两侧文本里出现）。
PROD_ID_RE = re.compile(r"PROD_[A-Za-z0-9]+")
# 产品身份锁定句标记（视频侧可以写 PROD_xx，也可以写下面的锁定语句任一个）。
PRODUCT_LOCK_MARKERS = (
    "身份锁定", "资产引用", "同一包装", "同一款包装", "同一 logo", "同一logo",
    "同一品牌色", "产品参考", "产品定妆", "hero product",
)

_HEAD_RE = re.compile(r"^(#{1,6})\s")
_BULLET_RE = re.compile(r"^\s*[-*•]\s*(.+?)\s*$")
# 常见颜色别名 → HEX（出图/视频任一侧用别名写品牌色时仍能对上）。
_COLOR_ALIASES = {
    "红": "ff0000", "红色": "ff0000", "正红": "ff0000",
    "蓝": "0000ff", "蓝色": "0000ff",
    "绿": "008000", "绿色": "008000",
    "黑": "000000", "黑色": "000000",
    "白": "ffffff", "白色": "ffffff",
    "黄": "ffff00", "黄色": "ffff00",
}


def _norm(text):
    """归一化：只留 CJK/字母/数字，丢空白与全部标点（·、→/-> 等差异不算漂移），统一小写。"""
    return re.sub(r"[^0-9A-Za-z㐀-鿿぀-ヿ가-힯]+", "", text or "").lower()


_ALIAS_LOOKUP = {_norm(a): canon for canon, aliases in _FIELD_ALIASES.items() for a in aliases}


def _hex_tokens(text):
    """从一段文本里抽出所有可比对的颜色归一 token（HEX / rgb() / 别名）。

    - `#E60012` / `e60012` → `e60012`；3 位简写 `#f00` → `ff0000`；
    - `rgb(230,0,18)` / `RGB（230, 0, 18）` → `e60012`；
    - 中文别名（红/蓝…）→ 预置 HEX。
    返回归一后小写 HEX 集合（无 `#`）。
    """
    tokens = set()
    s = text or ""
    # rgb(...) 形式
    for m in re.finditer(r"rgb\s*[\(（]\s*(\d{1,3})\D+(\d{1,3})\D+(\d{1,3})", s, re.IGNORECASE):
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        if max(r, g, b) <= 255:
            tokens.add("%02x%02x%02x" % (r, g, b))
    # #HEX 形式（6 位或 3 位简写）
    for m in re.finditer(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", s):
        h = m.group(1).lower()
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        tokens.add(h)
    # 裸 6 位 HEX（无 #，避免误吞普通词：要求前后非字母数字）
    for m in re.finditer(r"(?<![0-9a-zA-Z])([0-9a-fA-F]{6})(?![0-9a-zA-Z])", s):
        tokens.add(m.group(1).lower())
    # 中文别名
    for alias, hexv in _COLOR_ALIASES.items():
        if alias in s:
            tokens.add(hexv)
    return tokens


def _brand_color_inherited(img_val, clip_text):
    """品牌色按 HEX 归一比对：上游声明的任一颜色 token 在视频 prompt 里出现即继承。

    上游若没写出可解析的颜色 token（只有别名/HEX），退回归一化子串比对，避免漏判。
    """
    up_tokens = _hex_tokens(img_val)
    clip_tokens = _hex_tokens(clip_text)
    if up_tokens:
        return bool(up_tokens & clip_tokens)
    # 上游无可解析颜色 token：按归一化子串容忍比对
    return _norm(img_val) in _norm(clip_text)


def _field_inherited(img_val, clip_text):
    """光位/轴线等：归一化超集比对（视频 prompt 含上游原文的归一化即视为继承）。
    paraphrase/标点差异不算漂移（与 n2d compare_field 同口径的超集容忍）。"""
    img_n = _norm(img_val)
    return bool(img_n) and img_n in _norm(clip_text)


def diff_contract(image_contract, clip_prompt_text):
    """上游契约 image_contract(dict) vs 单 Clip 视频 prompt 文本。返回 findings（不含 clip 键）。"""
    findings = []
    text = clip_prompt_text or ""
    for field in HARD_FIELDS:
        val = str(image_contract.get(field, "")).strip()
        if not val:
            continue  # 上游没定义该硬字段，不强求
        if field == "品牌色":
            ok = _brand_color_inherited(val, text)
        else:
            ok = _field_inherited(val, text)
        if not ok:
            findings.append({"severity": "block", "field": field,
                             "msg": f"视频 prompt 未继承上游{field}「{val}」（{field}漂移风险）"})
    for field in SOFT_FIELDS:
        val = str(image_contract.get(field, "")).strip()
        if val and not _field_inherited(val, text):
            findings.append({"severity": "warn", "field": field,
                             "msg": f"视频 prompt 未显式继承{field}「{val}」"})
    return findings


def check_product_handoff(prod_ids, clip_prompt_text):
    """产品形态交接：本镜绑定的 PROD_xx 产品，视频 prompt 必须重新携带产品身份锁定句/资产引用。

    镜像 n2d 的 check_identity_handoff：命名主体（这里是产品）的逐镜 video prompt 若没锁住
    （既无 PROD_xx 资产引用，又无『同一包装/同一 logo/同一品牌色/身份锁定句』），→ block。
    返回 findings（不含 clip 键）。"""
    findings = []
    if not prod_ids:
        return findings
    text = clip_prompt_text or ""
    text_norm = _norm(text)
    has_asset_ref = bool(set(PROD_ID_RE.findall(text)) & set(prod_ids))
    has_lock = any(_norm(m) in text_norm for m in PRODUCT_LOCK_MARKERS)
    if not (has_asset_ref or has_lock):
        findings.append({
            "severity": "block", "field": "产品形态",
            "msg": (f"产品镜绑定 {sorted(prod_ids)}，但视频 prompt 未重携产品身份锁定句/资产引用"
                    "（缺 PROD_xx 或『同一包装/同一 logo/同一品牌色/身份锁定句』）——"
                    "产品形态/logo/品牌色无锚，出视频必抖花漂色。"),
        })
    return findings


# ── 上游契约源解析（出图 00_总览.md → storyboard.json 回退） ───────────────────────
def _extract_section(text, title=CONTRACT_SECTION_TITLE):
    """取 markdown 中标题含 title 的整节正文（到下一个同级/更高级标题为止）；无该节返回 None。"""
    lines = (text or "").splitlines()
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


def parse_overview_contract(overview_text):
    """出图 00_总览.md 全文 → {canonical字段: 原文值}。取「视觉一致性契约」节的 bullet `- 标签：值`。
    无该节 / 无可识别字段 → {}。纯函数·可测。"""
    section = _extract_section(overview_text)
    if section is None:
        section = overview_text or ""  # 无标准节标题时退回全文扫 bullet
    fields = {}
    current = None
    for ln in section.splitlines():
        m = _BULLET_RE.match(ln)
        if m:
            body = m.group(1)
            parts = re.split(r"[：:]", body, maxsplit=1)
            label = parts[0]
            value = parts[1] if len(parts) > 1 else ""
            canon = _ALIAS_LOOKUP.get(_norm(re.sub(r"\*+", "", label)))
            if canon:
                current = canon
                fields.setdefault(canon, value.strip())
            else:
                current = None
        elif current and ln.strip():
            fields[current] = (fields[current] + " " + ln.strip()).strip()
    return {k: v for k, v in fields.items() if v}


def load_contract(root):
    """上游契约单一真值源：① 出图/分镜/prompt/00_总览.md 的视觉契约节；② 回退 storyboard.json.visual_contract。

    返回 (contract_dict, source_rel)。"""
    overview_rel = os.path.join("出图", "分镜", "prompt", "00_总览.md")
    overview_path = os.path.join(root, overview_rel)
    if os.path.isfile(overview_path):
        with open(overview_path, encoding="utf-8", errors="replace") as f:
            parsed = parse_overview_contract(f.read())
        if parsed:
            return parsed, overview_rel
    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {}) or {}
    return sb.get("visual_contract", {}) or {}, os.path.join("脚本", "storyboard.json")


# ── 逐镜：shot → 视频 prompt 文件 + 绑定的 PROD 资产 ─────────────────────────────
def _shot_prod_ids(shot):
    """shot.assets 里值为真的 PROD_xx id 集合。"""
    assets = shot.get("assets") if isinstance(shot, dict) else None
    if not isinstance(assets, dict):
        return set()
    return {k for k, v in assets.items() if k.startswith("PROD_") and v}


def _shot_index_num(name):
    """'镜头03.md' / 'shot_3.txt' / 'S5' → int；提不出 → None。"""
    m = re.search(r"(\d+)", str(name or ""))
    return int(m.group(1)) if m else None


def storyboard_prod_by_index(storyboard):
    """storyboard.json → {1基序号: set(PROD_xx)}，按 shots/clips 顺序。供逐镜 prompt 文件按序号对齐。"""
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    out = {}
    for i, sh in enumerate(shots, 1):
        out[i] = _shot_prod_ids(sh)
    return out


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run(root, out_json=None):
    root = os.path.abspath(root)
    contract, contract_source = load_contract(root)
    sb = load_json(os.path.join(root, "脚本", "storyboard.json"), {}) or {}
    prod_by_index = storyboard_prod_by_index(sb)

    prompt_dir = os.path.join(root, "出视频", "分镜", "prompt")
    results = []
    if os.path.isdir(prompt_dir):
        for name in sorted(os.listdir(prompt_dir)):
            if not name.endswith((".md", ".txt")):
                continue
            with open(os.path.join(prompt_dir, name), encoding="utf-8", errors="replace") as f:
                txt = f.read()
            for fnd in diff_contract(contract, txt):
                fnd["clip"] = name
                results.append(fnd)
            idx = _shot_index_num(name)
            prod_ids = prod_by_index.get(idx, set()) if idx is not None else set()
            for fnd in check_product_handoff(prod_ids, txt):
                fnd["clip"] = name
                results.append(fnd)

    payload = {"schema_version": 1, "kind": "ad_contract_inheritance",
               "contract_source": contract_source, "visual_contract": contract,
               "findings": results,
               "summary": {"block": sum(1 for r in results if r["severity"] == "block"),
                           "warn": sum(1 for r in results if r["severity"] == "warn")}}
    if out_json:
        os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser(description="出图→出视频视觉契约继承机检（拍广告）")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    payload = run(args.project_root, args.json)
    results = payload["findings"]
    b, w = payload["summary"]["block"], payload["summary"]["warn"]
    print(f"# 契约继承机检  block={b}  warn={w}  (契约源={payload['contract_source']})")
    for r in results:
        print(("🔴" if r["severity"] == "block" else "🟡") + f" [{r['clip']}] {r['msg']}")
    if not results:
        print("✅ 视觉契约继承完整（品牌色/光位/轴线/产品形态已继承）")
    sys.exit(1 if b > 0 else 0)


if __name__ == "__main__":
    main()
