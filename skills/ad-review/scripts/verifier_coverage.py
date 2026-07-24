#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告线·一致性现实覆盖账本（verifier_coverage）—— 机检空转/休眠 fail-closed。

为什么存在（真空档）：
  ad 线的 gate 只问「报告在不在、summary.block 是多少」——它回答不了一个更阴险的问题：
  **报告在、干净，但它其实什么都没检**。典型空转形态：
    · registry 登记了 PROD_ 产品资产，product_qc.json 也落了档，但报告里 product_shots=0 /
      全部 finding 都是 degraded=no_image——一张产品图都没真正开检，报告却"干净"。
    · advisory 审计 available=false（缺料降级）却被当作"跑过了"。
    · 报告早于其输入产物——干净但过期的证据不是证据（与 gate.report_freshness 同哲学）。
  规矩：**「适用 × 休眠 → 交付前阻断」**（fail-closed）。
  每个核验器算一行 `applies × ran × fresh × effective`，适用却休眠/空转/过期的硬核验器 → block。

严重度边界（必读）：
  本报表**可以产 block**。它不是创意启发式——`score_findings` 立的「创意/启发式只提示复核，
  只有广告法与确定性闸门能 BLOCK」规矩管的是**好不好看**的判断；本账本管的是**机检有没有真跑**，
  与 `report_freshness_findings` / `registry_snapshot_findings` 同族（确定性闸门），
  遵循的是「适用 × 休眠 → 交付前阻断」。
  分档纪律：
    · 硬核验器（product_qc / asset_consistency / asset_drift_report / video_qc /
      contract_inheritance）：适用而未跑(dormant) / 过期(stale) / 空转(empty_run) → **block**。
    · final_media_consistency：喂人工签收的对照表，缺席 → **warn**（签收闸自己会挡）。
    · advisory 创意轴：available=false 或 0 镜空转而输入齐备 → **warn**（空转要说出来，
      但 advisory 核验器自己永不 block，此处也不替它们升档）。
    · applies=false → not_applicable 行如实入表，不产 finding（没有对象不算休眠）。

唯一逃生口（单一咽喉）：
  `合规/degraded_qc_waiver.json`：{"approved": true, "scope": ["product_qc", ...] 或 ["*"],
  "reason": "...", "signed_by": "..."}。有效豁免把命中核验器的 block 降为 warn 并留
  `waiver_active` 痕；缺 reason/signed_by 的豁免**无效**——忽略并 warn `waiver_invalid`。

诚实边界：
  - 本账本**零像素、纯标准库**：只读已有侧车与文件 mtime，不重算任何一致性距离；
    它只回答"该跑的检有没有真跑、检的时候有没有对象"，不回答"检得对不对"。
  - product_qc 落档 JSON 没有显式 examined 计数；effective 取反证法：报告自述
    product_shots=0 / pending_product_images>0 / 全部 finding 均 no_image → 视为没真检。
    findings 为空且无上述反证 → 视为有效（无法进一步核实张数，如实注明）。
  - asset_consistency 的 effective 只到「summary 可解析」——其 schema 无逐资产覆盖计数，
    不臆造更细的判断。

用法：
    python3 verifier_coverage.py <作品根> [--write] [--json] [--strict]
    # --write 落 生产数据/ad_verifier_coverage.json + .md（原子写：同盘 temp + os.replace）
    # --strict：有 block 时退出码 1（默认 0；gate 读侧车，不依赖退出码）

测试（从本目录跑）：
    cd skills/ad-review/scripts && python3 -m pytest test_verifier_coverage.py
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
KIND = "ad_verifier_coverage"
REPORT_REL = os.path.join("生产数据", "ad_verifier_coverage.json")
WAIVER_REL = os.path.join("合规", "degraded_qc_waiver.json")

