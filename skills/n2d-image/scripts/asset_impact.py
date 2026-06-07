#!/usr/bin/env python3
"""asset_impact.py — 改了某个共享定妆资产，扫出受影响的分镜镜头 + 标记需重出。

市场卖点"改一次人物资产，全剧镜头自动同步"。n2d 定妆库是共享的，但改了某个
`出图/common/定妆_<X>.png` 后，没机制告诉你"哪些已出镜头引用了它、要重出"——靠人记易漏。
本脚本扫各集 `出图/<集>/prompt/*.md` 的「参考图：」行 + 定妆引用，列出引用该资产的镜头，
并按目标 PNG 是否已存在分两类：**已出图→需重出** / 未出图→待出时自然用新版。

只读，不改任何文件、不删图。纯标准库。解析逻辑(normalize/parse_shots)可单测。

用法：
  python3 asset_impact.py <作品根> <资产名...>          # 人读
  python3 asset_impact.py <作品根> <资产名...> --json    # 喂回 LLM
资产名可写 `定妆_沈念.png` / `定妆_沈念_侧` / `沈念` / `冷宫寝殿`，会归一到核心名匹配。
"""
import glob
import json
import os
import re
import sys

VIEW_SUFFIXES = ("正脸", "正面", "侧", "侧脸", "背", "背面", "半身", "全身", "三视图")


def normalize(name):
    """`出图/common/定妆_沈念_侧.png` / `定妆_沈念` / `沈念` → 归一名（去目录/扩展/定妆_前缀）。"""
    s = str(name).strip().replace("\\", "/").split("/")[-1]
    if s.lower().endswith(".png"):
        s = s[:-4]
    if s.startswith("定妆_"):
        s = s[len("定妆_"):]
    return s


def core(name):
    """核心匹配键：去掉尾部的视图后缀（侧/半身/三视图…），保留角色/场景/状态主体。
    例：沈念_侧→沈念；沈念_觉醒_半身→沈念_觉醒；冷宫寝殿→冷宫寝殿。"""
    s = normalize(name)
    parts = s.split("_")
    while len(parts) > 1 and parts[-1] in VIEW_SUFFIXES:
        parts.pop()
    return "_".join(parts)


def ref_tokens(line):
    """把「参考图：沈念、柳娘子、冷宫寝殿」拆成 ['沈念','柳娘子','冷宫寝殿']。"""
    body = re.sub(r"^[\s>*-]*参考图\s*[:：]\s*", "", line.strip())
    return [t.strip() for t in re.split(r"[、,，/\s]+", body) if t.strip()]


def parse_shots(text):
    r"""解析一个分镜出图 prompt（按 `## ` 分块）。兼容两种 schema：
    ① 本宫式：`## 镜头 N（…）` + `目标：出图/…png` + `参考图：a、b、c`(裸名)
    ② 看花胖子式：`## Clip N · 镜N（…）` + `**参考图**：定妆_x.png …`(带前缀)，无目标行(目标由 Clip 号推)
    返回 [{title, target, refline, body}]。"""
    shots = []
    cur = None
    for ln in text.splitlines():
        if ln.startswith("## "):
            if cur:
                shots.append(cur)
            cur = {"title": ln[3:].strip(), "target": None, "refline": "", "body": []}
        elif cur is not None:
            cur["body"].append(ln)
            m = re.match(r"^\s*目标\s*[:：]\s*(.+)$", ln)
            if m:
                cur["target"] = m.group(1).strip().strip("`").strip()
            if re.match(r"^[\s>*-]*参考图\s*[:：]", ln):  # `*` 类覆盖 `**参考图**：`
                cur["refline"] = ln
    if cur:
        shots.append(cur)
    for s in shots:
        s["body"] = "\n".join(s["body"])
    return shots


# `定妆_<键>` 命中要求键后是真边界，避免前缀误伤：`定妆_沈` 不该命中 `定妆_沈念.png`、
# `冷宫` 不该命中 `冷宫寝殿`。边界 = .png / 视图后缀(_侧…) / 标点空白 / 行尾。
# 注：状态形态(如 沈念_觉醒)是独立 PNG，查 `沈念` 不连带命中——要重出该形态请显式查 `沈念_觉醒`。
_PREFIX_BOUND = r"(?:\.png|_(?:%s)|[、,，/\s.。)）]|$)" % "|".join(VIEW_SUFFIXES)


