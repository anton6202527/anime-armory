#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CCIP 外部解释器桥：让身份机检不再因当前解释器缺依赖而降级空转。

背景：gate/review 通常跑在系统 Python（PEP668，装不了 dghs-imgutils），
CCIP 动漫身份 embedding 长期"不可用→退化为色彩直方图代理"，一致性硬闸
实际空转（史进跨 4 话漂移未被拦截的直接根因之一）。

本桥按以下顺序解析可用的 CCIP 执行方式：
1. 当前解释器可直接 import imgutils → 进程内直调（零开销）；
2. 环境变量 ``COMIC_CCIP_PYTHON`` 指定的解释器；
3. 约定 conda 环境 ``comicqc``（安装：``conda create -n comicqc python=3.11``
   然后 ``pip install dghs-imgutils onnxruntime``）。

外部解释器模式用**常驻 worker 子进程 + 行式 JSON 协议**：模型仅加载一次，
一话几十格的批量判定不会退化成逐对冷启动。
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_CONDA_ENV_GLOBS = (
    "/opt/homebrew/Caskroom/miniforge/base/envs/comicqc/bin/python",
    str(Path.home() / "miniconda3/envs/comicqc/bin/python"),
    str(Path.home() / "anaconda3/envs/comicqc/bin/python"),
    str(Path.home() / "miniforge3/envs/comicqc/bin/python"),
)


def _interpreter_has_imgutils(python_path: str) -> bool:
    """不 spawn 解释器，直接查 site-packages，避免每次探测付模型级启动开销。"""
    root = Path(python_path).resolve().parent.parent
    return bool(glob.glob(str(root / "lib" / "python*" / "site-packages" / "imgutils")))


def _inprocess_available() -> bool:
    try:
        from imgutils.metrics import ccip_difference  # noqa: F401

        return True
    except Exception:
        return False


def resolve_interpreter() -> str:
    """返回可运行 CCIP worker 的解释器路径；进程内可用返回 ``inprocess``；找不到返回空串。"""
    if _inprocess_available():
        return "inprocess"
    override = str(os.environ.get("COMIC_CCIP_PYTHON") or "").strip()
    if override and Path(override).is_file() and _interpreter_has_imgutils(override):
        return override
    for candidate in _CONDA_ENV_GLOBS:
        if Path(candidate).is_file() and _interpreter_has_imgutils(candidate):
            return candidate
    return ""


class CCIPBridge:
    """一次会话一个 worker；worker 内模型只加载一次。"""

    def __init__(self) -> None:
        self._interpreter: str | None = None
        self._proc: subprocess.Popen[str] | None = None
        self._broken = False

    @property
    def interpreter(self) -> str:
        if self._interpreter is None:
            self._interpreter = resolve_interpreter()
        return self._interpreter

    def available(self) -> bool:
        return bool(self.interpreter) and not self._broken

    def mode(self) -> str:
        if not self.available():
            return "unavailable"
        return "inprocess" if self.interpreter == "inprocess" else "external_worker"

    def _ensure_worker(self) -> subprocess.Popen[str] | None:
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        try:
            self._proc = subprocess.Popen(
                [self.interpreter, "-u", str(Path(__file__).resolve()), "--worker"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError:
            self._broken = True
            self._proc = None
        return self._proc

    def batch_differences(self, pairs: list[tuple[str, str]]) -> list[float | None]:
        """逐对 CCIP difference；单对失败记 None，不拖垮整批。"""
        if not pairs:
            return []
        if not self.available():
            return [None] * len(pairs)
        if self.interpreter == "inprocess":
            from imgutils.metrics import ccip_difference

            out: list[float | None] = []
            for a, b in pairs:
                try:
                    out.append(float(ccip_difference(a, b)))
                except Exception:
                    out.append(None)
            return out
        proc = self._ensure_worker()
        if proc is None or proc.stdin is None or proc.stdout is None:
            self._broken = True
            return [None] * len(pairs)
        try:
            proc.stdin.write(json.dumps({"pairs": [[a, b] for a, b in pairs]}) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            payload = json.loads(line)
            diffs = payload.get("diffs")
            if not isinstance(diffs, list) or len(diffs) != len(pairs):
                raise ValueError("worker protocol mismatch")
            return [float(item) if item is not None else None for item in diffs]
        except Exception:
            self._broken = True
            self.close()
            return [None] * len(pairs)

    def close(self) -> None:
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                self._proc.terminate()
            except OSError:
                pass
            self._proc = None


_BRIDGE: CCIPBridge | None = None


def bridge() -> CCIPBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = CCIPBridge()
    return _BRIDGE


def available() -> bool:
    return bridge().available()


def batch_differences(pairs: list[tuple[str, str]]) -> list[float | None]:
    return bridge().batch_differences(pairs)


def describe() -> dict[str, Any]:
    b = bridge()
    return {"available": b.available(), "mode": b.mode(), "interpreter": b.interpreter or ""}


def _worker_loop() -> int:
    from imgutils.metrics import ccip_difference

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            diffs: list[float | None] = []
            for pair in request.get("pairs") or []:
                try:
                    diffs.append(float(ccip_difference(str(pair[0]), str(pair[1]))))
                except Exception:
                    diffs.append(None)
            print(json.dumps({"diffs": diffs}), flush=True)
        except Exception as exc:
            print(json.dumps({"error": str(exc), "diffs": []}), flush=True)
    return 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        sys.exit(_worker_loop())
    print(json.dumps(describe(), ensure_ascii=False, indent=2))
