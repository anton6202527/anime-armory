#!/usr/bin/env python3
"""出图后端连通性探活 adapter（选择点 → 能力/探针映射的单一真值源）。

为什么存在：付费出图前必须确认所选生图后端「能落 PNG」。SKILL.md 写了这条叙述，但此前
没有任何确定性闸门兜底——后端不通（内网 502 / CLI 未登录 / 缺 API key）时照样进付费工位，
要么白花钱碰壁，要么静默兜底换后端导致跨镜漂移。本模块把「后端 → 如何探活」收成 adapter，
gate 据此在 image_preflight 出 BLOCK/WARN。

设计原则（对齐 CLAUDE.md 选择点约定）：
- 候选快照带采集日期；探针规格是可刷新候选，不是真值。
- 留 manual 逃生舱：`N2D_SKIP_BACKEND_PROBE=1` 跳过 live 探活（仍 WARN 提醒人工确认）。
- 探针不确定的后端一律 `none` → unknown(WARN)，绝不用没核实的 argv 误判 down 造成假 BLOCK。
- 区分 down（探针真跑过且失败=可 BLOCK）vs unknown（探针跑不起来/无规格=只 WARN）。

采集日期：2026-06-13  来源：n2d-image/SKILL.md 现行叙述 + 各后端官方文档（探针待逐条复核）
"""
from __future__ import annotations

import os
import subprocess
from typing import Callable, Dict, Optional, Tuple

try:  # 包内/独立两种 import 路径都可用
    from n2d_contract import classify_image_backend
except Exception:  # pragma: no cover - 仅在异常打包布局下走相对兜底
    from .n2d_contract import classify_image_backend  # type: ignore


CATALOG_VERIFIED = {"date": "2026-06-13", "source": "n2d-image/SKILL.md + 各后端官方文档(探针待复核)"}

# canonical 后端 → 探针规格。kind:
#   "cli"  argv 探 CLI 可达/已登录（returncode 0=ok，非0/超时=down，binary 缺=unknown）；
#          可选 health_url_env：若该环境变量给了 base url，则改走 HTTP 健康探活（更能抓内网 502）。
#   "env"  云 API：env 缺=down（必失败），有=ok（best-effort，不实际花钱验）。
#   "none" 暂无核实过的探针 → unknown，由 gate 出 WARN 提示人工确认（不硬拦）。
IMAGE_BACKEND_PROBES: Dict[str, Dict[str, object]] = {
    # 默认路线：codex CLI；若导出 CODEX_IMAGE_BASE_URL（如内网 http://192.168.x.x）则改 HTTP 健康探活。
    "codex":    {"kind": "cli", "argv": ("codex", "features", "list"), "timeout": 8,
                 "health_url_env": "CODEX_IMAGE_BASE_URL"},
    "openai":   {"kind": "env", "env": "OPENAI_API_KEY"},
    # 以下官方后端的 CLI/API 探针口径仍在复核，先不臆造 argv（错的 argv 会假 BLOCK）：
    "dreamina": {"kind": "none", "manual": "确认即梦官方 CLI 已登录·会员态有效（dreamina 控制台或一次 dry-run）"},
    "gemini":   {"kind": "none", "manual": "确认 Gemini/Nano Banana 凭据可用"},
    "seedream": {"kind": "none", "manual": "确认 Seedream 官方 API key/额度可用"},
    "kling":    {"kind": "none", "manual": "确认可灵 Kling 账号/主体库可用"},
    "sora":     {"kind": "none", "manual": "确认 Sora Cameo 账号可用"},
}

Status = str  # "ok" | "down" | "unknown"


def _default_cli_runner(argv, timeout: int) -> Tuple[Status, str]:
    try:
        p = subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return ("unknown", f"未找到 CLI `{argv[0]}`——无法自动探活")
    except subprocess.TimeoutExpired:
        return ("down", f"`{argv[0]}` 探活超时（{timeout}s）")
    except Exception as exc:  # pragma: no cover - 防御
        return ("unknown", f"探活异常：{type(exc).__name__}")
    if p.returncode == 0:
        return ("ok", "")
    return ("down", (p.stderr or p.stdout or "").strip()[:200] or f"returncode={p.returncode}")


def _default_http_runner(url: str, timeout: int) -> Tuple[Status, str]:
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", 200) or 200
            if 200 <= code < 400:
                return ("ok", "")
            return ("down", f"HTTP {code}")
    except urllib.error.HTTPError as exc:
        # 5xx（含内网 502）= 后端不可用；4xx 多为鉴权/路径，归 down 让人确认
        return ("down", f"HTTP {exc.code}")
    except Exception as exc:
        return ("down", f"{type(exc).__name__}: {str(exc)[:120]}")


def probe_backend(
    raw: Optional[str],
    *,
    env: Optional[Dict[str, str]] = None,
    cli_runner: Optional[Callable[..., Tuple[Status, str]]] = None,
    http_runner: Optional[Callable[..., Tuple[Status, str]]] = None,
) -> Tuple[Status, str]:
    """探一个生图后端是否能落 PNG。返回 (status, detail)。

    status：ok=可达；down=探针确证不可达（gate 可据此 BLOCK）；unknown=无法自动探活（gate 只 WARN）。
    runner 可注入（测试用）。`N2D_SKIP_BACKEND_PROBE=1` → 直接 unknown（保留逃生舱）。
    """
    env = dict(os.environ) if env is None else env
    if env.get("N2D_SKIP_BACKEND_PROBE") in ("1", "true", "True"):
        return ("unknown", "N2D_SKIP_BACKEND_PROBE 已设——跳过 live 探活")
    canonical, kind = classify_image_backend(raw)
    if kind == "forbidden":
        # 由 gate 的 check_image_ai_policy 负责硬拦，这里不重复
        return ("unknown", "未授权后端（由后端政策闸门处理）")
    if not canonical:
        return ("unknown", f"未识别的生图后端 `{raw}`——无探针，需人工确认能落 PNG")
    spec = IMAGE_BACKEND_PROBES.get(canonical)
    if not spec:
        return ("unknown", f"`{canonical}` 暂无探针规格")
    cli_runner = cli_runner or _default_cli_runner
    http_runner = http_runner or _default_http_runner
    kind = str(spec.get("kind"))
    if kind == "env":
        var = str(spec.get("env") or "")
        if var and env.get(var):
            return ("ok", "")
        return ("down", f"缺环境变量 {var}（云 API 凭据未配置，必然落不了 PNG）")
    if kind == "cli":
        health_env = str(spec.get("health_url_env") or "")
        url = env.get(health_env) if health_env else None
        if url:
            return http_runner(url.rstrip("/") + "/", int(spec.get("timeout", 8)))
        return cli_runner(spec.get("argv") or (), int(spec.get("timeout", 8)))
    # kind == "none" 或未知
    return ("unknown", str(spec.get("manual") or "无自动探针，需人工确认后端可用"))


def candidate_snapshot() -> Dict[str, object]:
    """freshness/自审用：返回探针候选目录的采集日期戳。"""
    return {"verified": CATALOG_VERIFIED, "backends": sorted(IMAGE_BACKEND_PROBES)}