# 与 asset_drift_report.ASSET_RE 同构（刻意重复常量而非 import，保持本模块可独立测试）。
ASSET_RE = re.compile(r"\b(?:CHAR|LOC|PROP|BRAND|PROD)_[A-Za-z0-9_]+\b")
CRITICAL_RE = re.compile(r"\b(?:PROD|BRAND)_[A-Za-z0-9_]+\b")
# 与 product_qc.product_shots 的兜底语义同构（子集即可：本账本只判 applies，不判逐镜）。
_PRODUCT_MARKERS = ("产品", "包装", "logo", "特写", "endcard", "end-card", "cta")

VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")

HARD = "hard"          # 适用而休眠/空转/过期 → block
SIGNOFF = "signoff"    # 喂人工签收 → warn
ADVISORY = "advisory"  # 创意轴 → 只 warn 空转，不管缺席（gate 已有「建议先跑」info）

STATUS_OK = "ok"
STATUS_DORMANT = "dormant"          # 适用但侧车不存在/不可解析
STATUS_STALE = "stale"              # 侧车早于其输入
STATUS_EMPTY_RUN = "empty_run"      # 跑了但没有真实对象（机检空转）
STATUS_NA = "not_applicable"

# 每个核验器：铁律档位、侧车相对路径、新鲜度输入（相对路径，dir 取递归最新）。
# 输入清单刻意保持最小且与 ad-craft/gate.py 的 freshness 清单同源。
HARD_VERIFIERS: List[Dict[str, Any]] = [
    {"name": "product_qc", "tier": HARD,
     "sidecar": os.path.join("出图", "分镜", "product_qc.json"),
     "inputs": [os.path.join("脚本", "storyboard.json"),
                os.path.join("出图", "分镜", "prompt"),
                os.path.join("出图", "分镜", "图片"),
                os.path.join("出图", "共享", "asset_registry.json")]},
    {"name": "asset_consistency", "tier": HARD,
     "sidecar": os.path.join("生产数据", "asset_consistency.json"),
     "inputs": [os.path.join("脚本", "storyboard.json"),
                os.path.join("出图", "分镜", "图片")]},
    {"name": "asset_drift_report", "tier": HARD,
     "sidecar": os.path.join("生产数据", "asset_drift_report.json"),
     "inputs": [os.path.join("脚本", "storyboard.json"),
                os.path.join("出图", "分镜", "product_qc.json"),
                os.path.join("生产数据", "asset_consistency.json")]},
    {"name": "video_qc", "tier": HARD,
     "sidecar": os.path.join("出视频", "分镜", "video_qc.json"),
     "inputs": [os.path.join("出视频", "分镜", "视频"),
                os.path.join("出视频", "分镜", "prompt"),
                os.path.join("出视频", "分镜", "contract_inheritance.json")]},
    {"name": "contract_inheritance", "tier": HARD,
     "sidecar": os.path.join("出视频", "分镜", "contract_inheritance.json"),
     "inputs": [os.path.join("脚本", "storyboard.json"),
                os.path.join("出视频", "分镜", "prompt")]},
    {"name": "final_media_consistency", "tier": SIGNOFF,
     "sidecar": os.path.join("生产数据", "final_media_consistency.json"),
     "inputs": [os.path.join("合成",)]},
]

