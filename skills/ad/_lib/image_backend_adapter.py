#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 出图侧·图片后端身份能力表（一致性梯子的机器消费方）。

为什么存在：
    `ad-image/SKILL.md` 写了「一致性梯子：①参考图派生 → ②后端原生主体ID/主体库 → ③LoRA」，
    但 ad 线此前**没有图片侧能力表**——梯子只是散文，没有任何脚本能回答「当前 `生图模型`
    到底够得着哪一档」。于是 `plan_prompts.py` 只能把 registry 里静态登记的 reference_images
    原样列出，产品镜该喂几张、要不要升档，全靠人记。本表把「后端 → 能力」落成单一真值源。

治什么根因：
    对**后端品牌字串**分支（`if backend == "kling"`）会让每个消费方各抄一份后端知识，换厂就
    满仓库改。照 `ad-video/scripts/route.py` 的做法：后端按 **CAP_\\* 能力**登记，调用方问能力
    不问品牌——换厂只改本表，判型/处方逻辑一行不动。

诚实边界（**本文件最重要的部分**）：
    - 能力是**三态**：available / unknown / unavailable。厂商没有公开证据的能力一律标
      `unknown`，**绝不猜 True**。`has_capability()` 只认 available——未知即不可用于路由决策，
      但会在报告里显性写「未知」而不是伪装成「不支持」。
    - Codex / OpenAI(GPT Image 2) **没有可注册的持久主体库**。本表据此把 subject_library
      标 unavailable，梯子封顶在「指定参考图」档——这是 ad 线默认路线的真实天花板。

档位口径：
    梯子四档与用户可见契约 `skills/ad/ad-craft/references/选择点与偏好.md` 的选择点
    `一致性增强`（共享定妆+锚点 | 指定参考图 | 后端主体库 | +LoRA）**一一对齐**，不另造档名。
    - 未知后端 → 保守 profile（只有 reference、参考预算 1）+ `known=False`。**绝不假装支持**。
    - 参考预算是**内部启发式上限**（`provenance` 字段标注），不是厂商 API 文档承诺；真实上限
      以渠道 CLI/API 当次返回为准。

用法：
    from image_backend_adapter import profile_for, has_capability, lock_tier_for, CAP_SUBJECT_LIBRARY
    profile = profile_for("GPT Image 2", "Codex CLI")   # → dict（可直接塞进 JSON 报告）
    lock_tier_for(profile, "product")                   # → "directed_reference"（= 一致性增强·指定参考图）
    seed_capability(profile)                            # → seed 控制三态（available/unknown/unavailable）
    backends_reaching_tier("subject_library", "product")  # → 够得着该档的后端清单（升档建议路由）

测试（从本目录跑）：
    cd skills/ad/_lib && python3 -m pytest test_image_backend_adapter.py