def _refs_prefixed(text, k):
    return re.search(r"定妆_" + re.escape(k) + _PREFIX_BOUND, text) is not None


def shot_references(shot, keys):
    """该镜头是否引用了任一目标资产。两 schema 都靠：参考图行裸名 token 命中，
    或正文/参考图行出现 `定妆_<核心键>`（带前缀写法，需过 _refs_prefixed 边界判定）。
    keys = 各资产核心键集合。"""
    text = shot["refline"] + "\n" + shot["body"]
    ref_core = {core(t) for t in ref_tokens(shot["refline"])} if shot["refline"] else set()
    for k in keys:
        if not k:
            continue
        if k in ref_core or _refs_prefixed(text, k):
            return True
    return False


def shot_key(title):
    """从标题推镜头键，用于无 目标 行时定位 PNG：`Clip 1`→`Clip_01`；`镜头 3`→`镜头3`。"""
    m = re.search(r"Clip\s*(\d+)", title)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"镜头\s*(\d+)", title)
    if m:
        return f"镜头{int(m.group(1))}"
    return None


def resolve_target(root, ep, shot):
    """返回 (显示用目标, 是否已出图) 或 None(非出图镜头)。
    优先显式 目标 行；否则按 Clip/镜头 号 glob `出图/<集>/<key>*.png`。"""
    if shot["target"] and shot["target"].lower().endswith(".png"):
        return shot["target"], os.path.isfile(os.path.join(root, shot["target"]))
    key = shot_key(shot["title"])
    if not key:
        return None
    matches = sorted(glob.glob(os.path.join(root, "出图", ep, key + "*.png")))
    if matches:
        return os.path.relpath(matches[0], root), True
    return f"出图/{ep}/{key}*.png", False


def scan(root, assets):
    keys = sorted({core(a) for a in assets if core(a)})
    hits = []
    for pf in sorted(glob.glob(os.path.join(root, "出图", "*", "prompt", "*.md"))):
        ep = os.path.basename(os.path.dirname(os.path.dirname(pf)))  # 出图/<集>/prompt/x.md
        try:
            with open(pf, encoding="utf-8") as f:
                shots = parse_shots(f.read())
        except OSError:
            continue
        for s in shots:
            if not shot_references(s, keys):
                continue
            tgt = resolve_target(root, ep, s)
            if tgt is None:  # 00_总览.md 的章节头等：非出图镜头，过滤
                continue
            hits.append({"集": ep, "镜头": s["title"], "目标": tgt[0], "已出图": tgt[1]})
    return keys, hits


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    root, assets = argv[0], argv[1:]
    if not assets:
        sys.exit("⛔ 至少给一个资产名，如：定妆_沈念 / 沈念 / 冷宫寝殿")
    if not os.path.isdir(os.path.join(root, "出图")):
        sys.exit(f"⛔ {root}/出图 不存在")

    keys, hits = scan(root, assets)
    rerun = [h for h in hits if h["已出图"]]
    pending = [h for h in hits if not h["已出图"]]

    if as_json:
        print(json.dumps({"资产": keys, "引用镜头数": len(hits),
                          "需重出": rerun, "待出图": pending},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"=== 定妆变更影响：{('、'.join(keys)) or '(空)'} ===")
    print(f"引用该资产的镜头 {len(hits)} 个 | 🔁 已出图·需重出 {len(rerun)} | ⬜ 未出图·待出时用新版 {len(pending)}")
    if rerun:
        print("\n🔁 需重出（已落 PNG，资产变了要回 n2d-image 重出这些镜头）：")
        for h in rerun:
            print(f"  - {h['集']} · {h['镜头']} → {h['目标']}")
    if pending:
        print("\n⬜ 待出图（还没出，下次出图自然用新版，无需额外动作）：")
        for h in pending:
            print(f"  - {h['集']} · {h['镜头']}")
    if not hits:
        print("\n（没有镜头引用该资产——确认资产名拼写，或它只是共享层未被分镜引用）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