# advisory 创意轴：与 ad-craft/gate.creative_axis_findings 的侧车清单同源
# （含本轮新增 beat_structure / see_say）。applies = 全部输入存在。
ADVISORY_VERIFIERS: List[Dict[str, Any]] = [
    {"name": "concept_pack", "tier": ADVISORY,
     "sidecar": os.path.join("生产数据", "ad_concept_pack_check.json"),
     "inputs": [os.path.join("创意", "concept.json"), os.path.join("需求", "brief.json")]},
    {"name": "idea_payoff", "tier": ADVISORY,
     "sidecar": os.path.join("生产数据", "ad_idea_payoff_audit.json"),
     "inputs": [os.path.join("创意", "concept.json"), os.path.join("脚本", "storyboard.json")]},
    {"name": "copy_quality", "tier": ADVISORY,
     "sidecar": os.path.join("生产数据", "ad_copy_quality_audit.json"),
     "inputs": [os.path.join("脚本", "voiceover.txt"), os.path.join("脚本", "storyboard.json")]},
    {"name": "shot_variety", "tier": ADVISORY,
     "sidecar": os.path.join("生产数据", "ad_shot_variety_audit.json"),
     "inputs": [os.path.join("脚本", "storyboard.json")]},
    {"name": "product_craft", "tier": ADVISORY,
     "sidecar": os.path.join("生产数据", "ad_product_craft_audit.json"),
     "inputs": [os.path.join("脚本", "storyboard.json")]},
    {"name": "performance_cue", "tier": ADVISORY,
     "sidecar": os.path.join("生产数据", "ad_performance_cue_audit.json"),
     "inputs": [os.path.join("脚本", "storyboard.json")]},
    {"name": "beat_structure", "tier": ADVISORY,
     "sidecar": os.path.join("生产数据", "ad_beat_structure_audit.json"),
     "inputs": [os.path.join("脚本", "storyboard.json")]},
    {"name": "see_say", "tier": ADVISORY,
     "sidecar": os.path.join("生产数据", "ad_see_say_audit.json"),
     "inputs": [os.path.join("脚本", "storyboard.json"), os.path.join("脚本", "voiceover.txt")]},
]


# ── 纯函数（无 IO·可测） ─────────────────────────────────────────────────────

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, verifier: str = "",
            detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """findings 条目。权威键 `msg`（ad gate / consistency_findings 消费口径）。"""
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg, "message": msg}
    if verifier:
        out["verifier"] = verifier
    if detail:
        out["detail"] = detail
    return out


def parse_waiver(payload: Any) -> Tuple[Optional[set], Optional[str]]:
    """degraded_qc_waiver.json → (生效 scope 集合, 无效原因)。

    有效条件：approved=true 且 reason/signed_by 非空。scope 缺省视为无效（必须显式点名，
    哪怕是 ["*"]——逃生口不允许含糊）。返回 (None, reason) 表示无效或不存在。
    """
    if not isinstance(payload, Mapping):
        return None, None  # 不存在：不报 invalid
    if payload.get("approved") is not True:
        return None, "approved != true"
    reason = str(payload.get("reason") or "").strip()
    signed = str(payload.get("signed_by") or "").strip()
    scope_raw = payload.get("scope")
    if not reason or not signed:
        return None, "缺 reason/signed_by——豁免必须留人、留因"
    if isinstance(scope_raw, str):
        scope_raw = [scope_raw]
    if not isinstance(scope_raw, list) or not scope_raw:
        return None, "缺 scope——豁免必须显式点名核验器（可用 [\"*\"]）"
    return {str(s).strip() for s in scope_raw if str(s).strip()}, None


def waived(name: str, scope: Optional[set]) -> bool:
    return bool(scope) and ("*" in scope or name in scope)


def product_qc_effective(report: Mapping[str, Any]) -> Tuple[bool, str]:
    """product_qc 落档没有显式 examined 计数——用报告自述的反证判空转。纯函数·可测。"""
    env = report.get("qc_environment") if isinstance(report.get("qc_environment"), Mapping) else {}
    try:
        pending = int(env.get("pending_product_images") or 0)
    except (TypeError, ValueError):
        pending = 0
    if pending > 0:
        return False, f"pending_product_images={pending}：产品镜图未落档/未读到，等于没检"
    findings = [f for f in report.get("findings") or [] if isinstance(f, Mapping)]
    for f in findings:
        detail = f.get("detail") if isinstance(f.get("detail"), Mapping) else {}
        if detail.get("product_shots") == 0:
            return False, "报告自述 product_shots=0：storyboard 无产品镜绑定，一张产品图都没检"
    degraded = [f for f in findings
                if isinstance(f.get("detail"), Mapping) and f["detail"].get("degraded") == "no_image"]
    if findings and len(degraded) == len(findings):
        return False, "全部 finding 均为 degraded=no_image：像素检一张都没真跑"
    return True, ""


