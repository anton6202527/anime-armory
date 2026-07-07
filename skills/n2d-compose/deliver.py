#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d 一母带 → 全平台交付矩阵（G10）：从一集成片母带派生 多比例 × 多时长 cutdown × 平台规格，
落 `合成/交付/<集>/`。

**vendored fork（参照同仓另一条创作线的成熟交付实现，复制改写适配 n2d 语境）·不跨线 import·不碰 n2d/_lib**：
  - 交付规格由本作品的**选择点**决定（不写死单一平台）：读 `<作品根>/_设置.md` 的
    `目标平台 / 画幅 / 字幕语言`，派生应出哪些比例、哪些时长、响度目标。本脚本只用一个**最小的本地
    设置解析**（正则抠 `键: 值`），不引 n2d/_lib 的 get_setting，保持 n2d-compose 自包含可单测。
  - 比例派生：母带画幅（9:16 竖屏默认）视为原生不重出；选「多比例」时再为横屏/方版派生 reframe 件。
    竖→横/方默认用 `pad`（加边保全画），避免裁掉竖屏母带上下信息。
  - 时长派生：母带为正片时长；按 cutdown 方案派生 30s/15s 引流版（reframe.py 选镜保钩子/爽点/反转/集尾）。
  - 响度目标复用本目录 `loudness_conform.PLATFORM_TARGETS`（按平台 -14/-23/-16 LUFS），不重造。

矩阵无成片母带 → **优雅报错**（不臆造），提示先 n2d-compose 合成。`--run` 实际执行派生命令（需 ffmpeg）。

用法：
    python3 deliver.py <作品根> 第1集                    # 出交付计划 JSON + 命令清单
    python3 deliver.py <作品根> 第1集 --run             # 实际派生（cutdown + reframe）
    python3 deliver.py <作品根> 第1集 --aspects 9:16,16:9 --durations 15s,30s   # 显式覆盖
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import loudness_conform  # noqa: E402  本目录·复用平台响度目标（PLATFORM_TARGETS）


# ── 选择点解析（最小本地实现·不引 n2d/_lib，保持自包含可测） ──────────────────

# 目标平台（_设置.md 候选）→ 响度平台键（loudness_conform.PLATFORM_TARGETS）。
PLATFORM_LOUDNESS_KEY = {
    "抖音": "tiktok", "快手": "tiktok", "tiktok": "tiktok",
    "b站": "bilibili", "bilibili": "bilibili", "哔哩": "bilibili",
    "youtube": "youtube", "油管": "youtube",
    "红果": "default", "番茄": "default", "小红书": "default",
    "reelshort": "default", "广电": "broadcast", "电视": "broadcast",
}

# 平台 → 推荐交付比例（投放主流画幅）。跨平台/未定 → 多比例兜底。
PLATFORM_ASPECTS = {
    "抖音": ["9:16"], "快手": ["9:16"], "tiktok": ["9:16"], "reelshort": ["9:16"],
    "小红书": ["9:16", "1:1"], "红果": ["9:16"], "番茄": ["9:16"],
    "b站": ["16:9", "9:16"], "bilibili": ["16:9", "9:16"],
    "youtube": ["16:9", "9:16"], "油管": ["16:9", "9:16"],
}

ALL_ASPECTS = ("9:16", "16:9", "1:1")


