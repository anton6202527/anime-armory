#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测画漫画生图后端，并可把选择写入项目 _设置.md。

本脚本只做本线自包含探测，不依赖其它系列实现。当前优先级：
1. Codex CLI + image_generation feature（可自动落 PNG）
2. manual（只生成 job 包，人工外部出图）
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


CODEX_MODEL = "GPT Image 2"
CODEX_CHANNEL = "Codex CLI"


def run(cmd: list[str], timeout: float = 10) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return subprocess.CompletedProcess(cmd, 127, "", f"{type(exc).__name__}: {exc}")


def detect_codex() -> dict:
    path = shutil.which("codex")
    if not path:
        return {
            "id": "codex",
            "name": CODEX_CHANNEL,
            "usable": False,
            "reason": "codex not found in PATH",
        }
    version = run(["codex", "--version"])
    features = run(["codex", "features", "list"])
    feature_text = (features.stdout or "") + "\n" + (features.stderr or "")
    image_generation = any(
        line.split()[:1] == ["image_generation"] and line.rstrip().endswith("true")
        for line in feature_text.splitlines()
    )
    return {
        "id": "codex",
        "name": CODEX_CHANNEL,
        "model": CODEX_MODEL,
        "path": path,
        "version": (version.stdout or version.stderr or "").strip().splitlines()[:1],
        "image_generation_feature": image_generation,
        "usable": bool(version.returncode == 0 and features.returncode == 0 and image_generation),
        "reason": "" if image_generation else "codex image_generation feature not enabled",
    }


def detect() -> dict:
    codex = detect_codex()
    usable = []
    needs_manual = []
    if codex["usable"]:
        usable.append(codex)
    else:
        needs_manual.append(codex)
    manual = {
        "id": "manual",
        "name": "manual",
        "model": "自定义",
        "usable": True,
        "automatic_png": False,
        "reason": "manual fallback writes prompts only; user supplies images",
    }
    selected = usable[0] if usable else manual
    return {
        "kind": "comic_image_backend_scan",
        "priority": ["codex", "manual"],
        "usable_backends": usable,
        "needs_confirmation_backends": needs_manual,
        "fallback": manual,
        "selected": selected,
    }


def set_markdown_setting(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else ["# 设置", "", "## 选择点"]
    prefix_a = f"- {key}:"
    prefix_b = f"- {key}："
    replaced = False
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix_a) or stripped.startswith(prefix_b):
            out.append(f"- {key}: {value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        insert_at = len(out)
        for idx, line in enumerate(out):
            if line.strip().startswith("- 参考一致性策略"):
                insert_at = idx
                break
        out.insert(insert_at, f"- {key}: {value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_project_settings(root: Path, selected: dict) -> None:
    settings = root / "_设置.md"
    if selected.get("id") == "codex":
        set_markdown_setting(settings, "生图模型", selected.get("model") or CODEX_MODEL)
        set_markdown_setting(settings, "生图渠道", selected.get("name") or CODEX_CHANNEL)
        set_markdown_setting(settings, "生图AI", "Codex")
    else:
        set_markdown_setting(settings, "生图模型", selected.get("model") or "自定义")
        set_markdown_setting(settings, "生图渠道", selected.get("name") or "manual")
        set_markdown_setting(settings, "生图AI", "manual")


def main() -> int:
    parser = argparse.ArgumentParser(description="探测画漫画生图后端")
    parser.add_argument("project_root", nargs="?")
    parser.add_argument("--write-settings", action="store_true", help="把自动选择结果写入项目 _设置.md")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = detect()
    if args.write_settings:
        if not args.project_root:
            raise SystemExit("--write-settings requires project_root")
        root = Path(args.project_root).expanduser().resolve()
        write_project_settings(root, result["selected"])
        result["settings_written"] = str(root / "_设置.md")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        selected = result["selected"]
        print(f"selected: {selected.get('id')} / {selected.get('name')} / {selected.get('model')}")
        if result["usable_backends"]:
            print("usable: " + ", ".join(item["id"] for item in result["usable_backends"]))
        for item in result["needs_confirmation_backends"]:
            print(f"not usable: {item['id']} — {item.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
