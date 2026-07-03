#!/usr/bin/env python3
"""asset_impact.py — 改了某个共享定妆资产，扫出受影响的分镜镜头 + 标记需重出。

市场卖点"改一次人物资产，全剧镜头自动同步"。n2d 定妆库是共享的，但改了某个
`出图/共享/图片/定妆_<X>.png` 后，没机制告诉你"哪些已出镜头引用了它、要重出"——靠人记易漏。
本脚本扫各集 `出图/<集>/prompt/*.md` 的「参考图：」行 + 定妆引用，并读
`出图/共享/identity_registry.json` / `asset_registry.json` 的结构化绑定（镜头 prompt 写了
`CHAR_xx` / `LOC_xx` / `PROP_xx` / `OUTFIT_xx` / `VFX_xx` 或角色/资产名、靠 registry 自动取参考的
镜头同样命中），列出引用该资产的镜头，并按目标 PNG 是否已存在分两类：
**已出图→需重出** / 未出图→待出时自然用新版。

只读（除 --output-batch-tasks / --out 显式落盘外），不改任何产物、不删图。纯标准库。
解析逻辑(normalize/parse_shots/registry 绑定)可单测。

用法：
  python3 asset_impact.py <作品根> <资产名...>               # 人读：受影响镜头清单
  python3 asset_impact.py <作品根> <资产名...> --json         # 喂回 LLM
  python3 asset_impact.py <作品根> <资产名...> --rerun-plan   # 连锁重跑计划（重出图→刷新身份→重出视频→重合成→n2d-batch 命令）
  python3 asset_impact.py <作品根> <资产名...> --rerun-plan --json [--out 计划.md/json]
  python3 asset_impact.py <作品根> <资产名...> --include-video           # 加「已出视频需重生」清单
  python3 asset_impact.py <作品根> <资产名...> --check-native-adapters   # 加「后端身份注册基于旧定妆」提醒
  python3 asset_impact.py <作品根> <资产名...> --output-batch-tasks 计划.json
      # 输出 n2d-batch 可直接消费的任务 JSON（kind=n2d_asset_rerun_plan）：
      # python3 skills/n2d-batch/scripts/queue.py plan <作品根> --from-asset-impact 计划.json
资产名可写 `定妆_沈念.png` / `定妆_沈念_侧` / `沈念` / `冷宫寝殿` / `CHAR_01`，会归一到核心名匹配。
"""
import glob
import json
import os
import re
import sys

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import (  # noqa: E402  产物 kind / registry 路径 / adapter 状态单一真值源
    ASSET_RERUN_PLAN_KIND,
    IDENTITY_ADAPTER_READY_STATUSES,
    IDENTITY_HANDLE_FIELDS,
    asset_registry_path,
    identity_registry_path,
)

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


# ── registry 结构化绑定（盲区①：镜头没写参考图行、靠 registry 自动取参考也算受影响）──

def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _ref_paths(reference_group):
    """reference_group 的所有参考路径（值可为字符串/列表，如 expressions[]）。"""
    out = []
    if not isinstance(reference_group, dict):
        return out
    for value in reference_group.values():
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
    return out


