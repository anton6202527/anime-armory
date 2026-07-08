#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排器 prework 的「输入指纹缓存 + 顺序保持的并行执行」（本线 · 纯标准库）。

背景：`skills/n2d/run.py` 的 `gather_probes` 在每次 `run next` 到 image_prompt 前沿时，
串行 subprocess 调用 ~15+ 个独立审计脚本，每个都冷启动 Python + 重 import 整个 `_lib`，
拿一张动作卡要几十秒到几分钟。这些审计**互相独立**，且在输入未变时结果不变。

本模块提供两件正交的能力，让 run.py 在不改变任何决策语义的前提下提速：

1. **输入指纹**（`episode_input_fingerprint`）：把"本集脚本/分镜/设置 + 审计脚本自身"
   哈希成一个摘要。脚本或输入一变，摘要就变 → 缓存自动失效（粗粒度但永不复用陈旧结果，
   宁可偶尔多跑一次也不放过变更）。

2. **缓存感知的顺序保持并行**（`run_cached_parallel`）：把一组独立 step 的**执行**丢进线程池
   并发跑（subprocess 是 I/O-bound，线程池有效），但**按声明顺序回填结果**——这样
   "第一个失败的 step 决定 prework_block" 这类顺序敏感语义与串行版逐字一致，只是更快；
   命中缓存的 step 直接跳过 subprocess，复用上次结果。

设计约束：best-effort——任何缓存读写/哈希异常都退化成"照常串行/并行跑、不缓存"，
绝不让缓存层把编排器搞崩。可用 env `N2D_PREWORK_NOCACHE=1` 全局关闭缓存。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import sysconfig
from pathlib import Path


def _ensure_stdlib_queue_module() -> None:
    """Guard ThreadPoolExecutor against repo-local queue.py shadowing stdlib."""
    stdlib_queue = Path(sysconfig.get_path("stdlib")) / "queue.py"
    current = sys.modules.get("queue")
    current_file = Path(getattr(current, "__file__", "") or "") if current is not None else None
    if current is not None and current_file == stdlib_queue:
        return
    spec = importlib.util.spec_from_file_location("queue", stdlib_queue)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules["queue"] = module
    spec.loader.exec_module(module)


_ensure_stdlib_queue_module()
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# 默认并发度：subprocess 是 I/O/进程启动密集型，给一个温和上限即可；可用 env 覆盖。
DEFAULT_MAX_WORKERS = int(os.environ.get("N2D_PREWORK_WORKERS", "8") or "8")

# 每集参与指纹的"主输入"相对路径（存在才计入；缺失不报错）。
# 这些是 image_prompt 前沿审计真正读的源：台词 / 分镜 / 设置 / 角色场景卡 / 视觉契约种子。
_EPISODE_INPUT_RELPATHS = (
    "voiceover.txt",
    "storyboard.json",
    "故事板.md",
    "素材清单.md",
)
_ROOT_INPUT_RELPATHS = (
    "_设置.md",
    "_进度.md",
)


def _lib_contract_module_paths() -> list:
    """本目录（n2d/_lib）下的共享契约模块 *.py——审计脚本都 import 它们，改了会改审计行为。

    历史 bug：指纹只含审计脚本自身 mtime，不含 _lib；改 n2d_const/n2d_schema 等共享契约时，
    审计行为变了、指纹却没变 → 缓存吐**陈旧**结果。把 _lib 契约模块 mtime 纳入指纹修掉它
    （多失效=安全方向；生产态 _lib 稳定 → 仍命中，不伤吞吐）。排除 test_/__pycache__。"""
    import glob as _glob
    here = os.path.dirname(os.path.abspath(__file__))
    out = []
    for p in _glob.glob(os.path.join(here, "*.py")):
        base = os.path.basename(p)
        if base.startswith("test_") or base == "prework_cache.py":
            continue
        out.append(p)
    return sorted(out)


def cache_disabled() -> bool:
    return str(os.environ.get("N2D_PREWORK_NOCACHE", "")).strip() not in ("", "0", "false", "False")


def _hash_file_content(path: str, h: "hashlib._Hash") -> None:
    try:
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                h.update(chunk)
    except OSError:
        h.update(b"\0missing\0")


def _hash_file_stat(path: str, h: "hashlib._Hash") -> None:
    """只把 (size, mtime_ns) 计入——审计脚本可能很多很大，按内容哈希太贵；
    脚本一改 mtime 就变，足以让缓存失效。"""
    try:
        st = os.stat(path)
        h.update(f"{path}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8"))
    except OSError:
        h.update(f"{path}:missing".encode("utf-8"))


