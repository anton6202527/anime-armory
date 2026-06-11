#!/usr/bin/env python3
"""音色声纹一致性——对同一 voice_key 的逐句 wav 抽 speaker embedding，算同键余弦地板，
跨句/跨集低于地板=音色【实际】漂移。

补 voice_consistency.py 的盲区：那条线只比 `voice_key` 字符串是否相等，键写对了但后端实际
克隆/下发的音色因参考音质量、零样本漂移、后端音色映射而变，测不出来——脸侧有 face_consistency
拿 ArcFace 量真实相似度，音色侧此前没有等价的声纹机检。本模块与脸侧 flag-band 完全同构：

  - 不写死阈值：用同一角色（同 voice_key）句子之间的内部互余弦地板当"同一把嗓子下限"；
  - 每句 vs 组质心余弦落 🟢/🟡/🔴；低于 地板−margin=🔴、地板带=🟡；
  - 依赖 resemblyzer / speechbrain ECAPA（缺则优雅跳过，标 mode=no_speaker_backend +
    precision=insufficient_precision，**交还人判**，绝不输出假相似度）；
  - 占位轨（macOS say 应急、占位=True）单列不参与比对。

纯数学部分（cosine/calibrate_floor/band/analyze_groups）不依赖音频后端，带 pytest。
cd skills/n2d-identity/scripts && python3 -m pytest test_voice_print_consistency.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import math
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402
    CONSISTENCY_FINDINGS_KIND,
    IDENTITY_VOICE_PRINT_REPORT_KIND,
    consistency_dim_spec,
    production_dir,
)

VOICE_PRINT_REPORT_KIND = IDENTITY_VOICE_PRINT_REPORT_KIND
VOICE_DIM_KEY = "voice_consistency"

# resemblyzer d-vector 同说话人余弦经验下限 ~0.75（不同说话人通常 <0.6）；样本不足时的保守回退地板。
FALLBACK_FLOOR = 0.75
# 同一角色逐句 vs 质心余弦相对【中位数】的容许跌幅——超过即判音色漂移。用中位数而非最小值
# 自标定，鲁棒于少数离群句（离群句不会把地板拖到 0 反而自我豁免）。
DRIFT_MARGIN = 0.18
DEFAULT_MARGIN = 0.06  # 🟡 warn 缓冲带宽
# 标 precision：有真实声纹信号 = ok；缺后端 = insufficient_precision（与脸侧 pillow_fallback 同义）。
INSUFFICIENT_PRECISION = "insufficient_precision"


# ── 纯数学（无音频依赖，可单测） ─────────────────────────────────────────────
def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _median(values: Sequence[float]) -> float:
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def calibrate_floor(line_scores: Sequence[float], drift_margin: float = DRIFT_MARGIN,
                    fallback: float = FALLBACK_FLOOR) -> float:
    """漂移地板 = 逐句 vs 质心余弦【中位数】− 容许跌幅；样本不足回退保守经验值。

    不写死阈值，用本角色内部一致性自标定（与 face_consistency 同构）。用中位数而非最小值：
    少数离群句（真换音色）不会把地板拖到 0 反而自我豁免——这是 voice 与 face 的关键差异，
    face 的 intra 取自可信定妆参考组，voice 的句子里可能就混着漂移句。
    """
    scores = [s for s in line_scores if s is not None]
    if len(scores) < 2:
        return fallback
    return _median(scores) - drift_margin


def band(score: float, floor: float, margin: float = DEFAULT_MARGIN) -> str:
    """🟢 ok（≥地板）/ 🟡 warn（地板带内，floor-margin..floor）/ 🔴 bad（<地板-margin）。"""
    if score >= floor:
        return "ok"
    if score >= floor - margin:
        return "warn"
    return "bad"


def _centroid(vectors: Sequence[Sequence[float]]) -> List[float]:
    n = len(vectors)
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / n for i in range(dim)]


def analyze_group(embeddings: Sequence[Sequence[float]], margin: float = DEFAULT_MARGIN) -> Dict[str, Any]:
    """一个角色（同 voice_key）的逐句 embedding → {floor, lines:[{idx,score,band}], drift_count}。

    floor = 句间互余弦最小值自标定；每句 vs 组质心余弦落 band。单句无从比对 → floor_calibrated=False。
    """
    vecs = [v for v in embeddings if v]
    if len(vecs) < 2:
        return {"floor": FALLBACK_FLOOR, "floor_calibrated": False, "lines": [], "drift_count": 0,
                "note": "单句样本无从互比，地板退回保守经验值；不足以判音色漂移"}
    centroid = _centroid(vecs)
    line_scores = [cosine(v, centroid) for v in vecs]
    floor = calibrate_floor(line_scores)  # 中位数自标定，鲁棒于少数离群句
    lines = []
    drift = 0
    for idx, score in enumerate(line_scores):
        b = band(score, floor, margin)
        if b == "bad":
            drift += 1
        lines.append({"idx": idx, "score": round(score, 4), "band": b})
    return {"floor": round(floor, 4), "floor_calibrated": True, "lines": lines, "drift_count": drift}


def analyze_groups(groups: Mapping[str, Sequence[Sequence[float]]], margin: float = DEFAULT_MARGIN) -> Dict[str, Any]:
    """{ (角色,voice_key) 标签: [逐句 embedding] } → 逐组漂移分析 + 汇总。"""
    out: Dict[str, Any] = {}
    total_drift = 0
    for label, embs in groups.items():
        res = analyze_group(embs, margin)
        out[label] = res
        total_drift += res.get("drift_count", 0)
    return {"groups": out, "total_drift": total_drift}


# ── 音频后端（可选，缺则优雅跳过） ────────────────────────────────────────────
def load_speaker_encoder() -> Tuple[Optional[str], Any]:
    """返回 (backend_name, encoder)；都不可用返回 (None, None)，调用方据此优雅降级。"""
    try:
        from resemblyzer import VoiceEncoder  # type: ignore
        return "resemblyzer", VoiceEncoder(verbose=False)
    except Exception:
        pass
    try:
        from speechbrain.pretrained import EncoderClassifier  # type: ignore
        enc = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
        return "speechbrain_ecapa", enc
    except Exception:
        return None, None


def embed_wav(path: str, backend: str, encoder: Any) -> Optional[List[float]]:
    try:
        if backend == "resemblyzer":
            from resemblyzer import preprocess_wav  # type: ignore
            wav = preprocess_wav(path)
            return list(map(float, encoder.embed_utterance(wav)))
        if backend == "speechbrain_ecapa":
            import torchaudio  # type: ignore
            sig, _ = torchaudio.load(path)
            emb = encoder.encode_batch(sig).squeeze().tolist()
            return list(map(float, emb))
    except Exception:
        return None
    return None


# ── 读时长清单 → 逐角色逐句 wav，跑分析 ──────────────────────────────────────
def _entry_voice_key(entry: Mapping[str, Any]) -> str:
    return str(entry.get("voice_key") or entry.get("音色键") or "").strip()


def _manifest_paths(root: str, ep: str) -> Optional[str]:
    for base in ("合成", "出视频"):
        p = os.path.join(root, base, ep, "配音", "时长清单.json")
        if os.path.isfile(p):
            return p
    return None


def collect_wav_groups(root: str, ep: str) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """读一集时长清单 → { '角色|voice_key': [line wav 绝对路径] }（跳过占位轨/缺 wav）。"""
    mp = _manifest_paths(root, ep)
    groups: Dict[str, List[str]] = {}
    meta: Dict[str, str] = {"manifest": mp or "", "episode": ep}
    if not mp:
        meta["status"] = "no_manifest"
        return groups, meta
    try:
        data = json.load(open(mp, encoding="utf-8"))
    except Exception as exc:
        meta["status"] = f"invalid:{exc}"
        return groups, meta
    items = data if isinstance(data, list) else (data.get("items") or [])
    base_dir = os.path.dirname(mp)
    for entry in items:
        if not isinstance(entry, Mapping) or entry.get("占位") is True or entry.get("placeholder") is True:
            continue
        char = str(entry.get("角色") or entry.get("character") or "").strip()
        vk = _entry_voice_key(entry)
        wav = str(entry.get("line_wav") or entry.get("wav") or "").strip()
        if not (char and wav):
            continue
        wav_path = wav if os.path.isabs(wav) else os.path.join(base_dir, wav)
        if not os.path.isfile(wav_path):
            continue
        groups.setdefault(f"{char}|{vk}", []).append(wav_path)
    meta["status"] = "ok" if groups else "no_usable_lines"
    return groups, meta


def analyze(root: str, ep: str, margin: float = DEFAULT_MARGIN) -> Dict[str, Any]:
    """一集声纹一致性分析报告（available/mode/precision + 逐角色漂移）。"""
    wav_groups, meta = collect_wav_groups(root, ep)
    report: Dict[str, Any] = {
        "kind": VOICE_PRINT_REPORT_KIND, "episode": ep, "manifest": meta.get("manifest", ""),
        "margin": margin,
    }
    if not wav_groups:
        report.update(available=False, mode="no_audio", precision=INSUFFICIENT_PRECISION,
                      note=f"无可用逐句 wav（{meta.get('status')}）——交还人判，不报假漂移", groups={}, total_drift=0)
        return report
    backend, encoder = load_speaker_encoder()
    if backend is None:
        report.update(available=False, mode="no_speaker_backend", precision=INSUFFICIENT_PRECISION,
                      note="未装 resemblyzer/speechbrain 声纹后端——本机无法量音色相似度，交还人判（脸侧缺 insightface 同样降级）",
                      groups={}, total_drift=0, character_groups=sorted(wav_groups))
        return report
    emb_groups: Dict[str, List[List[float]]] = {}
    for label, paths in wav_groups.items():
        embs = [e for e in (embed_wav(p, backend, encoder) for p in paths) if e]
        if embs:
            emb_groups[label] = embs
    analysis = analyze_groups(emb_groups, margin)
    report.update(available=True, mode=backend, precision="ok", **analysis)
    return report


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _severity_for_group(group: Mapping[str, Any]) -> str:
    lines = group.get("lines") if isinstance(group.get("lines"), list) else []
    if any(isinstance(line, Mapping) and line.get("band") == "bad" for line in lines):
        return "block"
    if any(isinstance(line, Mapping) and line.get("band") == "warn" for line in lines):
        return "warn"
    return "info"


def findings_payload(root: str, ep: str, report: Mapping[str, Any]) -> Dict[str, Any]:
    """voice_print report → n2d_consistency_findings, so score/batch/feedback use the same channel."""
    spec = consistency_dim_spec(VOICE_DIM_KEY) or {}
    findings: List[Dict[str, Any]] = []
    if report.get("available"):
        for label, group in sorted((report.get("groups") or {}).items()):
            if not isinstance(group, Mapping):
                continue
            severity = _severity_for_group(group)
            if severity not in {"block", "warn"}:
                continue
            lines = group.get("lines") if isinstance(group.get("lines"), list) else []
            bad = [line for line in lines if isinstance(line, Mapping) and line.get("band") == "bad"]
            warn = [line for line in lines if isinstance(line, Mapping) and line.get("band") == "warn"]
            findings.append({
                "severity": severity,
                "dimension": spec.get("label", "音色一致性"),
                "dim_key": VOICE_DIM_KEY,
                "message": (
                    f"声纹机检发现「{label}」音色漂移：bad={len(bad)} warn={len(warn)}，"
                    f"floor={group.get('floor')} mode={report.get('mode')}"
                ),
                "loc": f"voice_print:{label}",
                "episode": ep,
                "return_to_stage": spec.get("return_to_stage", "voice"),
                "rerun_scope": spec.get("scope", "回 n2d-voice 重配受影响角色台词。"),
                "affected_shots": [],
                "affected_artifacts": [str(report.get("manifest") or "")] if report.get("manifest") else [],
                "source": "n2d-identity/voice_print",
            })
    counts = {"block": 0, "warn": 0, "info": 0}
    for finding in findings:
        counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1
    auto_tasks: List[Dict[str, Any]] = []
    active = [f for f in findings if f["severity"] in {"block", "warn"}]
    if active:
        artifacts: List[str] = []
        for finding in active:
            artifacts.extend(finding.get("affected_artifacts", []))
        auto_tasks.append({
            "return_to_stage": spec.get("return_to_stage", "voice"),
            "dimensions": [VOICE_DIM_KEY],
            "scope": spec.get("scope", "回 n2d-voice 重配受影响角色台词。"),
            "affected_shots": [],
            "affected_artifacts": sorted(set(a for a in artifacts if a)),
            "findings": active[:12],
        })
    return {
        "kind": CONSISTENCY_FINDINGS_KIND,
        "version": 1,
        "root": os.fspath(root),
        "episode": ep,
        "generated_at": _now_iso(),
        "summary": {"total": len(findings), "severity": counts, "by_dim": {spec.get("label", "音色一致性"): counts}},
        "findings": findings,
        "auto_return_tasks": auto_tasks,
        "source": {"kind": VOICE_PRINT_REPORT_KIND, "path": f"identity_voice_print_{ep}.json"},
    }


def run(root: str, ep: str, margin: float = DEFAULT_MARGIN) -> int:
    report = analyze(root, ep, margin)
    out_dir = production_dir(root)
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, f"identity_voice_print_{ep}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    findings_p = os.path.join(out_dir, f"consistency_findings_voice_print_{ep}.json")
    with open(findings_p, "w", encoding="utf-8") as f:
        json.dump(findings_payload(root, ep, report), f, ensure_ascii=False, indent=2)
        f.write("\n")
    if not report.get("available"):
        print(f"⚠️ 声纹机检 {ep}: {report.get('mode')}（{report.get('precision')}）→ 交还人判 · {p}")
        return 0
    drift = report.get("total_drift", 0)
    icon = "🔴" if drift else "✅"
    print(f"{icon} 声纹机检 {ep}: mode={report.get('mode')} 音色漂移句数={drift} → {p}；findings → {findings_p}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="音色声纹一致性机检（speaker embedding flag-band）")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument("--json", action="store_true", help="只输出声纹报告 JSON，不写文件")
    ns = ap.parse_args(argv)
    if ns.json:
        print(json.dumps(analyze(ns.root.rstrip("/"), ns.episode, ns.margin), ensure_ascii=False, indent=2))
        return 0
    return run(ns.root.rstrip("/"), ns.episode, ns.margin)


if __name__ == "__main__":
    raise SystemExit(main())
