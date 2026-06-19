"""image_lock_tier 档位梯子单测——含 P2a face_embedding 中间档 + 向后兼容。

从本目录跑：
  cd skills/n2d/_lib && python3 -m pytest test_lock_tier.py
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
lt = importlib.import_module("n2d_logic")


def test_lora_is_strongest():
    assert lt.image_lock_tier("codex", {}, {"status": "ready"}) == "lora"
    assert lt.image_lock_tier("seedream", {}, {"status": "training"}) == "lora"


def test_backward_compat_without_face_embedding():
    # 无 face_embedding adapter → 行为与改动前一致
    assert lt.image_lock_tier("codex", {}, {}) == "multi_reference"   # codex 多参考无持久主体
    assert lt.image_lock_tier("seedream", {}, {}) == "native_unregistered"  # 有持久能力未注册
    assert lt.image_lock_tier("seedream", {"seedream": {"status": "ready"}}, {}) == "native_subject"


def test_face_embedding_rung_on_non_persistent_backend():
    # 无持久主体后端(codex) 挂了 ready 的脸嵌入锁 → face_embedding（强于 multi_reference）
    adapters = {"face_embedding": {"status": "ready", "type": "ip_adapter_faceid"}}
    assert lt.image_lock_tier("codex", adapters, {}) == "face_embedding"
    # 字符串形态 status 也认
    assert lt.image_lock_tier("codex", {"face_embedding": "registered"}, {}) == "face_embedding"
    # 未就绪(planned) → 不算，回落 multi_reference
    assert lt.image_lock_tier("codex", {"face_embedding": {"status": "planned"}}, {}) == "multi_reference"


def test_face_embedding_below_native_subject():
    # 持久后端已注册原生主体 → native_subject 优先（强于 face_embedding）
    adapters = {"seedream": {"status": "ready"}, "face_embedding": {"status": "ready"}}
    assert lt.image_lock_tier("seedream", adapters, {}) == "native_subject"
    # 持久后端未注册但挂了 face_embedding → face_embedding（真锁 > 仅潜在能力的 native_unregistered）
    adapters2 = {"face_embedding": {"status": "ready"}}
    assert lt.image_lock_tier("seedream", adapters2, {}) == "face_embedding"


def test_lora_beats_face_embedding():
    adapters = {"face_embedding": {"status": "ready"}}
    assert lt.image_lock_tier("codex", adapters, {"status": "ready"}) == "lora"
