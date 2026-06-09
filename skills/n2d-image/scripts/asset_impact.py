#!/usr/bin/env python3
"""asset_impact.py — 改了某个共享定妆资产，扫出受影响的分镜镜头 + 标记需重出。

市场卖点"改一次人物资产，全剧镜头自动同步"。n2d 定妆库是共享的，但改了某个
`出图/共享/图片/定妆_<X>.png` 后，没机制告诉你"哪些已出镜头引用了它、要重出"——靠人记易漏。
本脚本扫各集 `出图/<集>/prompt/*.md` 的「参考图：」行 + 定妆引用，列出引用该资产的镜头，
并按目标 PNG 是否已存在分两类：**已出图→需重出** / 未出图→待出时自然用新版。

只读，不改任何文件、不删图。纯标准库。解析逻辑(normalize/parse_shots)可单测。

用法：
  python3 asset_impact.py <作品根> <资产名...>               # 人读：受影响镜头清单
  python3 asset_impact.py <作品根> <资产名...> --json         # 喂回 LLM
  python3 asset_impact.py <作品根> <资产名...> --rerun-plan   # 连锁重跑计划（重出图→刷新身份→重出视频→重合成→n2d-batch 命令）
  python3 asset_impact.py <作品根> <资产名...> --rerun-plan --json [--out 计划.md/json]
资产名可写 `定妆_沈念.png` / `定妆_沈念_侧` / `沈念` / `冷宫寝殿`，会归一到核心名匹配。
"""
import glob
import json
import os
import re
import sys

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import ASSET_RERUN_PLAN_KIND  # noqa: E402  产物 kind 单一真值源

VIEW_SUFFIXES = ("正脸", "正面", "侧", "侧脸", "背", "背面", "半身", "全身", "三视图")


def normalize(name):
    """`出图/共享/图片/定妆_沈念_侧.png` / `定妆_沈念` / `沈念` → 归一名（去目录/扩展/定妆_前缀）。"""
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
    matches = sorted(glob.glob(os.path.join(root, "出图", ep, "图片", key + "*.png")))
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


def build_rerun_plan(root, keys, hits):
    """把"改了定妆"的影响清单 → 连锁重跑计划：受影响集 → 重出图 → 刷新身份 →
    下游重出视频/重合成 → 可直接跑的 n2d-batch 最小范围重跑命令。把人工排查自动化。"""
    rerun = [h for h in hits if h["已出图"]]
    pending = [h for h in hits if not h["已出图"]]
    by_ep = {}
    for h in rerun:
        by_ep.setdefault(h["集"], []).append(h)
    episodes = sorted(by_ep)
    assets_label = "、".join(keys) or "(空)"
    steps = []
    if rerun:
        steps.append({
            "order": 1, "skill": "n2d-image", "action": "重出受影响镜头（已落 PNG）",
            "scope": [{"集": h["集"], "镜头": h["镜头"], "目标": h["目标"]} for h in rerun],
            "note": "用新版定妆 PNG 作参考重出这些镜头；未出图的镜头无需动作（下次出图自然用新版）。",
        })
        steps.append({
            "order": 2, "skill": "n2d-identity", "action": "刷新身份注册层 + 跨集漂移",
            "command": f"python3 skills/n2d-identity/scripts/identity.py {root} --write",
            "note": "定妆资产变了，reference_group/adapter matrix 与 drift 报表要重算。",
        })
        steps.append({
            "order": 3, "skill": "n2d-video", "action": "受影响镜头对应 Clip 重出视频",
            "note": "首帧 PNG 变了，由它图生视频的 Clip 必须重出；按 storyboard 镜头↔Clip 映射定位（见 故事板.md）。",
        })
        steps.append({
            "order": 4, "skill": "n2d-compose", "action": "受影响集重合成成片",
            "scope": episodes,
            "note": "重出的 Clip 并回后重跑合成；接缝按 seam_concat 自动处理。",
        })
        batch_cmds = []
        for ep in episodes:
            arts = sorted({h["目标"] for h in by_ep[ep] if h["目标"]})
            shots = sorted({shot_key(h["镜头"]) or h["镜头"] for h in by_ep[ep]})
            cmd = [f"python3 skills/n2d-batch/scripts/queue.py plan {root}",
                   f"--episodes {ep}", "--rerun-from image",
                   f'--scope "定妆{assets_label}变更连锁"']
            for a in arts:
                cmd.append(f'--affected-artifact "{a}"')
            for s in shots:
                cmd.append(f'--affected-shot "{s}"')
            batch_cmds.append(" \\\n    ".join(cmd))
        steps.append({
            "order": 5, "skill": "n2d-batch", "action": "最小范围重跑队列（每集一条，只重跑受影响镜头/产物）",
            "commands": batch_cmds,
        })
    return {
        "kind": ASSET_RERUN_PLAN_KIND, "version": 1, "root": root,
        "assets": keys, "affected_episodes": episodes,
        "rerun_count": len(rerun), "pending_count": len(pending),
        "rerun_shots": rerun, "pending_shots": pending, "steps": steps,
        "warnings": ([] if rerun else ["没有已出图镜头引用该资产——无需连锁重跑（未出图镜头下次出图自然用新版）"]),
    }


def render_rerun_plan(plan):
    lines = [f"# 定妆变更连锁重跑计划：{('、'.join(plan['assets'])) or '(空)'}", "",
             f"- 受影响集：{('、'.join(plan['affected_episodes'])) or '无'}",
             f"- 🔁 已出图·需重出镜头：{plan['rerun_count']} | ⬜ 待出图：{plan['pending_count']}", ""]
    for w in plan["warnings"]:
        lines.append(f"> ⚠️ {w}")
    if plan["warnings"]:
        lines.append("")
    for st in plan["steps"]:
        lines.append(f"## 步骤 {st['order']} · {st['skill']} — {st['action']}")
        if st.get("note"):
            lines.append(f"- {st['note']}")
        for h in st.get("scope", []) if isinstance(st.get("scope"), list) and st.get("scope") and isinstance(st["scope"][0], dict) else []:
            lines.append(f"  - {h['集']} · {h['镜头']} → {h['目标']}")
        if isinstance(st.get("scope"), list) and st.get("scope") and isinstance(st["scope"][0], str):
            lines.append(f"  - 集：{('、'.join(st['scope']))}")
        if st.get("command"):
            lines += ["", "```bash", st["command"], "```"]
        for c in st.get("commands", []):
            lines += ["", "```bash", c, "```"]
        lines.append("")
    return "\n".join(lines)


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    as_json = "--json" in argv
    rerun_plan = "--rerun-plan" in argv
    out_path = None
    if "--out" in argv:
        i = argv.index("--out")
        out_path = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    argv = [a for a in argv if a not in ("--json", "--rerun-plan")]
    root, assets = argv[0], argv[1:]
    if not assets:
        sys.exit("⛔ 至少给一个资产名，如：定妆_沈念 / 沈念 / 冷宫寝殿")
    if not os.path.isdir(os.path.join(root, "出图")):
        sys.exit(f"⛔ {root}/出图 不存在")

    keys, hits = scan(root, assets)
    rerun = [h for h in hits if h["已出图"]]
    pending = [h for h in hits if not h["已出图"]]

    if rerun_plan:
        plan = build_rerun_plan(root, keys, hits)
        text = json.dumps(plan, ensure_ascii=False, indent=2) if as_json else render_rerun_plan(plan)
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text + ("\n" if not text.endswith("\n") else ""))
            print(f"[rerun-plan] wrote {out_path}")
        else:
            print(text)
        return 0

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
