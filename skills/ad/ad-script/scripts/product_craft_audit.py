#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产品镜**传统工艺声明**机检（advisory·出图前·编剧/分镜轴）。

传统 tabletop/产品广告摄影的硬工艺（见 ad-image/references/传统产品镜手法.md）：
光要打在产品**周围**而不是产品上（侧光造型、逆光穿瓶给"内发光"）、液体靠 300fps 升格浇注、
细节靠微距（气泡/水珠/拉丝）、hero 角度 45°/低角度。这些在实拍片场是灯光师和摄影指导的
肌肉记忆；在 AI 流水线里**只存在于 prompt 文字里**——storyboard 产品镜不写光位/质感/角度，
生图模型就给你均匀平光的电商白底图，"高级感"无从谈起。

本审计查每个产品/品牌镜是否声明了三轴工艺：
    ① 光位（侧光/逆光/轮廓光/穿瓶透光…）
    ② 质感手法（升格/微距/水珠/蒸汽/浇注/气泡/拉丝…）
    ③ 角度机位（45°/低角度/环绕/推近…）
三轴全缺 → warn；缺两轴 → info；endcard/logo 板豁免（静版要稳不要花）。
全 advisory：`summary.block` 恒 0（工艺好坏归导演，机检只保证"想过这件事"）。

用法：
    python3 product_craft_audit.py <作品根> [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

VERSION = 1
KIND = "ad_product_craft_audit"
REPORT_REL = os.path.join("生产数据", "ad_product_craft_audit.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")
CRAFT_DOC = "skills/ad/ad-image/references/传统产品镜手法.md"

PROD_KEY_RE = re.compile(r"\b(?:PROD|BRAND)_[A-Za-z0-9_]*\b")
PRODUCTISH_RE = re.compile(r"产品特写|产品展示|beauty.?shot|hero.?shot|包装|开箱|质感镜", re.IGNORECASE)
ENDCARD_RE = re.compile(r"片尾|尾板|end.?card|endcard|logo|CTA|slogan|价格板|二维码", re.IGNORECASE)

LIGHT_RE = re.compile(
    r"侧光|逆光|背光|轮廓光|顶光|底光|柔光|硬光|穿瓶|透光|内发光|光位|布光|辉光|"
    r"backlight|back.?lit|side.?light|rim.?light|halo|glow", re.IGNORECASE)
TEXTURE_RE = re.compile(
    r"慢动作|升格|微距|水珠|凝露|蒸汽|雾气|浇注|倾倒|飞溅|气泡|拉丝|流动|绵密|挂壁|"
    r"高速|冰爽|油亮|酥脆|热气|slow.?motion|macro|pour|splash|fizz|drip|condensation|\d{3,}fps",
    re.IGNORECASE)
ANGLE_RE = re.compile(
    r"45|低角度|仰拍|俯拍|平拍|环绕|推近|推轨|滑轨|旋转|特写推|"
    r"hero.?angle|low.?angle|top.?down|orbit|dolly|slider", re.IGNORECASE)

AXES: Tuple[Tuple[str, re.Pattern], ...] = (("光位", LIGHT_RE), ("质感手法", TEXTURE_RE), ("角度机位", ANGLE_RE))


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, shots: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    if shots:
        out["shots"] = list(shots)
    return out


def iter_shots(storyboard: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = storyboard.get("shots") or storyboard.get("clips") or storyboard.get("镜头") or []
    return [r for r in rows if isinstance(r, dict)]


def shot_id(shot: Mapping[str, Any], idx: int) -> str:
    return str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"镜头{idx + 1}")


def shot_blob(shot: Mapping[str, Any]) -> str:
    parts = []
    for key in ("shot", "frame", "画面", "主体动作", "description", "desc", "visual", "scene", "场景",
                "light", "lighting", "光位", "布光", "camera", "运镜", "机位", "角度", "shot_type",
                "景别", "shot_size", "section", "purpose", "craft", "手法"):
        val = shot.get(key)
        if val:
            parts.append(str(val))
    assets = shot.get("assets")
    if isinstance(assets, Mapping):
        parts.extend(str(k) for k in assets)
    elif isinstance(assets, (list, tuple)):
        parts.extend(str(v) for v in assets)
    return " ".join(parts)


def is_product_shot(shot: Mapping[str, Any]) -> bool:
    blob = shot_blob(shot)
    if ENDCARD_RE.search(blob):
        return False
    return bool(PROD_KEY_RE.search(blob) or PRODUCTISH_RE.search(blob))


def missing_axes(shot: Mapping[str, Any]) -> List[str]:
    blob = shot_blob(shot)
    return [name for name, pattern in AXES if not pattern.search(blob)]


def build(root: Path) -> Dict[str, Any]:
    root = Path(root)
    findings: List[Dict[str, Any]] = []
    try:
        storyboard = json.loads((root / STORYBOARD_REL).read_text(encoding="utf-8"))
    except Exception:
        storyboard = None
    available = isinstance(storyboard, dict)
    product_shots: List[Tuple[str, List[str]]] = []
    if not available:
        findings.append(finding("warn", "storyboard_missing",
                                f"缺 {STORYBOARD_REL}——没有分镜可审产品镜工艺（insufficient_data）。"))
    else:
        shots = iter_shots(storyboard)
        for idx, shot in enumerate(shots):
            if not is_product_shot(shot):
                continue
            product_shots.append((shot_id(shot, idx), missing_axes(shot)))
        bare = [sid for sid, miss in product_shots if len(miss) == 3]
        thin = [(sid, miss) for sid, miss in product_shots if len(miss) == 2]
        if bare:
            findings.append(finding(
                "warn", "product_craft_unspecified",
                f"{'、'.join(bare)} 是产品/品牌镜但光位/质感手法/角度机位**三轴全没写**——"
                "AI 只会给均匀平光的电商图；传统 tabletop 起步是：光打在产品周围（侧光造型/逆光穿瓶）、"
                f"液体用升格浇注、细节用微距，hero 角度 45°/低角度。工艺词汇表见 {CRAFT_DOC}",
                bare))
        for sid, miss in thin:
            findings.append(finding(
                "info", "product_craft_thin",
                f"{sid} 产品镜缺 {'/'.join(miss)} 声明——补上更能逼出质感（advisory）", [sid]))

    return {
        "schema_version": VERSION, "kind": KIND, "available": available,
        "project_root": str(root), "generated_at": now_iso(),
        "craft_reference": CRAFT_DOC,
        "inputs": {"product_shots": len(product_shots)},
        "summary": {"block": 0,
                    "warn": sum(1 for f in findings if f["severity"] == "warn"),
                    "info": sum(1 for f in findings if f["severity"] == "info")},
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report["summary"]
    lines = ["# 产品镜传统工艺声明机检", "",
             f"- 产品/品牌镜 {report['inputs'].get('product_shots')} 个 · warn {s['warn']} · info {s['info']}"
             "（advisory：工艺好坏归导演，本检只保证三轴想过）", ""]
    icon = {"warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 产品镜均已声明光位/质感/角度（效果好坏仍需人判）")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    for target, payload in ((path, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                            (path.with_suffix(".md"), render_markdown(report))):
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ .md·原子写）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="warn>0 时 exit 1")
    ns = ap.parse_args(argv)
    report = build(Path(ns.root))
    if ns.write:
        write_report(Path(ns.root), report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