def video_qc_effective(report: Mapping[str, Any]) -> Tuple[bool, str]:
    for f in report.get("findings") or []:
        if not isinstance(f, Mapping):
            continue
        if (f.get("check") or f.get("code")) == "storyboard" and f.get("severity") == "block":
            return False, "video_qc 自述缺 storyboard clips/shots——没有验收对象"
    return True, ""


def drift_report_effective(report: Mapping[str, Any]) -> Tuple[bool, str]:
    if report.get("available") is False:
        return False, "asset_drift_report available=false（无资产全集可追踪）"
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    try:
        tracked = int(summary.get("assets_tracked") or 0)
    except (TypeError, ValueError):
        tracked = 0
    if tracked < 1:
        return False, "asset_drift_report 追踪 0 个资产——跨镜时间线是空的"
    return True, ""


def p0_noevidence_findings(report: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """drift report 里 P0（PROD_/BRAND_）资产**全镜** noevidence → warn。noevidence ≠ ok。"""
    out: List[Dict[str, Any]] = []
    for row in report.get("assets") or []:
        if not isinstance(row, Mapping) or not row.get("critical"):
            continue
        appeared = list(row.get("appeared_shots") or [])
        noev = list(row.get("noevidence_shots") or [])
        if appeared and len(noev) == len(appeared):
            out.append(finding(
                "warn", "p0_asset_no_evidence",
                f"{row.get('asset_id')}：产品/品牌资产出现的 {len(appeared)} 镜**全部**没有任何机检证据"
                f"（{'、'.join(noev)}）——noevidence ≠ ok，需补跑 product_qc/asset_consistency "
                "或人工并排签收后再交付。",
                "asset_drift_report",
                {"asset_id": row.get("asset_id"), "noevidence_shots": noev}))
    return out


def advisory_degraded_reason(report: Mapping[str, Any],
                             storyboard_shots: int) -> Optional[str]:
    """advisory 侧车空转判定：available=false，或报告自述 0 镜而 storyboard 有镜。"""
    if report.get("available") is False:
        return "available=false（缺料降级）——它没产出有效结论，不能当作『审过了』"
    inputs = report.get("inputs") if isinstance(report.get("inputs"), Mapping) else {}
    if storyboard_shots > 0 and inputs.get("shots") == 0:
        return f"报告自述审了 0 镜，而 storyboard 有 {storyboard_shots} 镜——机检空转"
    return None


# ── IO 助手 ───────────────────────────────────────────────────────────────────

def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def newest_mtime(paths: Sequence[Path]) -> float:
    newest = 0.0
    for path in paths:
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    newest = max(newest, child.stat().st_mtime)
        elif path.is_file():
            newest = max(newest, path.stat().st_mtime)
    return newest


def has_files(folder: Path, suffixes: Tuple[str, ...]) -> bool:
    if not folder.is_dir():
        return False
    return any(child.suffix.lower() in suffixes for child in folder.iterdir() if child.is_file())


def registry_ids(root: Path) -> set:
    for rel in ("设定库/asset_registry.json", "出图/共享/asset_registry.json"):
        data = load_json(root / rel)
        if data is not None:
            try:
                blob = json.dumps(data, ensure_ascii=False, default=str)
            except Exception:
                blob = ""
            return set(ASSET_RE.findall(blob))
    return set()


def storyboard_info(root: Path) -> Tuple[int, bool]:
    """(镜数, 是否含产品镜)。产品镜判定与 product_qc.product_shots 同构的简化子集。"""
    sb = load_json(root / "脚本" / "storyboard.json", {}) or {}
    shots = sb.get("shots") or sb.get("clips") or []
    if not isinstance(shots, list):
        return 0, False
    has_product = False
    count = 0
    for shot in shots:
        if not isinstance(shot, Mapping):
            continue
        count += 1
        assets = shot.get("assets")
        if isinstance(assets, Mapping):
            if any(CRITICAL_RE.fullmatch(str(k)) and bool(v) for k, v in assets.items()):
                has_product = True
                continue
        elif isinstance(assets, (list, tuple)):
            if any(CRITICAL_RE.fullmatch(str(a)) for a in assets):
                has_product = True
                continue
        text = " ".join(str(shot.get(k) or "") for k in
                        ("scene", "shot", "frame", "prompt", "desc", "description")).lower()
        if any(marker in text for marker in _PRODUCT_MARKERS):
            has_product = True
    return count, has_product


# ── 覆盖账本 ─────────────────────────────────────────────────────────────────

def _applies(root: Path, name: str, reg: set, sb_shots: int, sb_has_product: bool) -> Tuple[bool, str]:
    """每个核验器的 applies 判定（项目登记了对象才谈得上「该跑」）。"""
    if name == "product_qc":
        if any(CRITICAL_RE.fullmatch(a) for a in reg):
            return True, "registry 登记了 PROD_/BRAND_ 资产"
        if sb_has_product:
            return True, "storyboard 含产品镜"
        return False, "无产品/品牌资产登记，也无产品镜"
    if name in ("asset_consistency", "asset_drift_report"):
        if reg and has_files(root / "出图" / "分镜" / "图片", IMAGE_SUFFIXES):
            return True, "registry 有资产且已有落图"
        return False, "无登记资产或尚未落图"
    if name == "video_qc":
        if has_files(root / "出视频" / "分镜" / "视频", VIDEO_SUFFIXES):
            return True, "已有出视频 clip"
        return False, "尚无出视频 clip"
    if name == "contract_inheritance":
        prompt_dir = root / "出视频" / "分镜" / "prompt"
        if prompt_dir.is_dir() and any(p.is_file() for p in prompt_dir.iterdir()):
            return True, "已有出视频 prompt"
        return False, "尚无出视频 prompt"
    if name == "final_media_consistency":
        if (root / "合成" / "成片_主片.mp4").is_file():
            return True, "主片已合成"
        return False, "尚未合成主片"
    return False, "unknown verifier"


def _effective(name: str, report: Mapping[str, Any]) -> Tuple[bool, str]:
    if name == "product_qc":
        return product_qc_effective(report)
    if name == "video_qc":
        return video_qc_effective(report)
    if name == "asset_drift_report":
        return drift_report_effective(report)
    # asset_consistency / contract_inheritance / final_media_consistency：
    # schema 无更细的覆盖计数，effective 只到 summary 可解析——不臆造。
    return isinstance(report.get("summary"), Mapping), "缺 summary（格式异常）"


def build(root: Path) -> Dict[str, Any]:
    """接入契约（供 ad-craft/gate.py 读）：

        {"schema_version":1,"kind":"ad_verifier_coverage","available":true,
         "summary":{"block","warn","info",...},"coverage":[行...],"findings":[...]}

    「适用 × 休眠 → 交付前阻断」：硬核验器 dormant/stale/empty_run 产 block；
    有效豁免（合规/degraded_qc_waiver.json）降为 warn 并留痕。
    """
    root = Path(root).resolve()
    reg = registry_ids(root)
    sb_shots, sb_has_product = storyboard_info(root)
    waiver_payload = load_json(root / WAIVER_REL)
    waiver_scope, waiver_invalid = parse_waiver(waiver_payload)

    rows: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    if waiver_invalid:
        findings.append(finding(
            "warn", "waiver_invalid",
            f"合规/degraded_qc_waiver.json 无效（{waiver_invalid}）——已忽略，fail-closed 照常执行。",
            detail={"path": str(root / WAIVER_REL)}))

    for spec in HARD_VERIFIERS:
        name, tier = spec["name"], spec["tier"]
        sidecar = root / spec["sidecar"]
        applies, applies_reason = _applies(root, name, reg, sb_shots, sb_has_product)
        row: Dict[str, Any] = {"verifier": name, "tier": tier, "applies": applies,
                               "applies_reason": applies_reason,
                               "sidecar": spec["sidecar"], "ran": False, "fresh": None,
                               "effective": None, "status": STATUS_NA}
        if not applies:
            rows.append(row)
            continue
        block_sev = "block" if tier == HARD else "warn"
        report = load_json(sidecar)
        if not isinstance(report, Mapping):
            row.update(status=STATUS_DORMANT)
            sev, note = _apply_waiver(block_sev, name, waiver_scope)
            findings.append(finding(
                sev, "verifier_dormant",
                f"{name} 适用（{applies_reason}）但侧车 {spec['sidecar']} 不存在/不可解析——"
                "该跑的机检没跑，「没数据」不等于「没问题」。" + note,
                name, {"sidecar": spec["sidecar"], "waived": bool(note)}))
            rows.append(row)
            continue
        row["ran"] = True
        inputs = [root / rel for rel in spec["inputs"]]
        newest = newest_mtime([p for p in inputs if p.exists()])
        fresh = not (newest and sidecar.stat().st_mtime + 1e-6 < newest)
        row["fresh"] = fresh
        effective, why = _effective(name, report)
        row["effective"] = effective
        if not fresh:
            row.update(status=STATUS_STALE)
            sev, note = _apply_waiver(block_sev, name, waiver_scope)
            findings.append(finding(
                sev, "verifier_stale",
                f"{name} 侧车 {spec['sidecar']} 早于其输入产物——干净但过期的报告不能证明"
                "新产物通过，必须重跑。" + note,
                name, {"sidecar": spec["sidecar"], "waived": bool(note)}))
        elif not effective:
            row.update(status=STATUS_EMPTY_RUN)
            sev, note = _apply_waiver(block_sev, name, waiver_scope)
            findings.append(finding(
                sev, "verifier_empty_run",
                f"{name} 机检空转：报告存在且看似干净，但 {why}；而项目侧 {applies_reason}——"
                "跑了数据却没真检，fail-closed（适用 × 休眠 → 交付前阻断）。" + note,
                name, {"sidecar": spec["sidecar"], "reason": why, "waived": bool(note)}))
        else:
            row.update(status=STATUS_OK)
        if name == "asset_drift_report" and row["status"] == STATUS_OK:
            findings.extend(p0_noevidence_findings(report))
        rows.append(row)

    for spec in ADVISORY_VERIFIERS:
        name = spec["name"]
        sidecar = root / spec["sidecar"]
        applies = all((root / rel).exists() for rel in spec["inputs"])
        row = {"verifier": name, "tier": ADVISORY, "applies": applies,
               "applies_reason": "输入齐备" if applies else "输入未齐",
               "sidecar": spec["sidecar"], "ran": False, "fresh": None,
               "effective": None, "status": STATUS_NA}
        if not applies:
            rows.append(row)
            continue
        report = load_json(sidecar)
        if not isinstance(report, Mapping):
            # 缺席的 advisory 审计由 gate 的「建议先跑」info 提示，这里只如实记行，不重复报。
            row.update(status=STATUS_DORMANT)
            rows.append(row)
            continue
        row["ran"] = True
        reason = advisory_degraded_reason(report, sb_shots)
        if reason:
            row.update(status=STATUS_EMPTY_RUN, effective=False)
            findings.append(finding(
                "warn", "advisory_degraded",
                f"{name} 空转告警：{reason}。advisory 审计不阻断，但空转必须说出来"
                "（对齐『机检空转告警』纪律）。",
                name, {"sidecar": spec["sidecar"]}))
        else:
            row.update(status=STATUS_OK, effective=True)
        rows.append(row)

    if waiver_scope:
        hit = sorted({f["verifier"] for f in findings
                      if f.get("detail", {}).get("waived")})
        if hit:
            findings.append(finding(
                "info", "waiver_active",
                f"degraded_qc_waiver 生效（scope={sorted(waiver_scope)}），已把 {'、'.join(hit)} "
                f"的 block 降为 warn——欠账在案：{str((waiver_payload or {}).get('reason'))[:80]}",
                detail={"signed_by": (waiver_payload or {}).get("signed_by"),
                        "scope": sorted(waiver_scope)}))

    summary = {
        "block": sum(1 for f in findings if f["severity"] == "block"),
        "warn": sum(1 for f in findings if f["severity"] == "warn"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
        "verifiers_total": len(rows),
        "applicable": sum(1 for r in rows if r["applies"]),
        "effective": sum(1 for r in rows if r["status"] == STATUS_OK),
        "dormant_or_empty": sum(1 for r in rows
                                if r["status"] in (STATUS_DORMANT, STATUS_EMPTY_RUN, STATUS_STALE)),
    }
    return {
        "schema_version": VERSION,
        "kind": KIND,
        "generated_at": now_iso(),
        "available": True,
        "project_root": str(root),
        "waiver": {"present": waiver_payload is not None,
                   "valid": waiver_scope is not None,
                   "scope": sorted(waiver_scope) if waiver_scope else []},
        "summary": summary,
        "coverage": rows,
        "findings": findings,
    }


def _apply_waiver(severity: str, name: str, scope: Optional[set]) -> Tuple[str, str]:
    """block → warn 当且仅当有效豁免点名了该核验器。返回 (severity, 追加说明)。"""
    if severity == "block" and waived(name, scope):
        return "warn", "（degraded_qc_waiver 生效：降 block→warn，欠账留痕 waiver_active）"
    return severity, ""


# ── 输出 ─────────────────────────────────────────────────────────────────────

def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = ["# 广告机检覆盖账本（verifier_coverage）", "",
             f"- generated_at: {report.get('generated_at')}",
             f"- 核验器 {s.get('verifiers_total')} · 适用 {s.get('applicable')} · "
             f"有效 {s.get('effective')} · 休眠/空转/过期 {s.get('dormant_or_empty')}",
             f"- findings — block: {s.get('block')}  warn: {s.get('warn')}  info: {s.get('info')}",
             "",
             "> **适用 × 休眠 → 交付前阻断**（fail-closed）：报告在但没真检 = 没检。",
             "> 唯一逃生口：合规/degraded_qc_waiver.json（须 approved+scope+reason+signed_by）。", ""]
    icon = {STATUS_OK: "🟢", STATUS_DORMANT: "🔴", STATUS_STALE: "🟠",
            STATUS_EMPTY_RUN: "🔴", STATUS_NA: "⚪"}
    lines.append("| 核验器 | 档位 | 适用 | 跑过 | 新鲜 | 有效 | 状态 |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in report.get("coverage") or []:
        def yn(v):
            return "—" if v is None else ("✓" if v else "✗")
        lines.append(f"| {row['verifier']} | {row['tier']} | {yn(row['applies'])} | "
                     f"{yn(row['ran'])} | {yn(row['fresh'])} | {yn(row['effective'])} | "
                     f"{icon.get(row['status'], '·')} {row['status']} |")
    lines.append("")
    for item in report.get("findings") or []:
        mark = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}.get(item["severity"], "·")
        lines.append(f"- {mark} `{item['code']}` {item['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 所有适用核验器都真跑过、够新鲜、有真实对象")
    return "\n".join(lines) + "\n"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")  # 同盘 temp
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_report(root: Path, report: Mapping[str, Any]) -> Tuple[Path, Path]:
    json_path = Path(root) / REPORT_REL
    md_path = json_path.with_suffix(".md")
    _atomic_write(json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_root", help="作品根目录")
    ap.add_argument("--write", action="store_true", help=f"落 {REPORT_REL} + .md（原子写）")
    ap.add_argument("--json", action="store_true", help="打印 JSON 而非 Markdown")
    ap.add_argument("--strict", action="store_true", help="有 block 时退出码 1（默认 0；gate 读侧车）")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{ns.project_root}")
        return 2
    report = build(root)
    if ns.write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] verifier coverage JSON → {json_path}")
        print(f"[ok] verifier coverage MD   → {md_path}")
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not ns.write:
        print(render_markdown(report))
    return 1 if (ns.strict and report["summary"]["block"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