def parse_setting(text, key):
    """从 _设置.md 抠 `键: 值` / `键：值` / `- 键: 值`。返回去空白的值或 None。纯函数·可测。"""
    if not text:
        return None
    pat = re.compile(r"^[\s\-*>|]*" + re.escape(key) + r"\s*[:：]\s*(.+?)\s*$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return None
    val = m.group(1).strip().strip("`").strip()
    # 去掉表格尾管线/括注
    val = val.split("|")[0].split("（")[0].split("(")[0].strip()
    return val or None


def loudness_key_for_platform(platform):
    """目标平台 → loudness_conform 平台键。未知/未定 → default。纯函数·可测。"""
    if not platform:
        return "default"
    p = platform.strip().lower()
    for token, key in PLATFORM_LOUDNESS_KEY.items():
        if token in p:
            return key
    return "default"


def aspects_for(platform, aspect_setting):
    """派生交付比例集合。纯函数·可测。

    优先级：画幅=多比例 → 全比例；否则按目标平台推荐画幅；都没有 → 退回母带画幅单比例。
    `aspect_setting`（_设置.md「画幅」）作为母带原生比例。"""
    native = "9:16"
    if aspect_setting:
        a = aspect_setting.strip().replace("：", ":")
        if "16:9" in a:
            native = "16:9"
        elif "9:16" in a:
            native = "9:16"
        elif "多比例" in a:
            return list(ALL_ASPECTS), native if native in ALL_ASPECTS else "9:16"
    out = None
    if platform:
        p = platform.strip().lower()
        for token, ratios in PLATFORM_ASPECTS.items():
            if token in p:
                out = list(ratios)
                break
        if "跨平台" in p:
            out = list(ALL_ASPECTS)
    if not out:
        out = [native]
    # 母带原生比例置首（视作原生，不 reframe；其余派生 reframe）
    ordered = [native] + [a for a in out if a != native]
    return ordered, native


def durations_for(duration_setting, master_label="正片"):
    """派生 cutdown 时长集合（不含母带本身）。默认正片 → 30s/15s 引流版。纯函数·可测。"""
    if duration_setting:
        toks = [t.strip() for t in re.split(r"[、,，\s]+", duration_setting) if t.strip()]
        return [t for t in toks if t and "正片" not in t and "主片" not in t]
    return ["30s", "15s"]


# ── 母带定位 + 矩阵构建 ──────────────────────────────────────────────────────

def _is_backup_or_work_cut(path):
    name = os.path.basename(str(path or "")).lower()
    return any(token in name for token in (".pre_", ".pre-", ".bak", ".backup", ".tmp", ".loudnorm_tmp"))


def find_master(root, ep):
    """合成/<集>/ 下找母带，排除 loudnorm/backup/temp 派生件。无 → None。"""
    base = os.path.join(root, "合成", ep)
    for name in (f"成片_{ep}_zh.mp4", f"成片_{ep}.mp4"):
        preferred = os.path.join(base, name)
        if os.path.isfile(preferred):
            return preferred
    cands = [p for p in sorted(glob.glob(os.path.join(base, "成片_*.mp4"))) if not _is_backup_or_work_cut(p)]
    if not cands:
        return None
    return max(cands, key=lambda p: os.path.getmtime(p))


def _safe(label):
    return str(label).strip().lower().replace(" ", "").replace(":", "x") or "var"


def build_matrix(root, ep, platform, aspect_setting, duration_setting,
                 aspects_override=None, durations_override=None):
    """派生交付矩阵 deliverable 列表（纯计算·不落盘·可测）。

    返回 dict：master 路径、native 比例、响度目标、deliverables[]（cutdown × reframe 展开）。"""
    root = os.path.abspath(root)
    if aspects_override:
        aspects = list(aspects_override)
        native = aspects[0]
    else:
        aspects, native = aspects_for(platform, aspect_setting)
    durations = list(durations_override) if durations_override is not None \
        else durations_for(duration_setting)
    lkey = loudness_key_for_platform(platform)
    target_lufs = loudness_conform.PLATFORM_TARGETS.get(lkey, loudness_conform.PLATFORM_TARGETS["default"])

    master = find_master(root, ep)
    deliverables = []

    # 1) 多时长 cutdown（母带原生比例下重剪）
    for d in durations:
        rel = os.path.join("合成", "交付", ep, f"成片_{_safe(d)}.mp4")
        deliverables.append({
            "deliverable_id": f"cut_{_safe(d)}",
            "label": f"cutdown {d}",
            "kind": "cutdown", "duration": d, "aspect": native,
            "expected_path": rel,
            "exists": os.path.isfile(os.path.join(root, rel)),
        })

    # 2) 多比例 reframe（母带 + 各 cutdown 派生非原生比例）。母带原生比例不重出。
    for asp in aspects:
        if asp == native:
            continue
        # 母带 reframe
        rel = os.path.join("合成", "交付", ep, f"成片_{_safe(asp)}.mp4")
        deliverables.append({
            "deliverable_id": f"reframe_{_safe(asp)}",
            "label": f"reframe {asp}",
            "kind": "reframe", "duration": "正片", "aspect": asp,
            "expected_path": rel,
            "exists": os.path.isfile(os.path.join(root, rel)),
        })

    return {
        "schema_version": 1, "kind": "n2d_delivery_matrix",
        "project_root": root, "episode": ep,
        "platform": platform or "未定", "loudness_key": lkey, "target_lufs": target_lufs,
        "native_aspect": native, "aspects": aspects, "durations": durations,
        "master": (os.path.relpath(master, root) if master else None),
        "deliverables": deliverables,
    }


def aspect_value(s):
    a, _, b = s.replace("x", ":").partition(":")
    try:
        return float(a) / float(b)
    except (ValueError, ZeroDivisionError):
        return 9 / 16


def run_deliverables(root, ep, matrix):
    """实际派生：cutdown.py + reframe.py。返回 [{id, ok, msg}]。无 ffmpeg → 各项 skip。"""
    import cutdown as _cut
    import reframe as _ref
    results = []
    native = matrix["native_aspect"]
    master = matrix["master"]
    master_abs = os.path.join(root, master) if master else None

    # cutdown：读 storyboard + 镜头时长，规划 + 渲染
    sb = _cut.load_json(os.path.join(root, "脚本", ep, "storyboard.json"), {}) or {}
    clips = sb.get("clips") or sb.get("shots") or []
    dmap = _cut.duration_map_from_finalize(
        _cut.load_json(os.path.join(root, "脚本", ep, "镜头时长.json"), {}))

    for item in matrix["deliverables"]:
        out_abs = os.path.join(root, item["expected_path"])
        if item["kind"] == "cutdown":
            target = _cut.parse_seconds(item["duration"])
            kept, total, findings = _cut.plan_cutdown(clips, target, duration_map=dmap)
            plan_path = os.path.join(root, "合成", "交付", ep, f"plan_{_safe(item['duration'])}.json")
            os.makedirs(os.path.dirname(plan_path), exist_ok=True)
            blocked = any(f["severity"] in ("block", "error") for f in findings)
            with open(plan_path, "w", encoding="utf-8") as f:
                json.dump({"target_seconds": target, "total_seconds": total,
                           "kept_shots": [_cut.shot_id(s) for s in kept],
                           "blocked": blocked, "findings": findings}, f,
                          ensure_ascii=False, indent=2)
            if blocked:
                results.append({"id": item["deliverable_id"], "ok": False,
                                "msg": "cutdown 计划被阻断（镜头时长缺失）：" +
                                       "；".join(x["msg"] for x in findings if x["severity"] in ("block", "error"))})
                continue
            ok, msg, _ = _cut.render_cutdown(root, ep, kept, item["duration"], out_abs, native)
            results.append({"id": item["deliverable_id"], "ok": ok, "msg": msg})
        elif item["kind"] == "reframe":
            if not master_abs or not os.path.isfile(master_abs):
                results.append({"id": item["deliverable_id"], "ok": False,
                                "msg": "缺母带成片，无法 reframe（先 n2d-compose 合成）"})
                continue
            # 竖屏母带转横/方默认 pad（保全画）；目标仍竖（9:16）则 crop。
            mode = "pad" if aspect_value(item["aspect"]) > aspect_value(native) else "crop"
            src = "1080x1920" if aspect_value(native) < 1 else "1920x1080"
            vf = _ref.reframe_filter(src, item["aspect"], mode)
            ok, msg = _ref.render_reframe(master_abs, out_abs, vf)
            results.append({"id": item["deliverable_id"], "ok": ok, "msg": f"({mode}) {msg}"})
    return results


def main():
    ap = argparse.ArgumentParser(description="n2d 一母带 → 全平台交付矩阵（G10）")
    ap.add_argument("project_root")
    ap.add_argument("episode", help="第N集")
    ap.add_argument("--json", default=None, help="输出 delivery_matrix.json（默认 合成/交付/<集>/delivery_matrix.json）")
    ap.add_argument("--run", action="store_true", help="实际派生 cutdown + reframe（需 ffmpeg）")
    ap.add_argument("--aspects", default=None, help="显式覆盖比例集，逗号分隔，如 9:16,16:9,1:1（首个=母带原生）")
    ap.add_argument("--durations", default=None, help="显式覆盖 cutdown 时长集，逗号分隔，如 30s,15s")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    ep = args.episode

    settings_path = os.path.join(root, "_设置.md")
    settings_text = ""
    if os.path.isfile(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            settings_text = f.read()
    platform = parse_setting(settings_text, "目标平台")
    aspect_setting = parse_setting(settings_text, "画幅")
    duration_setting = parse_setting(settings_text, "交付时长")

    aspects_override = ([a.strip() for a in args.aspects.split(",") if a.strip()]
                        if args.aspects else None)
    durations_override = ([d.strip() for d in args.durations.split(",") if d.strip()]
                          if args.durations else None)

    matrix = build_matrix(root, ep, platform, aspect_setting, duration_setting,
                          aspects_override, durations_override)

    # 优雅报错：缺母带成片不臆造
    if matrix["master"] is None:
        print(f"⛔ 缺成片母带：合成/{ep}/成片_*.mp4 不存在——先 n2d-compose 合成本集再出交付矩阵。",
              file=sys.stderr)
        # 仍落计划（交付件全 ⬜），便于看将派生什么
        json_path = args.json or os.path.join(root, "合成", "交付", ep, "delivery_matrix.json")
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, ensure_ascii=False, indent=2)
        sys.exit(2)

    results = None
    if args.run:
        results = run_deliverables(root, ep, matrix)
        for item in matrix["deliverables"]:
            for r in results:
                if r["id"] == item["deliverable_id"]:
                    item["render_ok"] = r["ok"]
                    item["render_msg"] = r["msg"]
                    item["exists"] = os.path.isfile(os.path.join(root, item["expected_path"]))

    json_path = args.json or os.path.join(root, "合成", "交付", ep, "delivery_matrix.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)

    print(f"# n2d 交付矩阵  {ep}  平台={matrix['platform']}  母带={matrix['master']}")
    print(f"  比例={', '.join(matrix['aspects'])}（原生 {matrix['native_aspect']}）  "
          f"cutdown={', '.join(matrix['durations']) or '无'}  响度目标 {matrix['target_lufs']} LUFS")
    for item in matrix["deliverables"]:
        flag = "✅" if item.get("exists") else "⬜"
        line = f"{flag} {item['label']} [{item['kind']}/{item['aspect']}] -> {item['expected_path']}"
        if results is not None and "render_msg" in item:
            line += "  | " + ("ok" if item.get("render_ok") else "skip") + ": " + item["render_msg"]
        print(line)
    print(f"[ok] {json_path}")
    if not args.run:
        print("（--run 实际派生 cutdown + reframe；需 ffmpeg）")


if __name__ == "__main__":
    main()
