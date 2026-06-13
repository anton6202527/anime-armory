#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telemetry and dashboard integration for the n2d pipeline."""

import os
import subprocess
import time
from typing import Any, Dict, Optional

# 必须与 dashboard.py `record --event` 的 choices 白名单保持一致（单一真值）。
VALID_EVENTS = (
    "generation", "redraw", "qa", "cost", "duration", "manual", "release", "revenue",
)


def _dashboard_script() -> str:
    """绝对路径定位 dashboard.py（本文件已迁到 skills/n2d/_lib/，上溯两级到 skills/）。"""
    lib_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(lib_dir, "..", "..", "n2d-dashboard", "scripts", "dashboard.py"))


def record_event(
    work_root: str,
    episode: str,
    stage: str,
    event: str = "generation",
    *,
    asset: Optional[str] = None,
    status: str = "pass",
    duration_sec: float = 0.0,
    provider: str = "unknown",
    cost: float = 0.0,
    unit: str = "CNY",
    redraw_reason: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    build: bool = True,
):
    """记录生产数据到 n2d-dashboard（异步、不阻断生产）。

    work_root: 作品根目录
    episode: 集号（如 "第1集"）
    stage: 阶段（voice, image, video, compose, script, review）
    event: 事件类型，必须 ∈ VALID_EVENTS（与 dashboard.py 的 --event 白名单一致）。
           传非法值会 raise ValueError——属编程错误，不应静默吞掉（旧实现用
           Popen+DEVNULL 会把 dashboard 的 rc=2 拒绝完全吞没，事件无声丢失）。
    build: True 时 dashboard 录入后立即重建聚合；批量记账时传 False（追加 --no-build）
           以避免每条都抢 production_events.lock 做全量重算（见 n2d-batch runner）。
    """
    if event not in VALID_EVENTS:
        raise ValueError(f"record_event: 非法 event={event!r}；合法值 {VALID_EVENTS}")
    try:
        cmd = [
            "python3", _dashboard_script(),
            "record", work_root,
            "--episode", episode,
            "--stage", stage,
            "--event", event,
            "--status", status,
            "--duration-sec", f"{duration_sec:.2f}",
            "--provider", provider,
            "--cost", str(cost),
            "--unit", unit,
        ]
        if not build:
            cmd.append("--no-build")
        if asset:
            cmd += ["--asset", asset]
        if redraw_reason:
            cmd += ["--redraw-reason", redraw_reason]
        if meta:
            for k, v in meta.items():
                cmd += ["--meta", f"{k}={v}"]

        # 异步后台执行，避免阻塞主流程
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        # 遥测失败不阻断生产（路径/spawn 异常）
        print(f"⚠️ Telemetry failed: {e}")


class Timer:
    """Simple timer context manager for duration tracking."""
    def __init__(self):
        self.start_time = None
        self.duration = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            self.duration = time.time() - self.start_time

    def elapsed(self) -> float:
        if self.start_time:
            return time.time() - self.start_time
        return 0.0
