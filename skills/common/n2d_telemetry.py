#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telemetry and dashboard integration for the n2d pipeline."""

import os
import subprocess
import time
from typing import Any, Dict, Optional


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
):
    """记录生产数据到 n2d-dashboard。
    
    work_root: 作品根目录
    episode: 集号（如 "第1集"）
    stage: 阶段（voice, image, video, compose, script, review）
    event: 事件类型（generation, redraw, manual, gate, qa）
    """
    try:
        # 寻找 dashboard.py 路径
        # 假设当前文件在 skills/common/n2d_telemetry.py
        common_dir = os.path.dirname(os.path.abspath(__file__))
        dashboard_script = os.path.abspath(os.path.join(common_dir, "..", "n2d-dashboard", "scripts", "dashboard.py"))
        
        if not os.path.exists(dashboard_script):
            # 兜底：如果路径不对（比如被打包后），尝试直接调用命令行
            dashboard_script = "python3 skills/n2d-dashboard/scripts/dashboard.py"
        else:
            dashboard_script = f"python3 {dashboard_script}"

        cmd = [
            "python3", os.path.abspath(os.path.join(common_dir, "..", "n2d-dashboard", "scripts", "dashboard.py")),
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
        # 电测失败不阻断生产
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
