#!/usr/bin/env python3
"""出图前·脸漂风险分（③ 把 LoRA/加强参考的判断从「事后升档」前移到「事前预测」）。

现状链路里，脸漂只有**事后**才被处理：跨集出现 ≥2 集 warn/block 才由 n2d-identity 建议升 LoRA
（identity.py lora_upgrade_candidates）——意味着前两集已经漂了才反应。本脚本在**出图之前**，用
分镜本身的高危信号预测哪些角色本集容易脸漂，提前提示加强参考 / 建表情库 / 上 LoRA。

风险信号（全部来自 storyboard.json + identity_registry.json，不读像素、不花钱）：
  - 近景占比   ：该角色出现的镜里 CU/ECU/MCU/OTS/特写/反打 的比例（近景脸放大，漂移最刺眼）；
  - 大表情数   ：desc 命中强情绪（哭/怒/狂喜/崩溃…）的镜（大表情让 AI 重画整张脸）；
  - 多人同框   ：与其它命名角色同框的镜（单图参考后端难分别控脸，易串脸）；
  - 极端角度   ：lens/desc 命中该角色 angle_policy.risky（俯仰/远景/逆光暗部）的镜；
  - 锁脸档位   ：默认后端的身份能力——Codex/OpenAI/Dreamina/Nano 只有多图参考/图生图、无持久主体 ID，
                 Seedream/可灵/Sora 可注册原生主体库更稳，LoRA 最稳。
  - 复现间隔   ：本集是否为该角色「长间隔再登场」（identity_drift_report 里上次出场距本集缺席 ≥ 阈值）——
                 EntityBench(2026) 实证一致性随复现间隔急剧衰退，长间隔再登场最易崩脸，出图前应重锚。

输出 生产数据/face_drift_risk_<ep>.json + .md，按风险排序，对 high/medium 角色给出可执行建议
（与 image_qc 的 no_expression_lib_ref gate、n2d-lora init 对齐）。预测档（high/medium）默认只提示不阻断；
核心长线角在无持久主体后端上只有当项目没有明确的“项目记忆/真实参考图束/分层合成/QC”执行计划时，
才升为出图前阻断。

**实测漂移回灌（②）**：本脚本还读 生产数据/identity_drift_report.json——n2d-identity 对**已出图集**
真量出的跨集漂移（embedding 质心 high / block 级脸漂镜）。命中的角色升 **block** 档（既成事实，非预测），
退出码 2，让 SOP/gate 能卡住"带病继续出下一集图"。无该报告 / 无 insightface → 仅预测档生效，不假报。

用法：python3 face_drift_risk.py <作品根> <第N集> [--json]
纯 stdlib（实测数只读 identity 产出的 JSON，本脚本不读像素、不依赖 insightface）；纯函数有 pytest 覆盖。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
try:
    from n2d_contract import classify_image_backend, image_identity_profile, image_lock_tier
except Exception:  # pragma: no cover - 测试/异常布局兜底
    classify_image_backend = None  # type: ignore
    image_identity_profile = None  # type: ignore
    image_lock_tier = None  # type: ignore

# 近景景别（与 image_qc.CLOSEUP_MARKERS / video_qc 同义；本 skill 自留一份，不跨 import）。
CLOSEUP_MARKERS = ("ECU", "MCU", "BCU", "CU", "OTS", "反打", "特写", "近景", "过肩", "脸部")
# 强情绪（与 image_qc.STRONG_EMOTION_MARKERS 对齐：表情镜脸漂的触发词）。
STRONG_EMOTION_MARKERS = (
    "哭", "泣", "落泪", "含泪", "泪", "怒", "愤", "暴怒", "狂怒", "震惊", "惊恐", "恐惧",
    "狂喜", "大笑", "狂笑", "嘶吼", "咆哮", "嚎", "痛苦", "崩溃", "狰狞", "扭曲", "癫狂",
    "失控", "绝望", "悲恸", "惊愕",
)
READY_STATUSES = {"registered", "ready"}
CORE_SCOPE_MARKERS = ("核心", "长线", "全篇", "主角", "女主", "男主", "主反派", "贯穿")
# 2026 公认正面+3/4+侧面是身份核心集，纯 90° 正侧是较弱的重投影锚。
# 现在 three_quarter 是所有人物/形态的基础硬包；近景比例只影响完整表情库/动作参考等增强项。
CU_HEAVY_RATIO = 0.4

WEIGHTS = {"base_reference_group": 28, "base_multi_reference": 22, "base_face_embedding": 14,
           "base_native_unregistered": 20, "base_native": 8, "base_lora": 0,
           "closeup": 30, "emotion_each": 8, "emotion_cap": 24,
           "multi": 20, "angle_each": 6, "angle_cap": 24,
           "recurrence_base": 18, "recurrence_per": 4, "recurrence_cap": 30,
           # in-context 记功：strong-in-context 模型（如 GPT Image 2 高保真多参考/上下文一致性）在集内同源出图
           # （scene_batch 默认开，连续同场景多镜可同源 batch 出）比泛多参考后端更稳，给集内 base 适度减分。
           # 下限锁在 base_face_embedding（14），永不低于真脸嵌入锁；只抵 base，不碰 recurrence 跨集项 → 跨集不放水。
           "in_context_strong_credit": 6}
BAND_HIGH, BAND_MEDIUM = 55, 30
# 复现间隔阈值：上次出场距本集缺席 ≥ 这么多集 = 长间隔再登场（与 n2d-identity 同义，本 skill 自留一份不跨 import）。
RECURRENCE_GAP_THRESHOLD = 2
PROJECT_MEMORY_BACKENDS = {"codex", "openai", "dreamina", "nano_banana"}
PROJECT_MEMORY_TOKENS = (
    "参考图入参清单", "资产身份注册层", "identity_registry", "reference_group",
    "image2image", "图生图", "多图参考", "真实附件", "真实参考图",
)
FACE_REFERENCE_TOKENS = ("脸部特写", "face_anchor", "expression", "表情库", "表情锚")
MULTI_SUBJECT_TOKENS = (
    "split_composite_required", "shot_reverse_shot_or_split_composite_required",
    "分别出图", "分层合成", "单人分层", "多人同框身份槽位", "多人同框执行策略",
)


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def is_closeup(lens_or_desc: str) -> bool:
    s = str(lens_or_desc or "").upper()
    return any(m.upper() in s for m in CLOSEUP_MARKERS)


def has_strong_emotion(text: str) -> bool:
    t = str(text or "")
    return any(m in t for m in STRONG_EMOTION_MARKERS)


def extreme_angle_tokens(lens: str, desc: str, risky: Sequence[str]) -> List[str]:
    """命中该角色 angle_policy.risky 的高危项（lens/desc 文字 → risky token）。纯函数·可测。"""
    text = f"{lens or ''} {desc or ''}"
    hit: List[str] = []
    risky_set = set(risky or [])
    if ("extreme_top" in risky_set) and re.search(r"俯|顶光|顶视|鸟瞰|top", text, re.I):
        hit.append("extreme_top")
    if ("extreme_low" in risky_set) and re.search(r"仰|low\b|脚下", text, re.I):
        hit.append("extreme_low")
    if ("face_too_small" in risky_set) and re.search(r"\bELS\b|\bLS\b|远景|全景|大全|群像", text, re.I):
        hit.append("face_too_small")
    if ("deep_shadow" in risky_set) and re.search(r"逆光|暗部|阴影|剪影|暗光|背光|silhouet", text, re.I):
        hit.append("deep_shadow")
    return hit


def three_quarter_ready(form: Mapping[str, Any]) -> bool:
    """该形态是否已备好 ready 的 3/4 侧脸参考（reference_atlas.base_views.three_quarter，
    或 reference_group 里 45°/三分之二/three_quarter 命名的图）。纯函数·可测。

    口径：base_views.three_quarter.status ∈ {ready,registered} 为准；若 atlas 未建但
    reference_group 直接挂了 45° 命名图，也算就绪（旧项目兼容）。planned 不算。"""
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    base_views = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
    tq = base_views.get("three_quarter")
    if isinstance(tq, Mapping) and _status_value(tq.get("status")) in READY_STATUSES:
        return True
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    for key, val in rg.items():
        if re.search(r"three_quarter|45|三分之二|三七", str(key), re.I) and str(val or "").strip():
            return True
    return False


def _status_value(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("status")
    return str(value or "").strip().lower()


def _ref_path_status_ready(ref: Any) -> Tuple[str, bool]:
    if isinstance(ref, Mapping):
        path = str(ref.get("path") or "").strip()
        return path, _status_value(ref.get("status")) in READY_STATUSES
    path = str(ref or "").strip()
    return path, bool(path)


def same_source_expression_ready(form: Mapping[str, Any]) -> bool:
    """是否已有 ready 的非中性同源表情参考。

    中性脸锚能辅助锁脸，但不等于“表情库”；只有显式 `_表情_` 资产或 emotion/label
    标为具体情绪的 ready 条目，才抵消 Codex-only 核心角色预测 high 的 preflight block。
    """
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    neutral = {"", "中性", "neutral", "base", "基础", "脸锚", "同源脸锚"}
    for source in (rg.get("expressions"), atlas.get("expression_refs")):
        for ref in source or []:
            path, ready = _ref_path_status_ready(ref)
            if not path or not ready:
                continue
            emotion = ""
            if isinstance(ref, Mapping):
                emotion = str(ref.get("emotion") or ref.get("label") or "").strip().lower()
            if "_表情_" in Path(path).stem:
                return True
            if emotion and emotion not in neutral and not emotion.endswith("同源脸锚"):
                return True
    return False


def _load_backend_capability_record(root: Path, backend: str) -> Dict[str, Any]:
    path = root / "生产数据" / "image_backend_capabilities" / f"{backend}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _prompt_text(root: Path, ep: str) -> str:
    path = root / "出图" / ep / "prompt" / "01_分镜出图.md"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def backend_can_use_project_memory(root: Path, backend: str, profile: Mapping[str, Any]) -> bool:
    """无持久主体 ID 不等于无一致性能力。

    这里判的是“能否消费项目记忆”：项目文件中生成的定妆图、脸部锚、场景/道具参考和上一帧成图，
    是否能作为真实图片入参传给当前后端。Codex 走 codex exec --image 的 auditable bundle；
    OpenAI/Dreamina/Nano 这类多参考/编辑后端也按同一思想处理。它不是服务端 subject_id。
    """
    if bool(profile.get("persistent_subject")):
        return False
    capability = _load_backend_capability_record(root, backend)
    ref = capability.get("reference_input") if isinstance(capability.get("reference_input"), Mapping) else {}
    modes = {str(x).strip() for x in (capability.get("generation_modes") or []) if str(x).strip()}
    true_refs = bool(profile.get("multi_reference")) or bool(capability.get("supports_high_fidelity_reference"))
    true_refs = true_refs or bool(ref.get("mode")) or bool(modes & {"image_reference", "image_edit", "multi_turn_edit"})
    if backend == "codex":
        runner = Path(__file__).with_name("codex_image_runner.py")
        return true_refs and runner.is_file()
    return true_refs and (backend in PROJECT_MEMORY_BACKENDS or bool(profile.get("multi_reference")))


def project_memory_mitigation(root: Path, ep: str, backend: str, profile: Mapping[str, Any],
                              signals: Mapping[str, Any]) -> Dict[str, Any]:
    """项目记忆缓解判定。

    ready=True 只表示“预测 high 不应因无 subject_id 自动阻断”；不表示参考图已经生成完毕。
    后续仍由 image_preflight / codex_reference_bundles / image_qc 检查 actual --image 入参、
    missing_ready_refs 和 full QC。
    """
    gaps: List[str] = []
    if not backend_can_use_project_memory(root, backend, profile):
        gaps.append("backend_without_verified_true_image_reference_support")
    text = _prompt_text(root, ep)
    if not text:
        gaps.append("episode_prompt_pack_missing")
    elif not all(token in text for token in ("参考图入参清单", "资产身份注册层")):
        gaps.append("prompt_missing_reference_bundle_contract")
    elif not any(token in text for token in PROJECT_MEMORY_TOKENS):
        gaps.append("prompt_missing_project_memory_tokens")
    if int(signals.get("closeup", 0)) > 0 or int(signals.get("emotion", 0)) > 0:
        if not any(token in text for token in FACE_REFERENCE_TOKENS):
            gaps.append("prompt_missing_face_anchor_or_expression_refs")
    if int(signals.get("multi", 0)) > 0:
        if not any(token in text for token in MULTI_SUBJECT_TOKENS):
            gaps.append("prompt_missing_split_composite_or_subject_slots")
    return {
        "ready": not gaps,
        "strategy": "project_memory_reference_bundle",
        "backend": backend,
        "gaps": gaps,
        "requirements": [
            "先生成共享定妆/脸部特写/场景道具主参考并标 ready",
            "正式分镜出图必须生成 codex_reference_bundles 或等价 reference_manifest",
            "每个高风险镜 actual image inputs 不得为 0，missing_ready_refs 必须清零",
            "多人同框按 split_composite/反打/单人分层执行，成图后跑 full image_qc",
        ],
    }


def missing_3q_baseline(appear: int, tq_ready: bool) -> bool:
    """任一入镜人物缺 ready 的 3/4 侧脸 → True。纯函数·可测。"""
    return int(appear) > 0 and not tq_ready


def is_core_scope(scope: str, name: str = "") -> bool:
    text = f"{scope or ''} {name or ''}"
    return any(marker in text for marker in CORE_SCOPE_MARKERS)


def lock_tier(default_backend: str, image_adapters: Mapping[str, Any], lora: Mapping[str, Any]) -> str:
    """该角色当前锁脸档位。

    档位由 `n2d/_lib/n2d_schema.py::IMAGE_IDENTITY_PROFILES` 驱动，避免把
    Dreamina/Nano 这类多参考后端误判成 Seedream/可灵的持久主体层。
    """
    if image_lock_tier is not None:
        return image_lock_tier(str(default_backend or ""), dict(image_adapters or {}), dict(lora or {}))  # type: ignore[misc]
    if str((lora or {}).get("status") or "").strip() in {"ready", "training"}:
        return "lora"
    return "multi_reference"


def score_character(signals: Mapping[str, Any], tier: str, in_context: str = "") -> Dict[str, Any]:
    """风险分 + 档位 + 驱动因子（纯函数·可测）。

    signals: {appear, closeup, emotion, multi, angle}（计数）。score 0–100，band high/medium/low。
    in_context: 模型「同次/同会话内」多参考/上下文身份一致性强度（来自 IMAGE_IDENTITY_PROFILES.in_context_consistency）。
      仅当 tier=='multi_reference' 且 in_context=='strong'（=GPT Image 2 等强上下文一致性模型）时，
      给集内 base 减一笔 in-context 记功（封顶不低于 face_embedding base=14，永不超过真脸嵌入锁），
      且**只抵 base，不碰 recurrence_gap 跨集项**——跨集复现仍按 multi_reference 不放水。
    """
    appear = max(int(signals.get("appear", 0)), 0)
    base = {
        "reference_group": WEIGHTS["base_reference_group"],
        "multi_reference": WEIGHTS["base_multi_reference"],
        "face_embedding": WEIGHTS["base_face_embedding"],
        "native_unregistered": WEIGHTS["base_native_unregistered"],
        "native_subject": WEIGHTS["base_native"],
        "native": WEIGHTS["base_native"],  # 兼容旧 report
        "lora": WEIGHTS["base_lora"],
    }.get(tier, WEIGHTS["base_reference_group"])
    drivers: List[Dict[str, Any]] = [{"factor": f"锁脸档位={tier}", "points": base}]
    if tier == "multi_reference" and str(in_context or "").strip().lower() == "strong":
        eff_base = max(base - WEIGHTS["in_context_strong_credit"], WEIGHTS["base_face_embedding"])
        credit = round(eff_base - base, 1)  # 负值
        if credit < 0:
            drivers.append({"factor": "同源场景 in-context 记功(strong·如 GPT Image 2)", "points": credit})
            base = eff_base
    closeup_ratio = (signals.get("closeup", 0) / appear) if appear else 0.0
    multi_ratio = (signals.get("multi", 0) / appear) if appear else 0.0
    cu = round(closeup_ratio * WEIGHTS["closeup"], 1)
    emo = min(int(signals.get("emotion", 0)) * WEIGHTS["emotion_each"], WEIGHTS["emotion_cap"])
    mp = round(multi_ratio * WEIGHTS["multi"], 1)
    ang = min(int(signals.get("angle", 0)) * WEIGHTS["angle_each"], WEIGHTS["angle_cap"])
    rec_gap = max(int(signals.get("recurrence_gap", 0) or 0), 0)
    recur = 0.0
    if rec_gap >= RECURRENCE_GAP_THRESHOLD:
        recur = min(WEIGHTS["recurrence_base"] + (rec_gap - RECURRENCE_GAP_THRESHOLD) * WEIGHTS["recurrence_per"],
                    WEIGHTS["recurrence_cap"])
    if cu:
        drivers.append({"factor": f"近景占比 {signals.get('closeup',0)}/{appear}", "points": cu})
    if emo:
        drivers.append({"factor": f"大表情 {signals.get('emotion',0)} 镜", "points": emo})
    if mp:
        drivers.append({"factor": f"多人同框 {signals.get('multi',0)}/{appear}", "points": mp})
    if ang:
        drivers.append({"factor": f"极端角度 {signals.get('angle',0)} 镜", "points": ang})
    if recur:
        drivers.append({"factor": f"长间隔再登场(缺席{rec_gap}集)", "points": recur})
    score = min(round(base + cu + emo + mp + ang + recur, 1), 100.0)
    band = "high" if score >= BAND_HIGH else ("medium" if score >= BAND_MEDIUM else "low")
    drivers.sort(key=lambda d: d["points"], reverse=True)
    return {"score": score, "band": band, "tier": tier, "drivers": drivers}


def suggestions_for(name: str, scored: Mapping[str, Any], signals: Mapping[str, Any],
                    char_id: str, form: str, root_hint: str = "<作品根>",
                    backend_profile: Optional[Mapping[str, Any]] = None) -> List[str]:
    """按驱动因子 + 档位给可执行建议（与 image_qc 表情库 gate、n2d-lora init 对齐）。纯函数·可测。"""
    out: List[str] = []
    tier = scored.get("tier")
    appear = max(int(signals.get("appear", 0)), 1)
    # 阈值化：只在某高危信号**材料性出现**时给对应建议，避免每个角色都堆同一套样板话。
    if tier == "reference_group":
        out.append("当前后端无已知多参考/持久主体能力——跨镜全靠单组参考图和锚点句，是脸漂高危底色。")
    elif tier == "multi_reference":
        label = str((backend_profile or {}).get("label") or "当前后端")
        out.append(f"{label} 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。")
        if str((backend_profile or {}).get("canonical") or "") == "dreamina":
            out.append("Dreamina/即梦参考框有粘性：切换角色前清空参考图；场景定妆必须清空人物参考。")
    elif tier == "face_embedding":
        out.append("已挂脸嵌入锁（IP-Adapter FaceID 等）：比纯参考图组稳，但不是后端原生持久主体 ID——"
                   "核心长线角若仍跨集漂，下一档考虑注册原生主体或上 LoRA。")
    elif tier == "native_unregistered":
        label = str((backend_profile or {}).get("label") or "所选后端")
        out.append(f"{label} 支持持久主体/角色 ID，但该角色尚未 registered/ready；核心或高危镜建议先注册主体再出图。")
    if int(signals.get("emotion", 0)) >= 2:
        out.append("大表情镜多：必建表情库 expressions + 脸部特写参考，首尾双帧只插值（对齐 image_qc no_expression_lib_ref）。")
    if int(signals.get("closeup", 0)) / appear >= 0.4:
        out.append("近景占比高：补脸部特写主参考，近景镜锁脸型/五官比例/发型发饰。")
    if int(signals.get("multi", 0)) >= 2:
        if tier in {"native_unregistered", "native_subject", "face_embedding"}:
            out.append("多人同框多：按 registry priority 标 primary，逐主体绑定画面槽位(LEFT/RIGHT/FOREGROUND/BACKGROUND)"
                       "+各自原生主体名额/参考——空间槽位绑定是同框硬约束（gate 对所有后端 block），决不用一张共享参考喂整帧。")
        else:
            out.append("多人同框多：换用支持持久主体的官方后端（Seedream/可灵/Sora）或把同框拆成正反打分别出；"
                       "无论哪种都必须逐主体写画面槽位+各自参考（空间绑定硬约束，否则模型把多张脸平均成一张）。")
    if int(signals.get("angle", 0)) >= 1:
        out.append("极端角度/远景/逆光：按 angle_policy.requires_extra_reference 补侧/背/全身参考，或改分镜避开极端角度。")
    if scored.get("band") == "high" and tier != "lora":
        out.append(f"风险 high 且未上 LoRA：考虑 python3 skills/n2d-lora/scripts/lora.py init '{root_hint}' "
                   f"--character-id {char_id} --form '{form}'（事前升档，别等跨集漂了再补）。")
    return out


# ── 实测漂移回灌（②：把 n2d-identity 已**测**出的跨集漂移，前移成本集出图前的 block） ──────────

def measured_block_reason(measured: Mapping[str, Any]) -> str:
    """把实测漂移命中明细拼成人读理由（纯函数·可测）。"""
    bits: List[str] = []
    if measured.get("embedding_drift_high"):
        spans = str(measured.get("spans") or "").strip()
        bits.append(f"跨集质心漂移 high×{measured['embedding_drift_high']}" + (f"（{spans}）" if spans else ""))
    if measured.get("total_block"):
        fb = str(measured.get("first_bad_episode") or "").strip()
        bits.append(f"已出现 block 级脸漂 {measured['total_block']} 镜" + (f"（first={fb}）" if fb else ""))
    return "；".join(bits)


def measured_drift_block(drift_report: Optional[Mapping[str, Any]],
                         aliases: Set[str], name: str) -> Optional[Dict[str, Any]]:
    """该角色在 identity_drift_report 里是否已**实测**到该升 block 的跨集漂移（既成事实，非预测）。

    命中任一即返回明细（否则 None）：
      ① embedding_drift 里有 severity=high 段（每集各自过 floor 但质心逐集偏离锚点）；
      ② characters[char].total_block>0（已出现 block 级脸漂镜）。
    drift_report.available=False（无 insightface / 跳过机检）→ 一律 None，不假报。
    角色对号：drift report 的 char 名 == 本角色 name 或落在其 aliases 里。纯函数·可测。"""
    if not isinstance(drift_report, Mapping) or not drift_report.get("available"):
        return None
    chars = drift_report.get("characters") if isinstance(drift_report.get("characters"), Mapping) else {}
    emb = drift_report.get("embedding_drift") if isinstance(drift_report.get("embedding_drift"), Mapping) else {}
    name = str(name or "").strip()
    alias_set = set(aliases or set())
    for drift_char in set(chars.keys()) | set(emb.keys()):
        dc = str(drift_char).strip()
        if not dc or (dc != name and dc not in alias_set):
            continue
        emb_high = [e for e in (emb.get(drift_char) or [])
                    if isinstance(e, Mapping) and e.get("severity") == "high"]
        info = chars.get(drift_char) if isinstance(chars.get(drift_char), Mapping) else {}
        total_block = int(info.get("total_block", 0) or 0)
        if not emb_high and total_block <= 0:
            continue
        return {
            "drift_char": dc,
            "embedding_drift_high": len(emb_high),
            "total_block": total_block,
            "first_bad_episode": str(info.get("first_bad_episode") or "").strip(),
            "spans": "，".join(f"{e.get('episode_from')}→{e.get('episode_to')}(掉{e.get('drop')})"
                               for e in emb_high),
        }
    return None


def _episode_num(ep: str) -> Optional[int]:
    """从 '第N集' 抽集号；抽不到 → None。本 skill 自留一份，不跨 import n2d-identity。纯函数·可测。"""
    m = re.search(r"(\d+)", str(ep or ""))
    return int(m.group(1)) if m else None


def recurrence_reentry_risk(drift_report: Optional[Mapping[str, Any]],
                            aliases: Set[str], name: str, current_ep: str) -> Optional[Dict[str, Any]]:
    """本集是否为该角色「长间隔再登场」：identity_drift_report 里上次出场距本集缺席 ≥ 阈值
    （EntityBench 2026：跨镜一致性随复现间隔急剧衰退，长间隔再登场最易崩脸）。

    用 characters[char].episodes（已机检出场集）找本集之前最近一次出场，集号差 ≥ RECURRENCE_GAP_THRESHOLD
    即判长间隔再登场。返回 {last_episode, gap, current_episode} 或 None。
    复现是「出场排期」事实而非像素度量，故**不**要求 drift available（无 insightface 也能算）；
    drift 缺失 / 无历史出场 / 集号不可解析 → None（不假报）。角色对号同 measured_drift_block。纯函数·可测。"""
    if not isinstance(drift_report, Mapping):
        return None
    chars = drift_report.get("characters") if isinstance(drift_report.get("characters"), Mapping) else {}
    cur_n = _episode_num(current_ep)
    if cur_n is None or not chars:
        return None
    name = str(name or "").strip()
    alias_set = set(aliases or set())
    for drift_char, info in chars.items():
        dc = str(drift_char).strip()
        if not dc or (dc != name and dc not in alias_set) or not isinstance(info, Mapping):
            continue
        eps = info.get("episodes") if isinstance(info.get("episodes"), Mapping) else {}
        prior = [n for e in eps for n in [_episode_num(e)] if n is not None and n < cur_n]
        if not prior:
            return None
        last_n = max(prior)
        gap = cur_n - last_n - 1
        if gap >= RECURRENCE_GAP_THRESHOLD:
            last_label = next((str(e) for e in eps if _episode_num(e) == last_n), f"第{last_n}集")
            return {"last_episode": last_label, "gap": gap, "current_episode": str(current_ep)}
        return None
    return None


def load_prior_drift(root: Path) -> Dict[str, Any]:
    """读 生产数据/identity_drift_report.json（n2d-identity 对已出图集机检的真值）。读不到/无效 → {}。"""
    try:
        data = json.loads((root / "生产数据" / "identity_drift_report.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


# ── 数据装载 + 推断（best-effort I/O） ──────────────────────────────────────────

def project_default_backend(root: Path) -> str:
    """_设置.md 的『生图AI：X』→ 后端规范名（小写）；读不到 → codex（与全局默认一致）。"""
    raw = ""
    try:
        text = (root / "_设置.md").read_text(encoding="utf-8")
        m = re.search(r"生图AI[：:]\s*([^\n（(]+)", text)
        if m:
            raw = m.group(1).strip()
    except Exception:
        pass
    if classify_image_backend is not None:
        canon, kind = classify_image_backend(raw)  # type: ignore[misc]
        if kind == "approved" and canon:
            return canon
    low = raw.lower()
    alias = {"codex": "codex", "openai": "openai", "即梦": "dreamina", "dreamina": "dreamina",
             "可灵": "kling", "kling": "kling", "seedream": "seedream", "即梦seedream": "seedream",
             "sora": "sora", "nano banana": "nano_banana", "nano_banana": "nano_banana",
             "nanobanana": "nano_banana", "gemini": "nano_banana"}
    for k, v in alias.items():
        if k in low:
            return v
    return "codex"


def backend_profile(default_backend: str) -> Dict[str, Any]:
    if image_identity_profile is not None:
        return image_identity_profile(default_backend)  # type: ignore[misc]
    return {"canonical": default_backend, "label": default_backend, "persistent_subject": False, "multi_reference": True}


def _split_aliases(*texts: str) -> Set[str]:
    out: Set[str] = set()
    for t in texts:
        for part in re.split(r"[/／、,，|\s]+", str(t or "")):
            p = part.strip()
            if len(p) >= 2:
                out.add(p)
    return out


def load_characters(root: Path) -> List[Dict[str, Any]]:
    """identity_registry.json → 每角色 {id, name, aliases, form, angle_policy, image_adapters, lora}。
    多形态取第 1 形态做策略锚（多数角色单形态），lora 取任一 ready。"""
    path = root / "出图" / "共享" / "identity_registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    chars: List[Dict[str, Any]] = []
    for ch in data.get("characters") or []:
        cid = str(ch.get("id") or "").strip()
        forms = [f for f in (ch.get("forms") or []) if isinstance(f, dict)]
        if not cid or not forms:
            continue
        aliases = _split_aliases(ch.get("name") or "")
        for f in forms:
            aliases |= _split_aliases(f.get("asset_key") or "")
        f0 = forms[0]
        adapters = f0.get("identity_adapters") or {}
        expression_ready = any(same_source_expression_ready(f) for f in forms)
        # lora ready on ANY form 算已上档
        lora = {"status": "not_ready"}
        for f in forms:
            ls = str(((f.get("identity_adapters") or {}).get("lora") or {}).get("status") or "")
            if ls in {"ready", "training"}:
                lora = {"status": ls}
                break
        chars.append({
            "id": cid,
            "name": str(ch.get("name") or cid),
            "scope": str(ch.get("scope") or f0.get("scope") or ""),
            "aliases": aliases,
            "form": str(f0.get("form") or "常态"),
            "angle_policy": f0.get("angle_policy") or {},
            "image_adapters": adapters.get("image") or {},
            "lora": lora,
            "tq_ready": three_quarter_ready(f0),
            "expression_ready": expression_ready,
        })
    return chars


def load_clips(root: Path, ep: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads((root / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    return data.get("clips") or data.get("shots") or []


def clip_text(clip: Mapping[str, Any]) -> Tuple[str, str]:
    """(全文本, lens 串)——全文本含 label/scene/desc/continuity，用于角色匹配 + 情绪/角度判定。"""
    parts: List[str] = [str(clip.get("label") or ""), str(clip.get("scene") or "")]
    cont = clip.get("continuity") or {}
    parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or "")]
    lenses: List[str] = []
    for s in (clip.get("shots") or []):
        if isinstance(s, dict):
            parts.append(str(s.get("desc") or ""))
            lenses.append(str(s.get("lens") or ""))
    return " ".join(parts), " ".join(lenses)


def present_characters(text: str, chars: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return [c for c in chars if any(a in text for a in c.get("aliases") or set())]


def analyze(root: Path, ep: str) -> Dict[str, Any]:
    chars = load_characters(root)
    clips = load_clips(root, ep)
    default_backend = project_default_backend(root)
    profile = backend_profile(default_backend)
    prior_drift = load_prior_drift(root)  # ② 已出图集的实测漂移（identity_drift_report.json）
    by_id: Dict[str, Dict[str, Any]] = {
        c["id"]: {"char": c, "appear": 0, "closeup": 0, "emotion": 0, "multi": 0, "angle": 0,
                  "angle_tokens": set(), "clips": []}
        for c in chars
    }
    notes: List[str] = []
    if not chars:
        notes.append("identity_registry.json 缺失/无角色——无法算风险分。")
    if not clips:
        notes.append("storyboard.json 缺失/无 clips——先跑 n2d-script 分镜设计再算风险。")
    for clip in clips:
        text, lens = clip_text(clip)
        present = present_characters(text, chars)
        multi = len({c["id"] for c in present}) >= 2
        for c in present:
            agg = by_id[c["id"]]
            agg["appear"] += 1
            agg["clips"].append(str(clip.get("id") or clip.get("label") or ""))
            if is_closeup(lens) or is_closeup(text):
                agg["closeup"] += 1
            if has_strong_emotion(text):
                agg["emotion"] += 1
            if multi:
                agg["multi"] += 1
            toks = extreme_angle_tokens(lens, text, (c.get("angle_policy") or {}).get("risky") or [])
            if toks:
                agg["angle"] += 1
                agg["angle_tokens"].update(toks)
    results: List[Dict[str, Any]] = []
    for cid, agg in by_id.items():
        if agg["appear"] == 0:
            continue
        c = agg["char"]
        tier = lock_tier(default_backend, c.get("image_adapters") or {}, c.get("lora") or {})
        signals = {k: agg[k] for k in ("appear", "closeup", "emotion", "multi", "angle")}
        # ③+ 复现间隔回灌：本集是否为该角色长间隔再登场（出场排期事实，不要求 insightface）。
        reentry = recurrence_reentry_risk(prior_drift, c.get("aliases") or set(), c["name"], ep)
        signals["recurrence_gap"] = reentry["gap"] if reentry else 0
        scored = score_character(signals, tier, str((profile or {}).get("in_context_consistency") or ""))
        sug = suggestions_for(c["name"], scored, signals, cid, c["form"], str(root), profile)
        if reentry:
            sug = [
                f"↩️ 长间隔再登场：上次出场 {reentry['last_episode']}，缺席 {reentry['gap']} 集后本集重现——"
                "EntityBench 2026 实证一致性随复现间隔急剧衰退，出图前务必重锚（喂该角色质心定妆图/最强参考，"
                "核心角考虑升原生主体或 LoRA），别让模型「凭印象」重画。"
            ] + sug
        reference_gaps: List[str] = []
        # ③ 基础包缺 ready 的 3/4 侧脸：45° 不再是近景重角增强项，而是所有人物/形态基础角。
        if missing_3q_baseline(signals["appear"], bool(c.get("tq_ready"))):
            reference_gaps.append("missing_3q_baseline")
            sug = sug + [
                "基础定妆包缺 ready 的 3/4 侧脸参考：补 `reference_atlas.base_views.three_quarter`（45°/三分之二侧脸）"
                "并出图标 ready——45° 是全员基础角，不再按近景占比或角色体量延后。"
            ]
        rec = {
            "character_id": cid, "name": c["name"], "form": c["form"],
            "scope": c.get("scope") or "",
            "signals": signals, "angle_tokens": sorted(agg["angle_tokens"]),
            "appears_in": agg["clips"], **scored, "suggestions": sug,
            "reference_gaps": reference_gaps,
        }
        if reentry:
            rec["recurrence_reentry"] = reentry
        if (
            rec["band"] == "high"
            and not bool(profile.get("persistent_subject"))
            and is_core_scope(str(c.get("scope") or ""), str(c.get("name") or ""))
            and rec.get("tier") in {"reference_group", "multi_reference", "native_unregistered"}
        ):
            pm = project_memory_mitigation(root, ep, default_backend, profile, signals)
            if bool(c.get("expression_ready")):
                rec["predicted_block_mitigated_by"] = "same_source_expression_refs"
                rec["suggestions"] = [
                    "已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考 + split_composite + full image_qc 回验，"
                    "不再因预测 high 在 preflight 阶段硬阻断。"
                ] + sug
            elif pm.get("ready"):
                rec["predicted_block_mitigated_by"] = "project_memory_reference_bundle"
                rec["project_memory_mitigation"] = pm
                rec["suggestions"] = [
                    "已写明项目记忆/真实参考图束路线：当前后端仍无持久主体 ID，但不再因这一点自动阻断。"
                    "后续必须先生成共享定妆和脸部锚，再让执行端把这些 PNG 作为真实图片入参传入，并以 full image_qc 回验。",
                    "注意：这不是官方服务端 subject_id；若 codex_reference_bundles 出现 actual image inputs=0、"
                    "missing_ready_refs 未清零或多人同框未按分层/反打执行，仍应在 image_preflight/image 阶段阻断。"
                ] + sug
            else:
                rec["band"] = "block"
                rec["project_memory_mitigation"] = pm
                rec["predicted_block_reason"] = (
                    f"核心/长线角色在 `{default_backend}` 这类无持久主体能力后端上预测 high，"
                    "且尚未写齐项目记忆/真实参考图束/分层合成/QC 执行计划。"
                )
                rec["suggestions"] = [
                    "⛔ 预测高危已升级为阻断：先切到持久主体后端，或写齐项目记忆路线"
                    "（真实参考图束/脸部锚/分层或反打/actual image input manifest/full QC），"
                    "也可补 face_embedding/主体库/LoRA/同源表情库后重跑 preflight。"
                ] + sug
        # ② 实测漂移回灌：上一集已**测**出该升 block 的跨集漂移 → 本集预测分直接 block（既成事实，非预测）
        measured = measured_drift_block(prior_drift, c.get("aliases") or set(), c["name"])
        if measured:
            rec["band"] = "block"
            rec["measured_drift"] = measured
            rec["suggestions"] = [
                "⛔ 上一集已实测跨集脸漂（" + measured_block_reason(measured)
                + "）：本集出图前先处置（重出漂移集 / 升原生主体或 LoRA），别带病续出——这是既成事实不是预测。"
            ] + sug
        results.append(rec)
    band_rank = {"block": 3, "high": 2, "medium": 1, "low": 0}
    results.sort(key=lambda r: (band_rank.get(r["band"], 0), r["score"]), reverse=True)
    return {
        "kind": "n2d_face_drift_risk", "version": 1, "root": str(root), "episode": ep,
        "default_backend": default_backend,
        "backend_profile": profile,
        "block": sum(1 for r in results if r["band"] == "block"),
        "high": sum(1 for r in results if r["band"] == "high"),
        "medium": sum(1 for r in results if r["band"] == "medium"),
        "missing_3q_baseline": sum(1 for r in results
                                   if "missing_3q_baseline" in r.get("reference_gaps", [])),
        "recurrence_reentries": sum(1 for r in results if r.get("recurrence_reentry")),
        "blocking": any(r["band"] == "block" for r in results),
        "prior_drift_available": bool(prior_drift.get("available")),
        "characters": results, "notes": notes,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    icon = {"block": "⛔", "high": "🔴", "medium": "🟡", "low": "🟢"}
    lines = [
        "# 出图前·脸漂风险分（事前预测 + 实测漂移回灌）",
        "",
        f"- episode: {report.get('episode')} · 默认后端: {report.get('default_backend')}",
        f"- ⛔ 阻断 {report.get('block', 0)} · 🔴 预测高危 {report.get('high', 0)} · 🟡 中危 {report.get('medium', 0)}"
        + (f" · ↩️ 长间隔再登场 {report.get('recurrence_reentries', 0)}" if report.get('recurrence_reentries') else ""),
        "",
        "| 角色 | 风险 | 分 | 锁脸档 | 主驱动 |",
        "|---|---|---|---|---|",
    ]
    for r in report.get("characters", []):
        drv = "；".join(f"{d['factor']}(+{d['points']})" for d in r.get("drivers", [])[:3])
        if r.get("measured_drift"):
            drv = "实测跨集漂移（既成事实）｜" + drv
        elif r.get("predicted_block_reason"):
            drv = "预测阻断（缺项目记忆/参考图束执行计划）｜" + drv
        lines.append(f"| {r['name']}（{r['character_id']}/{r['form']}） | {icon.get(r['band'],'?')} {r['band']} "
                     f"| {r['score']} | {r['tier']} | {drv} |")
    lines.append("")
    for r in report.get("characters", []):
        if r["band"] == "low" or not r.get("suggestions"):
            continue
        lines.append(f"## {icon.get(r['band'])} {r['name']}（{r['character_id']}/{r['form']}）· 分 {r['score']}")
        for s in r["suggestions"]:
            lines.append(f"- {s}")
        lines.append("")
    for n in report.get("notes", []):
        lines.append(f"- note: {n}")
    lines.append("")
    lines.append("说明：🔴/🟡 是**出图前预测**（按建议提前加强参考/建表情库/上 LoRA）；⛔ 包含两类："
                 "n2d-identity 对已出图集**实测**到的跨集漂移回灌，或核心长线角在无持久主体后端上"
                 "预测 high 且缺项目记忆/真实参考图束/分层合成/QC 执行计划。前者先处置漂移，后者先补执行计划或升档。"
                 + ("（本次无可用实测数据：identity_drift_report 缺失或无 insightface，仅预测档生效。）"
                    if not report.get("prior_drift_available") else ""))
    return "\n".join(lines) + "\n"


def run(root: Path, ep: str) -> Dict[str, Any]:
    report = analyze(root, ep)
    out_dir = root / "生产数据"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"face_drift_risk_{ep}.json"
    md_path = out_dir / f"face_drift_risk_{ep}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    report["json_path"] = str(json_path)
    report["markdown_path"] = str(md_path)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true", help="打印机器可读 report")
    ns = ap.parse_args(argv)
    report = run(Path(ns.root).expanduser().resolve(), ns.episode)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    icon = {"block": "⛔", "high": "🔴", "medium": "🟡", "low": "🟢"}
    print(f"出图前脸漂风险（{ns.episode}·后端 {report['default_backend']}）："
          f"⛔ {report.get('block', 0)} · 🔴 {report['high']} · 🟡 {report['medium']}")
    for r in report["characters"]:
        if r["band"] == "low":
            continue
        print(f"  {icon.get(r['band'])} {r['name']}（{r['character_id']}/{r['form']}）分 {r['score']}·{r['tier']}")
        for s in r["suggestions"]:
            print(f"     - {s}")
    for n in report["notes"]:
        print("ℹ️ " + n)
    print(f"→ {report['markdown_path']}")
    # 实测漂移 → 非零退出，让 SOP / gate 能据此卡住"带病续出图"
    return 2 if report.get("blocking") else 0


if __name__ == "__main__":
    raise SystemExit(main())