def episode_input_fingerprint(root: str, ep: str, script_paths: Sequence[str] = ()) -> str:
    """本集 prework 输入指纹：主输入文件内容 + 参与审计脚本的 (size,mtime)。

    任一变化都改变指纹，从而让缓存失效。纯函数式（只读盘），永不抛。
    """
    h = hashlib.sha256()
    h.update(f"v1|{ep}|".encode("utf-8"))
    ep_dir = os.path.join(root, "脚本", ep)
    for rel in _EPISODE_INPUT_RELPATHS:
        h.update(f"|{rel}|".encode("utf-8"))
        _hash_file_content(os.path.join(ep_dir, rel), h)
    for rel in _ROOT_INPUT_RELPATHS:
        h.update(f"|{rel}|".encode("utf-8"))
        _hash_file_content(os.path.join(root, rel), h)
    for sp in sorted(set(script_paths)):
        h.update(b"|script|")
        _hash_file_stat(sp, h)
    # 共享 _lib 契约模块（n2d_const/n2d_schema/n2d_contract…）：审计脚本 import 它们，
    # 改了会改审计行为——纳入指纹，避免共享契约一改、缓存仍吐陈旧审计结果。
    for lp in _lib_contract_module_paths():
        h.update(b"|lib|")
        _hash_file_stat(lp, h)
    return h.hexdigest()


def cache_path(root: str, ep: str, stage_key: str) -> str:
    return os.path.join(root, "生产数据", f".prework_cache_{ep}_{stage_key}.json")


def load_cache(path: str) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(path: str, data: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass  # best-effort：缓存写不下不影响主流程


class PreworkCache:
    """单个 (root, ep, stage) 的 step 结果缓存。

    结构：{ "fingerprint": "<hex>", "steps": { "<step_key>": <outcome dict> } }
    指纹不匹配 → 整份作废重建（任一输入/脚本变化 = 全部重跑，安全优先）。
    """

    def __init__(self, root: str, ep: str, stage_key: str, fingerprint: str):
        self.path = cache_path(root, ep, stage_key)
        self.fingerprint = fingerprint
        self.enabled = not cache_disabled()
        raw = load_cache(self.path) if self.enabled else {}
        if raw.get("fingerprint") != fingerprint:
            raw = {"fingerprint": fingerprint, "steps": {}}
        self._steps: Dict[str, Any] = dict(raw.get("steps") or {})
        self._fresh: Dict[str, Any] = {}  # 本轮新算的结果，save 时合并落盘

    def get(self, step_key: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        # 先看本轮新算的（同会话内已 put 的复用），再看上次落盘的。
        hit = self._fresh.get(step_key)
        if not isinstance(hit, dict):
            hit = self._steps.get(step_key)
        return dict(hit) if isinstance(hit, dict) else None

    def put(self, step_key: str, outcome: Dict[str, Any]) -> None:
        self._fresh[step_key] = outcome

    def save(self) -> None:
        if not self.enabled or not self._fresh:
            return
        merged = dict(self._steps)
        merged.update(self._fresh)
        save_cache(self.path, {"fingerprint": self.fingerprint, "steps": merged})


def run_cached_parallel(
    steps: Sequence[Tuple[str, Any]],
    run_one: Callable[[Any], Dict[str, Any]],
    *,
    cache: Optional[PreworkCache] = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    should_cache: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> List[Dict[str, Any]]:
    """并发执行独立 step，按声明顺序返回结果（命中缓存的跳过执行）。

    steps:   [(step_key, step_obj), ...]——step_key 唯一标识该 step（缓存键），step_obj 透传给 run_one。
    run_one: (step_obj) -> outcome dict（须可 JSON 序列化；约定含 'status' 等字段，由调用方解释）。
             只在缓存未命中时被调用；不得有跨 step 副作用顺序依赖（调用方负责保证 step 间独立）。
    should_cache: (outcome) -> bool，决定该结果是否写回缓存。默认全部缓存；闸门类常传
             `lambda o: o.get("status") in ("pass","warn")`——只缓存"绿"，让"红"/异常下次仍重跑，
             防瞬时崩溃被当成持久阻断粘住。
    返回：与 steps 等长、同序的 outcome 列表。命中缓存的项带 '_cached': True。

    语义保证：结果按输入顺序回填，故调用方据此设置 prework_block 等顺序敏感状态时，
    行为与纯串行一致——并行只影响 subprocess 的执行时机，不影响结果应用顺序。
    """
    n = len(steps)
    results: List[Optional[Dict[str, Any]]] = [None] * n
    misses: List[Tuple[int, Any]] = []

    for i, (key, obj) in enumerate(steps):
        cached = cache.get(key) if cache is not None else None
        if cached is not None:
            cached["_cached"] = True
            results[i] = cached
        else:
            misses.append((i, obj))

    if misses:
        workers = max(1, min(max_workers, len(misses)))
        if workers == 1:
            for i, obj in misses:
                results[i] = run_one(obj)
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                fut_to_idx = {ex.submit(run_one, obj): i for i, obj in misses}
                for fut in as_completed(fut_to_idx):
                    i = fut_to_idx[fut]
                    results[i] = fut.result()
        if cache is not None:
            for i, _obj in misses:
                key = steps[i][0]
                out = results[i]
                if isinstance(out, dict) and (should_cache is None or should_cache(out)):
                    cache.put(key, {k: v for k, v in out.items() if k != "_cached"})

    return [r if isinstance(r, dict) else {} for r in results]