def load_registry_bindings(root):
    """读 identity_registry.json + asset_registry.json，建结构化绑定条目。

    每条 = {"id"(CHAR_/LOC_/PROP_/OUTFIT_/VFX_), "kind"(character|asset),
            "names"(角色名/资产名集合，角色名按 `/`、顿号拆分),
            "keys"(asset_key 与定妆参考路径的核心键集合), "forms"(角色形态原文，供 adapter 检查)}。
    registry 缺失/损坏返回 []——纯文本「参考图：」匹配照旧，不因 registry 缺席而报错。"""
    entries = []
    ident = _read_json(identity_registry_path(root))
    if isinstance(ident, dict):
        for char in ident.get("characters") or []:
            if not isinstance(char, dict):
                continue
            cid = str(char.get("id", "")).strip()
            if not cid:
                continue
            names = {p.strip() for p in re.split(r"[/、,，\s]+", str(char.get("name", ""))) if p.strip()}
            keys, forms = set(), [f for f in char.get("forms") or [] if isinstance(f, dict)]
            for form in forms:
                asset_key = str(form.get("asset_key", "")).strip()
                if asset_key:
                    keys.add(core(asset_key))
                for path in _ref_paths(form.get("reference_group")):
                    keys.add(core(path))
            entries.append({"id": cid, "kind": "character", "names": names, "keys": keys, "forms": forms})
    areg = _read_json(asset_registry_path(root))
    if isinstance(areg, dict):
        for asset in areg.get("assets") or []:
            if not isinstance(asset, dict):
                continue
            aid = str(asset.get("id", "")).strip()
            if not aid:
                continue
            names = {s for s in (str(asset.get("name", "")).strip(),) if s}
            keys = {core(p) for p in _ref_paths(asset.get("reference_group"))}
            entries.append({"id": aid, "kind": "asset", "names": names, "keys": keys, "forms": []})
    return entries


def match_bindings(entries, keys):
    """目标资产核心键 → 命中的 registry 条目（按 ID / 角色·资产名 / 定妆核心键三路匹配）。"""
    keys = set(keys)
    return [e for e in entries if e["id"] in keys or (keys & e["names"]) or (keys & e["keys"])]


# ID 命中要求边界：`CHAR_01` 不得命中 `CHAR_011` / `CHAR_01B`。
_ID_BOUND = r"(?![0-9A-Za-z])"


def shot_references_bindings(shot, bindings):
    """registry 结构化命中：镜头 prompt 文本（标题/参考图行/正文）里出现绑定条目的
    CHAR_/LOC_/PROP_/OUTFIT_/VFX_ ID（带边界）或角色/资产名——覆盖『没写参考图行、
    靠 registry 自动取定妆组』的镜头。"""
    text = shot["title"] + "\n" + shot["refline"] + "\n" + shot["body"]
    for b in bindings:
        if re.search(re.escape(b["id"]) + _ID_BOUND, text):
            return True
        if any(name and name in text for name in b["names"]):
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


def scan(root, assets, *, bindings=None):
    """扫各集分镜 prompt：文本「参考图」匹配 + registry 结构化绑定匹配（盲区①）。
    bindings=None 时自动从 registry 加载并按目标资产过滤；传 [] 可强制只走纯文本匹配。"""
    keys = sorted({core(a) for a in assets if core(a)})
    if bindings is None:
        bindings = match_bindings(load_registry_bindings(root), keys)
    hits = []
    for pf in sorted(glob.glob(os.path.join(root, "出图", "*", "prompt", "*.md"))):
        ep = os.path.basename(os.path.dirname(os.path.dirname(pf)))  # 出图/<集>/prompt/x.md
        try:
            with open(pf, encoding="utf-8") as f:
                shots = parse_shots(f.read())
        except OSError:
            continue
        for s in shots:
            if not (shot_references(s, keys) or shot_references_bindings(s, bindings)):
                continue
            tgt = resolve_target(root, ep, s)
            if tgt is None:  # 00_总览.md 的章节头等：非出图镜头，过滤
                continue
            hits.append({"集": ep, "镜头": s["title"], "目标": tgt[0], "已出图": tgt[1]})
    return keys, hits


# ── 盲区②：已出视频需重生（--include-video）────────────────────────────────

VIDEO_EXTS = (".mp4", ".mov", ".webm", ".m4v")


def _key_in_name(text, key):
    """镜头键命中文件名/文本，要求键后不接数字：`镜头1` 不得命中 `镜头10`。"""
    if not key:
        return False
    return re.search(re.escape(key) + r"(?!\d)", text) is not None