"""
from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Union

# ── 能力常量（图片侧身份相关子集·换厂只改本文件） ────────────────────────────────
CAP_REFERENCE = "reference"                  # 吃单张参考图做 image-to-image / 图生图（梯子第①档地板）
CAP_MULTI_REFERENCE = "multi_reference"      # 一次吃多张参考图（正/侧/细节/logo 特写同时喂）
CAP_SUBJECT_LIBRARY = "subject_library"      # 后端原生**持久**主体/角色库：注册一次按 ID 引用（梯子第②档）
CAP_FACE_EMBEDDING = "face_embedding"        # 人脸嵌入/faceid（只对代言人有意义，对产品包装无意义）
CAP_LORA = "lora"                            # 可挂 LoRA / 微调权重（梯子第③档）
CAP_CONTROLNET = "controlnet"                # 结构/边缘/深度控制网（锁包装轮廓、锁构图）
CAP_MASK_INPAINT = "mask_inpaint"            # 带 mask 的局部重绘（logo 保护区）
# seed 控制：调用方能否把**固定随机种子**传给后端并真实生效（重抽单镜/跨镜复用同一产品
# 时锁随机起点）。seed 不是身份锁，只是可复现起点；判定证据只认**仓内该渠道的真实调用
# 方式/落档口径**——查不到证据一律 unknown，绝不猜 available。
CAP_SEED_CONTROL = "seed_control"

ALL_CAPABILITIES: Tuple[str, ...] = (
    CAP_REFERENCE, CAP_MULTI_REFERENCE, CAP_SUBJECT_LIBRARY, CAP_FACE_EMBEDDING,
    CAP_LORA, CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL,
)

# 能力三态。unknown 是**诚实位**：厂商没给公开证据 → 既不敢用，也不谎称不支持。
CAP_AVAILABLE = "available"
CAP_UNKNOWN = "unknown"
CAP_UNAVAILABLE = "unavailable"

# ── 一致性梯子档位（**必须与用户可见的既有契约对齐，不另造档名**） ─────────────────
# 单一真值源：`skills/ad/ad-craft/references/选择点与偏好.md` 的选择点
#   `一致性增强`: 共享定妆+锚点 | 指定参考图 | 后端主体库 | +LoRA（默认 共享定妆+锚点）
# 与 `ad-image/SKILL.md`「一致性梯子」的 ①参考图派生 → ②后端原生主体ID → ③LoRA 是同一把梯子：
#   ① = 共享定妆+锚点 / 指定参考图（两档都属"参考图派生"，后者是逐镜精选、更强）
#   ② = 后端主体库
#   ③ = +LoRA
# 这里只给它们机器可读的 id，档名/档数**一一对应**用户看到的四档——用户在 `_设置.md` 里选的
# 是哪档，报告里说的就是哪档，不引入第五个用户不认识的档。
TIER_SHARED_KIT = "shared_kit_anchor"        # 共享定妆+锚点（默认地板档）
TIER_DIRECTED_REFERENCE = "directed_reference"  # 指定参考图（逐镜精选多参考）
TIER_SUBJECT_LIBRARY = "subject_library"     # 后端主体库（注册一次按 ID 引用）
TIER_LORA = "lora"                           # +LoRA（SKILL.md：仅核心长线代言人）

TIER_LADDER: Tuple[str, ...] = (
    TIER_SHARED_KIT, TIER_DIRECTED_REFERENCE, TIER_SUBJECT_LIBRARY, TIER_LORA,
)
# 档位 ↔ 用户可见的 `一致性增强` 取值（报告/找人说话时用这个词，别用内部 id）。
TIER_SETTING_VALUE: Dict[str, str] = {
    TIER_SHARED_KIT: "共享定妆+锚点",
    TIER_DIRECTED_REFERENCE: "指定参考图",
    TIER_SUBJECT_LIBRARY: "后端主体库",
    TIER_LORA: "+LoRA",
}
# 档位 → 该档需要的能力（地板档 共享定妆+锚点 = 单图 i2i + 锚点句，无条件成立）。
# 注意 CAP_FACE_EMBEDDING **不是一档**：它是能强化"指定参考图/后端主体库"两档的能力，
# 用户契约里没有这一档，就不在梯子上另立一档。
TIER_CAPABILITY: Dict[str, Optional[str]] = {
    TIER_SHARED_KIT: None,
    TIER_DIRECTED_REFERENCE: CAP_MULTI_REFERENCE,
    TIER_SUBJECT_LIBRARY: CAP_SUBJECT_LIBRARY,
    TIER_LORA: CAP_LORA,
}
# 只对「人」成立的档位：ad-image/SKILL.md 明确「③LoRA（仅核心长线代言人）」——
# 不能拿 LoRA 当产品包装的锁来给产品镜升档。
CHARACTER_ONLY_TIERS: Tuple[str, ...] = (TIER_LORA,)

# ── 资产类型（按 storyboard/registry 的 ID 前缀，与 product_qc 的 PROD_/BRAND_ 同口径） ──
ASSET_KIND_PRODUCT = "product"
ASSET_KIND_BRAND = "brand"
ASSET_KIND_CHARACTER = "character"
ASSET_KIND_LOCATION = "location"
ASSET_KIND_PROP = "prop"
ASSET_KIND_UNKNOWN = "unknown"

_ASSET_PREFIX_KIND: Tuple[Tuple[str, str], ...] = (
    ("PROD_", ASSET_KIND_PRODUCT),
    ("BRAND_", ASSET_KIND_BRAND),
    ("CHAR_", ASSET_KIND_CHARACTER),
    ("LOC_", ASSET_KIND_LOCATION),
    ("PROP_", ASSET_KIND_PROP),
)

# ── 参考预算上限（**内部启发式**，非厂商承诺） ──────────────────────────────────
# provenance: internal-heuristic·confidence=low
# 口径：这是「构造 job 时最多喂几张参考图」的保守上限，不代表某渠道 runner 已装好。
# 真实上限以渠道 CLI/API 当次返回为准；未知后端故意压到 1（宁可报「参考不足」也不臆造预算）。
UNKNOWN_BACKEND_REFERENCE_LIMIT = 1

_PROVENANCE = "internal-heuristic·confidence=low"


def _profile(backend: str, label: str, *, available: Sequence[str], unknown: Sequence[str],
             reference_limit: int, notes: str, known: bool = True) -> Dict[str, Any]:
    """把「可用/未知」两张清单铺成全能力三态表；没点名的能力 = unavailable（明确不支持）。"""
    caps: Dict[str, str] = {}
    for cap in ALL_CAPABILITIES:
        if cap in available:
            caps[cap] = CAP_AVAILABLE
        elif cap in unknown:
            caps[cap] = CAP_UNKNOWN
        else:
            caps[cap] = CAP_UNAVAILABLE
    return {
        "backend": backend,
        "label": label,
        "known": known,
        "capabilities": caps,
        "reference_limit": int(reference_limit),
        "notes": notes,
        "provenance": _PROVENANCE,
    }


# ── 后端能力档表（单一真值源·换厂只改这里） ──────────────────────────────────────
IMAGE_BACKEND_PROFILES: Dict[str, Dict[str, Any]] = {
    # ad 线默认路线（生图模型=GPT Image 2 / 生图渠道=Codex CLI 或 OpenAI Images API）。
    # 诚实点：**无持久主体库**，所以梯子在这条默认路线上封顶 multi_reference，
    # 产品身份只能靠「多张真实参考图 + 身份锁定句」硬堆，这正是产品镜必须多喂参考的原因。
    "openai": _profile(
        "openai", "GPT Image 2（Codex CLI / OpenAI Images API）",
        available=(CAP_REFERENCE, CAP_MULTI_REFERENCE, CAP_MASK_INPAINT),
        unknown=(CAP_CONTROLNET,),
        reference_limit=5,  # 观测到的 Codex image_generation 附件天花板；非文档承诺。
        notes="官方图生图/多参考可用；无可注册的持久主体 ID，产品/代言人只能走多参考兜底；无 LoRA 挂载点。"
              "seed 控制 unavailable：兄弟线 Codex 渠道 runner 已落档 no-seed-api 降级口径，"
              "官方 Images API 公开参数亦无 seed——planned_seed 在此路线只作 provenance 记录，不假装生效。",
    ),
    "gemini": _profile(
        "gemini", "Nano Banana Pro / Gemini 3 Pro Image（Google Gemini API）",
        available=(CAP_REFERENCE, CAP_MULTI_REFERENCE),
        unknown=(CAP_SUBJECT_LIBRARY, CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL),
        reference_limit=5,
        notes="多模态多参考可用；是否有可注册持久主体未取得公开证据 → 标 unknown，不据此升档。"
              "seed 控制：仓内无该渠道传 seed 的调用证据 → unknown。",
    ),
    "seedream": _profile(
        "seedream", "Seedream 4.5（BytePlus ModelArk API）",
        available=(CAP_REFERENCE, CAP_MULTI_REFERENCE, CAP_SUBJECT_LIBRARY),
        unknown=(CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL),
        reference_limit=4,
        notes="universal reference / 主体引用可按 ID 复用（梯子第②档）；LoRA 无官方挂载点。"
              "seed 控制：仓内无该渠道传 seed 的调用证据 → unknown。",
    ),
    "kling": _profile(
        "kling", "Kling Image 3.0（Kling API）",
        available=(CAP_REFERENCE, CAP_MULTI_REFERENCE, CAP_SUBJECT_LIBRARY),
        unknown=(CAP_FACE_EMBEDDING, CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL),
        reference_limit=4,
        notes="原生主体/角色库可注册后按 ID 引用（梯子第②档）；脸嵌入是否独立可用未确证 → unknown。"
              "seed 控制：仓内无该渠道传 seed 的调用证据 → unknown。",
    ),
    # 即梦：ad 线**禁逆向路径**（见 ad-image/SKILL.md 生图后端治理）；此档只描述其官方图生图
    # 能力，登记在表里是为了让路由诚实回答「它够不着第②档」，不构成放行任何路径。
    "dreamina": _profile(
        "dreamina", "即梦 Dreamina Image（官方版本，需单项目签核）",
        available=(CAP_REFERENCE, CAP_MULTI_REFERENCE),
        unknown=(CAP_SUBJECT_LIBRARY, CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL),
        reference_limit=4,
        notes="官方图生图/多参考可用；持久主体未确证 → unknown。逆向/未授权即梦路径在 ad 线永久禁用。"
              "seed 控制：ad 线官方 CLI 调用未暴露 seed 旗标，兄弟线 runner 落档口径为"
              "「unsupported_or_unknown」→ 如实标 unknown。",
    ),
}

# 后端名归一：**模型**字串优先，其次渠道字串（防止 `生图渠道=Codex CLI` 把
# `生图模型=Seedream 4.5` 误判成 openai）。换厂只改这张别名表 + 上面的档表。
_BACKEND_TOKENS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("openai", ("gptimage", "gpt-image", "openai", "codex", "chatgpt", "dalle", "sora")),
    ("gemini", ("gemini", "nanobanana", "nano-banana")),
    ("seedream", ("seedream", "byteplus", "modelark")),
    ("kling", ("kling", "可灵")),
    ("dreamina", ("dreamina", "即梦", "jimeng")),
)


def _norm(value: Any) -> str:
    return re.sub(r"[\s/_.]+", "", str(value or "")).lower()


def _match_backend(text: str) -> str:
    key = _norm(text)
    if not key:
        return ""
    for backend, tokens in _BACKEND_TOKENS:
        if any(_norm(token) in key for token in tokens):
            return backend
    return ""


def normalize_backend(model: str, channel: str = "") -> str:
    """(生图模型, 生图渠道) → 档表 key；认不出返回 ""（**不给默认值**，由 profile_for 保守兜底）。

    模型优先：模型是「由什么生成」，渠道只是访问入口（见 选择点与偏好.md `生图模型`/`生图渠道`）。
    纯函数·可测。
    """
    return _match_backend(model) or _match_backend(channel)


def unknown_profile(model: str = "", channel: str = "") -> Dict[str, Any]:
    """未知/自定义后端的保守 profile：只有 reference，其余全 unknown，预算压到 1，`known=False`。

    绝不假装支持：调用方看到 known=False 应显式降级报告，而不是按「大概能多参考」下计划。
    """
    raw = " ".join(x for x in (str(model or "").strip(), str(channel or "").strip()) if x)
    profile = _profile(
        "unknown", f"未登记后端（{raw or '未声明'}）",
        available=(CAP_REFERENCE,),
        unknown=(CAP_MULTI_REFERENCE, CAP_SUBJECT_LIBRARY, CAP_FACE_EMBEDDING,
                 CAP_LORA, CAP_CONTROLNET, CAP_MASK_INPAINT, CAP_SEED_CONTROL),
        reference_limit=UNKNOWN_BACKEND_REFERENCE_LIMIT,
        notes="后端未登记在 IMAGE_BACKEND_PROFILES：只假定最基本的单张图生图，参考预算按最保守 1 张算；"
              "要按真实能力规划请先把该后端登记进能力档表。",
        known=False,
    )
    profile["requested_model"] = str(model or "")
    profile["requested_channel"] = str(channel or "")
    return profile


def profile_for(model: str, channel: str = "") -> Dict[str, Any]:
    """(生图模型, 生图渠道) → 能力 profile（dict·可直接嵌进 JSON 报告）。

    认不出的后端 → `unknown_profile()`（保守 + known=False），**不抛异常、不猜能力**。
    """
    backend = normalize_backend(model, channel)
    if not backend:
        return unknown_profile(model, channel)
    profile = dict(IMAGE_BACKEND_PROFILES[backend])
    profile["capabilities"] = dict(profile["capabilities"])
    profile["requested_model"] = str(model or "")
    profile["requested_channel"] = str(channel or "")
    return profile


ProfileLike = Union[str, Mapping[str, Any]]


def _as_profile(value: ProfileLike) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return profile_for(str(value))


def capability_state(profile: ProfileLike, capability: str) -> str:
    """能力三态查询：available / unknown / unavailable。纯函数·可测。"""
    caps = _as_profile(profile).get("capabilities") or {}
    return str(caps.get(capability, CAP_UNKNOWN))


def has_capability(profile: ProfileLike, capability: str) -> bool:
    """**只认 available**。unknown 一律当不可用于决策——但调用方应把「未知」写进报告，
    而不是悄悄按「不支持」处理（这两者对人的下一步动作完全不同）。"""
    return capability_state(profile, capability) == CAP_AVAILABLE


def reference_limit_for(profile: ProfileLike) -> int:
    """该后端一次最多喂几张参考图（内部启发式上限；未知后端 = 1）。"""
    limit = _as_profile(profile).get("reference_limit")
    try:
        return max(1, int(limit))
    except (TypeError, ValueError):
        return UNKNOWN_BACKEND_REFERENCE_LIMIT


def asset_kind_for_id(asset_id: str) -> str:
    """资产 ID → 类型（PROD_/BRAND_/CHAR_/LOC_/PROP_）。认不出 → unknown。纯函数·可测。"""
    raw = str(asset_id or "").strip()
    for prefix, kind in _ASSET_PREFIX_KIND:
        if raw.startswith(prefix):
            return kind
    return ASSET_KIND_UNKNOWN


def tier_rank(tier: str) -> int:
    """档位序（越大越强）。不认识的档位 → -1。纯函数·可测。"""
    try:
        return TIER_LADDER.index(str(tier))
    except ValueError:
        return -1


def tier_setting_value(tier: str) -> str:
    """档位 id → 用户在 `_设置.md` 里看到的 `一致性增强` 取值。纯函数·可测。"""
    return TIER_SETTING_VALUE.get(str(tier), str(tier))


def tier_for_setting(value: str) -> Optional[str]:
    """`一致性增强` 取值 → 档位 id。认不出返回 None（不猜）。纯函数·可测。"""
    raw = _norm(value)
    if not raw:
        return None
    for tier, label in TIER_SETTING_VALUE.items():
        if _norm(label) in raw:
            return tier
    return None


def lock_tier_for(backend: ProfileLike, asset_kind: str = ASSET_KIND_UNKNOWN) -> str:
    """按后端能力返回该类资产**可达的最高档**（一致性梯子·四档与 `一致性增强` 对齐）。纯函数·可测。

    - 地板永远是 `共享定妆+锚点`：连未知后端也假定能吃一张图 + 锚点句
      （这是 ad 线「绝不文生图产品」的底线）。
    - `+LoRA` 只对 character 成立——SKILL.md 写死「仅核心长线代言人」，不给产品包装升这档。
    - 只有 available 的能力才算数；unknown 不升档（诚实边界）。
    """
    profile = _as_profile(backend)
    kind = str(asset_kind or ASSET_KIND_UNKNOWN)
    best = TIER_SHARED_KIT
    for tier in TIER_LADDER:
        capability = TIER_CAPABILITY.get(tier)
        if capability is None:
            continue
        if tier in CHARACTER_ONLY_TIERS and kind != ASSET_KIND_CHARACTER:
            continue
        if has_capability(profile, capability):
            best = tier
    return best


def seed_capability(profile: ProfileLike) -> str:
    """seed 控制能力三态查询：available / unknown / unavailable。纯函数·可测。

    规划端（plan_prompts）无论后端是否支持都会生成确定性 planned_seed，并把本三态
    一并写进 manifest——「记录了 seed」≠「seed 生效了」，渲染端与 provenance 据此判断。
    """
    return capability_state(profile, CAP_SEED_CONTROL)


def backends_reaching_tier(tier: str, asset_kind: str = ASSET_KIND_UNKNOWN) -> list:
    """能力表里对该类资产**够得着指定档位**的后端清单（[{backend, label}, ...]）。

    供升档建议路由用：建议档超出当前后端能力时，如实列出「哪些登记后端够得着」——
    仅 advisory 建议切换素材，不自动改设置；只认 available（unknown 不算够得着）。
    档位不认识 → 空清单（不猜）。纯函数·可测。
    """
    if tier_rank(tier) < 0:
        return []
    out = []
    for key, profile in IMAGE_BACKEND_PROFILES.items():
        if tier_rank(lock_tier_for(profile, asset_kind)) >= tier_rank(tier):
            out.append({"backend": key, "label": str(profile.get("label"))})
    return out


def unknown_capabilities(profile: ProfileLike) -> list:
    """该 profile 里状态为 unknown 的能力（供报告显性降级，不静默）。"""
    caps = _as_profile(profile).get("capabilities") or {}
    return sorted(cap for cap, state in caps.items() if state == CAP_UNKNOWN)


def describe(profile: ProfileLike) -> str:
    """一行人读摘要（给 markdown 报告用）。"""
    p = _as_profile(profile)
    available = sorted(cap for cap, state in (p.get("capabilities") or {}).items()
                       if state == CAP_AVAILABLE)
    return (f"{p.get('label')}（known={str(p.get('known')).lower()}·参考上限 "
            f"{reference_limit_for(p)}·可用能力 {', '.join(available) or '无'}）")
