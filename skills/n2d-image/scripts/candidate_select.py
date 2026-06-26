#!/usr/bin/env python3
"""best-of-N 候选自动排序选片 + reroll 决策 —— 把人从「抽卡选片」里解放出来。

批量产线的最大人工触点之一是「一个可用镜要生 20-30 张、人工挑一张」（2026 行业实测）。本脚本对一个
镜头的 N 张候选图自动排序、选最优、并判「是否全废需 reroll」，让批量 runner 不必每镜等人挑版。

**2026 SOTA 铁律（arXiv 2604.25235「VLM Judges Can Rank but Cannot Score」）**：VLM 能可靠地**成对排序**
（A 和 B 哪张更好），但给的**绝对分不可校准**。故本脚本把 VLM 当 **ranker（成对比较）** 用、绝不当
绝对打分器；硬地板（崩脸/QC 硬伤）用**确定性**信号兜底，VLM 只在合格者之间挑更好的那张。

三层（自上而下，缺则降级，绝不臆造）：
  ① 硬地板·确定性：`qc_hard_fail`(崩脸/纯文生图/接缝断等 image_qc 硬伤) 直接淘汰，不进选片；
  ② 排序·VLM ranker（可选）：配 `N2D_VLM_COMPARE_CMD`（占位 {image_a}{image_b}{prompt}，stdout 回
     `{"winner":"a"|"b"|"tie"}`·厂商无关）→ 合格者单淘汰赛选冠军（N-1 次比较，确定性分做平局裁决）；
  ③ 排序·确定性兜底：无 VLM 时按 face 余弦(对锚)→QC warn 数→清晰度 排序。
reroll_needed：全部候选都硬伤（无合格者），或最优者 face 余弦仍 < identity_floor（最好的也崩脸）。

报告型：写 `生产数据/candidate_selection_第N集.json`；`--apply` 才把选中图拷到落档路径（不可逆=显式）。
纯排序/选片是纯函数，有 pytest 覆盖（test_candidate_select.py）。

用法：python3 candidate_select.py <作品根> 第N集 [--clip 镜头X] [--apply] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

KIND = "n2d_candidate_selection"
VERSION = 1

# 确定性兜底排序权重（face 余弦是身份主信号 → 最高权重；清晰度兜底）。
DET_WEIGHTS = {"face_consistency": 1.0, "composition": 0.3, "hook_strength": 0.3,
               "style_match": 0.3, "asset_consistency": 0.4, "sharpness": 0.2}
# 最优者 face 余弦仍低于此 → 判「最好的也崩脸」→ reroll（与 face_consistency 自标定地板同量级的保守线）。
IDENTITY_FLOOR = float(os.environ.get("N2D_CANDIDATE_IDENTITY_FLOOR", "0.45") or "0.45")


# ── 纯函数：排序 / 单淘汰冠军 / 选片 ─────────────────────────────────────────────

def deterministic_score(cand: Dict[str, Any]) -> float:
    """候选确定性总分（信号缺失记 0，绝不臆造）。纯函数。"""
    s = 0.0
    for key, w in DET_WEIGHTS.items():
        v = cand.get(key)
        if isinstance(v, (int, float)):
            s += w * float(v)
    return round(s, 4)


def deterministic_rank(cands: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """确定性排序：硬伤沉底；合格者按 face 余弦→总分→清晰度 降序。纯函数。"""
    def key(c: Dict[str, Any]):
        hard = bool(c.get("qc_hard_fail"))
        face = c.get("face_consistency")
        face = float(face) if isinstance(face, (int, float)) else -1.0
        return (not hard, face, deterministic_score(c),
                float(c.get("sharpness") or 0))
    return sorted(cands, key=key, reverse=True)


def vlm_champion(survivors: Sequence[Dict[str, Any]],
                 compare: Callable[[Dict[str, Any], Dict[str, Any]], str]) -> Dict[str, Any]:
    """合格候选里用成对比较（VLM ranker）单淘汰选冠军，N-1 次比较。平局→确定性分高者胜。纯函数。

    compare(a, b) → 'a' | 'b' | 'tie'。VLM 当 ranker（成对）用，不当绝对打分器。"""
    champ = survivors[0]
    for challenger in survivors[1:]:
        try:
            verdict = compare(champ, challenger)
        except Exception:
            verdict = "tie"
        if verdict == "b":
            champ = challenger
        elif verdict == "tie":
            if deterministic_score(challenger) > deterministic_score(champ):
                champ = challenger
    return champ


def select_best(cands: Sequence[Dict[str, Any]], *,
                vlm_compare: Optional[Callable[[Dict[str, Any], Dict[str, Any]], str]] = None,
                identity_floor: float = IDENTITY_FLOOR) -> Dict[str, Any]:
    """对一个镜头的候选排序选片 + reroll 决策。纯函数·report-only（不落盘、不拷文件）。

    返回 {ranked, picked, reroll_needed, reason, method, survivors, disqualified}。"""
    cands = [dict(c) for c in cands]
    if not cands:
        return {"ranked": [], "picked": None, "reroll_needed": True,
                "reason": "无候选图", "method": "none", "survivors": 0, "disqualified": 0}
    ranked = deterministic_rank(cands)
    survivors = [c for c in ranked if not c.get("qc_hard_fail")]
    disq = len(cands) - len(survivors)
    if not survivors:
        return {"ranked": ranked, "picked": None, "reroll_needed": True,
                "reason": f"全部 {len(cands)} 张候选都有 QC 硬伤（崩脸/纯文生图/接缝断）→ 整镜 reroll",
                "method": "deterministic", "survivors": 0, "disqualified": disq}
    if vlm_compare is not None and len(survivors) > 1:
        picked = vlm_champion(survivors, vlm_compare)
        method = "vlm_ranker"
    else:
        picked = survivors[0]
        method = "deterministic"
    face = picked.get("face_consistency")
    reroll = isinstance(face, (int, float)) and float(face) < identity_floor
    reason = ("选出最优候选" if not reroll
              else f"最优候选 face 余弦 {float(face):.3f} < 地板 {identity_floor:.2f}（最好的也崩脸）→ reroll")
    return {"ranked": ranked, "picked": picked, "reroll_needed": bool(reroll),
            "reason": reason, "method": method, "survivors": len(survivors), "disqualified": disq}


# ── VLM ranker 适配（厂商无关·N2D_VLM_COMPARE_CMD）────────────────────────────────

COMPARE_PROMPT = ("你是漫剧出图选片助手。比较 A、B 两张同一镜头候选图，哪张在【角色身份不崩脸、贴合分镜"
                  "意图、构图与画质】上整体更好？只回 JSON：{\"winner\":\"a\"} 或 {\"winner\":\"b\"} 或 "
                  "{\"winner\":\"tie\"}。不要解释。")


def make_vlm_compare() -> Optional[Callable[[Dict[str, Any], Dict[str, Any]], str]]:
    """从 `N2D_VLM_COMPARE_CMD` 构造成对比较器；未配置→None（降级确定性）。

    模板占位 {image_a} {image_b} {prompt}（路径/prompt 经 shell-quote）；stdout 回 {"winner":"a"|"b"|"tie"}。
    例：export N2D_VLM_COMPARE_CMD='python3 ~/bin/vlm_pair.py --a {image_a} --b {image_b} --q {prompt}'"""
    tmpl = os.environ.get("N2D_VLM_COMPARE_CMD", "").strip()
    if not tmpl or "{image_a}" not in tmpl or "{image_b}" not in tmpl:
        return None

    def compare(a: Dict[str, Any], b: Dict[str, Any]) -> str:
        pa, pb = str(a.get("path") or ""), str(b.get("path") or "")
        if not (pa and pb and os.path.exists(pa) and os.path.exists(pb)):
            return "tie"
        cmd = tmpl.replace("{image_a}", shlex.quote(pa)).replace("{image_b}", shlex.quote(pb))
        if "{prompt}" in cmd:
            cmd = cmd.replace("{prompt}", shlex.quote(COMPARE_PROMPT))
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
            data = json.loads(res.stdout or "{}")
            w = str(data.get("winner") or "").strip().lower()
            return w if w in {"a", "b", "tie"} else "tie"
        except Exception:
            return "tie"

    return compare


# ── 信号采集（确定性·优雅降级）──────────────────────────────────────────────────

def _sharpness(png: str) -> Optional[float]:
    """归一化清晰度代理（梯度能量·Pillow 纯实现，无 cv2 依赖）；失败→None。"""
    try:
        from PIL import Image
        im = Image.open(png).convert("L")
        im.thumbnail((256, 256))
        px = list(im.getdata())
        w = im.width
        if w < 2 or len(px) < w * 2:
            return None
        total, n = 0, 0
        for y in range(im.height - 1):
            row = y * w
            for x in range(w - 1):
                i = row + x
                gx = px[i] - px[i + 1]
                gy = px[i] - px[i + w]
                total += gx * gx + gy * gy
                n += 1
        return round((total / n) / 6000.0, 4) if n else None  # 经验归一到 ~0-1
    except Exception:
        return None


def gather_candidate(png: str, root: str) -> Dict[str, Any]:
    """采一张候选的确定性信号：旁车 JSON（face_consistency/composition/qc_hard_fail…·沿用 候选 sidecar 约定）
    + 自动清晰度。绝不臆造缺失信号。"""
    cand: Dict[str, Any] = {"path": png, "candidate": Path(png).stem,
                            "rel": os.path.relpath(png, root)}
    sidecar = os.path.splitext(png)[0] + ".json"
    if os.path.isfile(sidecar):
        try:
            data = json.loads(Path(sidecar).read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k in ("face_consistency", "composition", "hook_strength", "style_match",
                          "asset_consistency", "qc_hard_fail"):
                    if k in data:
                        cand[k] = data[k]
        except Exception:
            pass
    sh = _sharpness(png)
    if sh is not None:
        cand["sharpness"] = sh
    return cand


def candidate_dir(root: str, ep: str, clip: str) -> str:
    return os.path.join(root, "出图", ep, "候选", clip)


def list_clips(root: str, ep: str) -> List[str]:
    base = os.path.join(root, "出图", ep, "候选")
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))


def select_clip(root: str, ep: str, clip: str,
                vlm_compare: Optional[Callable] = None) -> Dict[str, Any]:
    cdir = candidate_dir(root, ep, clip)
    pngs = sorted(glob.glob(os.path.join(cdir, "*.png")))
    cands = [gather_candidate(p, root) for p in pngs]
    res = select_best(cands, vlm_compare=vlm_compare)
    res["clip"] = clip
    res["candidate_count"] = len(cands)
    return res


def apply_pick(root: str, ep: str, clip: str, picked: Mapping[str, Any]) -> Optional[str]:
    """把选中候选拷到落档路径 出图/<ep>/图片/<clip>.png（不可逆=只在 --apply 调用）。"""
    src = str(picked.get("path") or "")
    if not src or not os.path.isfile(src):
        return None
    dst_dir = os.path.join(root, "出图", ep, "图片")
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, f"{clip}.png")
    shutil.copy2(src, dst)
    return os.path.relpath(dst, root)


def build_report(root: str, ep: str, only_clip: Optional[str] = None) -> Dict[str, Any]:
    vlm = make_vlm_compare()
    clips = [only_clip] if only_clip else list_clips(root, ep)
    rows = [select_clip(root, ep, c, vlm_compare=vlm) for c in clips if c]
    reroll = [r["clip"] for r in rows if r.get("reroll_needed")]
    return {
        "kind": KIND, "version": VERSION, "episode": ep,
        "vlm_ranker": vlm is not None,
        "clips_selected": len(rows),
        "reroll_clips": reroll,
        "rows": rows,
        "notes": ([] if vlm is not None else
                  ["未配置 N2D_VLM_COMPARE_CMD：用确定性排序（face 余弦→QC→清晰度）选片；"
                   "配置厂商无关成对比较器可启用 VLM ranker（成对·非绝对打分）。"]),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--clip", help="只选某一镜（默认全集所有候选镜）")
    ap.add_argument("--apply", action="store_true", help="把选中候选拷到落档路径（不可逆）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    report = build_report(root, ns.episode, ns.clip)
    applied = []
    if ns.apply:
        for r in report["rows"]:
            if r.get("picked") and not r.get("reroll_needed"):
                dst = apply_pick(root, ns.episode, r["clip"], r["picked"])
                if dst:
                    applied.append({"clip": r["clip"], "dst": dst})
        report["applied"] = applied
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"candidate_selection_{ns.episode}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"候选选片 {ns.episode}：{report['clips_selected']} 镜，VLM ranker={report['vlm_ranker']}，"
              f"需 reroll {len(report['reroll_clips'])} 镜")
        for r in report["rows"]:
            pick = (r.get("picked") or {}).get("candidate") if r.get("picked") else "—"
            flag = "🔁REROLL" if r.get("reroll_needed") else f"✅{pick}"
            print(f"  · {r['clip']}（{r['candidate_count']}选·{r['method']}）：{flag}　{r['reason']}")
        if ns.apply:
            print(f"  已落档 {len(applied)} 镜")
    return 0  # report-only，永不非零退出


if __name__ == "__main__":
    raise SystemExit(main())