def scan_video_impact(root, hits):
    """受影响镜头 → 「已出视频需重生」清单。

    命中条件（任一即收）：① `出视频/<集>/视频/` 已有该镜头对应 clip（文件名含镜头键或首帧
    PNG 主名）；② `出视频/<集>/prompt/*.md` 引用了受影响 PNG（相对路径或文件名）。
    只看已出图镜头——首帧没落 PNG 不可能有由它派生的 clip。"""
    out = []
    for h in hits:
        if not h["已出图"]:
            continue
        ep = h["集"]
        skey = shot_key(h["镜头"])
        png_rel = h["目标"]
        png_base = os.path.basename(png_rel)
        stem = os.path.splitext(png_base)[0]
        clips = []
        for p in sorted(glob.glob(os.path.join(root, "出视频", ep, "视频", "*"))):
            name = os.path.basename(p)
            if not name.lower().endswith(VIDEO_EXTS):
                continue
            if _key_in_name(name, skey) or _key_in_name(name, stem):
                clips.append(os.path.relpath(p, root))
        prompt_refs = []
        for pf in sorted(glob.glob(os.path.join(root, "出视频", ep, "prompt", "*.md"))):
            try:
                with open(pf, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue
            if png_rel in text or png_base in text:
                prompt_refs.append(os.path.relpath(pf, root))
        if clips or prompt_refs:
            out.append({"集": ep, "镜头": h["镜头"], "首帧": png_rel,
                        "clips": clips, "prompt引用": prompt_refs})
    return out


# ── 盲区③：后端身份注册基于旧定妆（--check-native-adapters）───────────────────

def native_adapter_notices(bindings):
    """被改角色在 registry identity_adapters 里已有 registered/ready 且带句柄的后端 →
    「该后端身份注册基于旧定妆，需重新注册」提醒（image/video 各后端 + LoRA）。"""
    notices = []
    for b in bindings:
        if b["kind"] != "character":
            continue
        for form in b["forms"]:
            adapters = form.get("identity_adapters")
            if not isinstance(adapters, dict):
                continue
            form_name = str(form.get("form", "") or "")
            sections = [(area, adapters.get(area)) for area in ("image", "video")]
            lora = adapters.get("lora")
            if isinstance(lora, dict):
                sections.append(("lora", {"lora": lora}))
            for area, section in sections:
                if not isinstance(section, dict):
                    continue
                for backend, cfg in section.items():
                    if not isinstance(cfg, dict):
                        continue
                    status = str(cfg.get("status", "")).strip()
                    handles = {f: cfg.get(f) for f in IDENTITY_HANDLE_FIELDS
                               if str(cfg.get(f) or "").strip()}
                    if status in IDENTITY_ADAPTER_READY_STATUSES and handles:
                        notices.append({
                            "角色": b["id"], "形态": form_name, "区域": area, "后端": backend,
                            "status": status, "句柄": handles,
                            "提醒": "该后端身份注册基于旧定妆，定妆变更后需重新注册",
                        })
    return notices


# ── 盲区④：n2d-batch 直读任务 JSON（--output-batch-tasks）─────────────────────

def build_batch_tasks(root, keys, hits, video_impacts=None):
    """输出 n2d-batch `queue.py plan --from-asset-impact` 可直接消费的任务 JSON。

    字段对齐 queue.py 的 rerun 任务入参：每条 = episode / rerun_from / scope /
    affected_artifacts / affected_shots；顶层 kind=ASSET_RERUN_PLAN_KIND。
    已出图镜头按集聚合成 image 重跑任务；--include-video 命中的 clip 另出 video 重跑任务。"""
    label = "、".join(keys) or "(空)"
    rerun = [h for h in hits if h["已出图"]]
    by_ep = {}
    for h in rerun:
        by_ep.setdefault(h["集"], []).append(h)
    tasks = []
    for ep in sorted(by_ep):
        tasks.append({
            "episode": ep,
            "rerun_from": "image",
            "scope": f"定妆{label}变更连锁·重出受影响镜头",
            "affected_artifacts": sorted({h["目标"] for h in by_ep[ep] if h["目标"]}),
            "affected_shots": sorted({shot_key(h["镜头"]) or h["镜头"] for h in by_ep[ep]}),
        })
    video_by_ep = {}
    for v in video_impacts or []:
        video_by_ep.setdefault(v["集"], []).append(v)
    for ep in sorted(video_by_ep):
        rows = video_by_ep[ep]
        tasks.append({
            "episode": ep,
            "rerun_from": "video",
            "scope": f"定妆{label}变更连锁·重生已出视频 clip",
            "affected_artifacts": sorted({c for v in rows for c in v["clips"]}),
            "affected_shots": sorted({shot_key(v["镜头"]) or v["镜头"] for v in rows}),
        })
    return {
        "kind": ASSET_RERUN_PLAN_KIND,
        "version": 1,
        "root": root,
        "assets": keys,
        "rerun_tasks": tasks,
    }


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


def _pop_value_flag(argv, flag):
    """从 argv 摘走 `<flag> <值>`，返回 (值或None, 余下argv)。"""
    if flag not in argv:
        return None, argv
    i = argv.index(flag)
    value = argv[i + 1] if i + 1 < len(argv) else None
    return value, argv[:i] + argv[i + 2:]


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    as_json = "--json" in argv
    rerun_plan = "--rerun-plan" in argv
    include_video = "--include-video" in argv
    check_adapters = "--check-native-adapters" in argv
    out_path, argv = _pop_value_flag(argv, "--out")
    batch_out, argv = _pop_value_flag(argv, "--output-batch-tasks")
    argv = [a for a in argv if a not in ("--json", "--rerun-plan", "--include-video", "--check-native-adapters")]
    root, assets = argv[0], argv[1:]
    if not assets:
        sys.exit("⛔ 至少给一个资产名，如：定妆_沈念 / 沈念 / 冷宫寝殿")
    if not os.path.isdir(os.path.join(root, "出图")):
        sys.exit(f"⛔ {root}/出图 不存在")

    raw_keys = sorted({core(a) for a in assets if core(a)})
    bindings = match_bindings(load_registry_bindings(root), raw_keys)
    keys, hits = scan(root, assets, bindings=bindings)
    rerun = [h for h in hits if h["已出图"]]
    pending = [h for h in hits if not h["已出图"]]
    video_impacts = scan_video_impact(root, hits) if include_video else None
    adapter_notices = native_adapter_notices(bindings) if check_adapters else None

    if batch_out:
        plan_tasks = build_batch_tasks(root, keys, hits, video_impacts=video_impacts)
        with open(batch_out, "w", encoding="utf-8") as f:
            json.dump(plan_tasks, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"[batch-tasks] wrote {batch_out}（共 {len(plan_tasks['rerun_tasks'])} 条任务）")
        print(f"[batch-tasks] 对接：python3 skills/n2d-batch/scripts/queue.py plan {root} --from-asset-impact {batch_out}")

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
        payload = {"资产": keys, "引用镜头数": len(hits),
                   "需重出": rerun, "待出图": pending}
        if video_impacts is not None:
            payload["已出视频需重生"] = video_impacts
        if adapter_notices is not None:
            payload["后端身份提醒"] = adapter_notices
        print(json.dumps(payload, ensure_ascii=False, indent=2))
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
    if video_impacts is not None:
        if video_impacts:
            print("\n🎬 已出视频需重生（首帧 PNG 变了，由它派生的 clip 必须回 n2d-video 重出）：")
            for v in video_impacts:
                refs = "、".join(v["clips"] + v["prompt引用"])
                print(f"  - {v['集']} · {v['镜头']} → {refs}")
        else:
            print("\n🎬 已出视频需重生：无（受影响镜头还没有对应 clip / 视频 prompt 引用）")
    if adapter_notices is not None:
        if adapter_notices:
            print("\n🪪 后端身份提醒（registered/ready 且带句柄——身份注册基于旧定妆，需重新注册）：")
            for n in adapter_notices:
                handles = "、".join(f"{k}={v}" for k, v in n["句柄"].items())
                print(f"  - {n['角色']}/{n['形态']} · {n['区域']}.{n['后端']} status={n['status']} ({handles})")
        else:
            print("\n🪪 后端身份提醒：无（被改角色没有 registered/ready 的后端身份）")
    if not hits:
        print("\n（没有镜头引用该资产——确认资产名拼写，或它只是共享层未被分镜引用）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
