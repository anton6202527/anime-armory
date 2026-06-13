#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配音/TTS 后端注册表（跨线管道 · 纯标准库 · 无网络调用）。

这是「配音后端」选择点的**候选快照 + 适配层**单一真值源。此前各线（n2d-voice /
ad-voice）各自把后端优先级 + env 名硬编在 render 脚本里，新增一个零样本后端要改两处、
易漂。本表把「有哪些后端、各自靠哪个 env 探测、优先级、能力、是否克隆真人嗓需授权」
收敛到一处；render 脚本只 import 优先级 spec 与归一函数，不再各抄一份。

为何放 common/ 而非某条线：这是纯**管道注册**（env 名/优先级/能力标签），不含某条线
的业务语义；授权闸门（克隆真人嗓需 VOICE_CLONE_AUTHORIZED=1）仍由各线 voice skill
自己执行——见 `skills/n2d/references/选择点与偏好.md` common/ 判据：删掉后各线表现一致 → 进 common/。

戳记：催 本线 _lib/refresh.py 按需核验后端是否新增/改名/改 env。
采集日期：2026-06-13  来源：n2d-voice/render_voice.py 现行优先级 + 各后端官方文档（待逐条复核）
"""
from __future__ import annotations

from typing import Dict, List, Optional


CATALOG_VERIFIED = {"date": "2026-06-13", "source": "n2d-voice 现行优先级 + 各后端官方文档(待复核)"}

# tier: 后端档位，决定取用优先级。
#   zero_shot 本地零样本克隆 > cloud_clone 云端 > placeholder 占位。
# env: 探测该后端是否可用的环境变量（URL 或 API key）。
# clone_capable: 是否能克隆指定嗓（→ 触发授权闸门，由 voice skill 执行，非本表）。
# 同 tier 内按列出顺序取第一个 env 命中的。
VOICE_BACKEND_SPECS: List[Dict[str, object]] = [
    {"key": "cosyvoice", "label": "CosyVoice", "tier": "zero_shot",
     "env": "COSYVOICE_URL", "ref_prefix": "COSY", "timeout": 120, "clone_capable": True},
    {"key": "fishspeech", "label": "FishSpeech", "tier": "zero_shot",
     "env": "FISHSPEECH_URL", "ref_prefix": "FISH", "timeout": 300, "clone_capable": True},
    {"key": "gptsovits", "label": "GPT-SoVITS", "tier": "zero_shot",
     "env": "GPTSOVITS_URL", "ref_prefix": "GSV", "timeout": 300, "clone_capable": True},
    {"key": "indextts", "label": "IndexTTS-2", "tier": "zero_shot",
     "env": "INDEXTTS_URL", "ref_prefix": "IDX", "timeout": 300, "clone_capable": True},
    {"key": "voxcpm", "label": "VoxCPM2", "tier": "zero_shot",
     "env": "VOXCPM_URL", "ref_prefix": "VOX", "timeout": 300, "clone_capable": True},
    {"key": "minimax", "label": "MiniMax", "tier": "cloud_clone",
     "env": "MINIMAX_API_KEY", "ref_prefix": None, "timeout": 120, "clone_capable": True},
    {"key": "volcano", "label": "火山/豆包 TTS", "tier": "cloud_clone",
     "env": "VOLC_APPID", "ref_prefix": None, "timeout": 120, "clone_capable": True},
    {"key": "say", "label": "macOS say（占位/应急）", "tier": "placeholder",
     "env": None, "ref_prefix": None, "timeout": 60, "clone_capable": False},
]

_TIER_ORDER = {"zero_shot": 0, "cloud_clone": 1, "placeholder": 2}

# 别名 → canonical key（手输归一）
_ALIASES = {
    "cosyvoice": "cosyvoice", "cosy": "cosyvoice",
    "fishspeech": "fishspeech", "fish-speech": "fishspeech", "fish": "fishspeech",
    "gpt-sovits": "gptsovits", "gptsovits": "gptsovits", "sovits": "gptsovits",
    "indextts": "indextts", "indextts-2": "indextts", "index-tts": "indextts",
    "voxcpm": "voxcpm", "voxcpm2": "voxcpm",
    "minimax": "minimax",
    "volcano": "volcano", "volc": "volcano", "火山": "volcano", "豆包": "volcano",
    "say": "say", "macos say": "say", "占位": "say",
}


def normalize_voice_backend(raw: Optional[str]) -> str:
    """手输配音后端字面值 → canonical key；未知返回 ""（调用方走 unknown 提示，不硬拦）。"""
    text = (raw or "").strip().lower()
    if not text:
        return ""
    for alias in sorted(_ALIASES, key=len, reverse=True):
        if alias in text:
            return _ALIASES[alias]
    return ""


def spec_by_key(key: str) -> Optional[Dict[str, object]]:
    for s in VOICE_BACKEND_SPECS:
        if s["key"] == key:
            return dict(s)
    return None


def zero_shot_specs() -> List[Dict[str, object]]:
    """零样本克隆后端，按优先级。供 render_voice 的 ZS_SPECS 取用。"""
    return [dict(s) for s in VOICE_BACKEND_SPECS if s["tier"] == "zero_shot"]


def zs_specs_legacy() -> List[tuple]:
    """render_voice.py 历史 ZS_SPECS 形状：(URL_env, ref_prefix, label, timeout)。

    抽到此处后 render_voice 直接 import 本函数，不再内联硬编一份。
    """
    return [(s["env"], s["ref_prefix"], s["label"], s["timeout"]) for s in zero_shot_specs()]


def priority_order() -> List[str]:
    """全部后端按 (tier, 列出顺序) 排出的取用优先级 key 列表。"""
    indexed = list(enumerate(VOICE_BACKEND_SPECS))
    indexed.sort(key=lambda iv: (_TIER_ORDER.get(str(iv[1]["tier"]), 9), iv[0]))
    return [str(s["key"]) for _, s in indexed]


if __name__ == "__main__":
    import json
    print(json.dumps({
        "verified": CATALOG_VERIFIED,
        "priority": priority_order(),
        "specs": VOICE_BACKEND_SPECS,
    }, ensure_ascii=False, indent=2))
