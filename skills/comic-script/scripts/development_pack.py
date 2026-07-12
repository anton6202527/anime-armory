#!/usr/bin/env python3
"""漫画开发包（2026-07 标准审计·port 自 n2d P-1 开发包模式的漫画裁剪重实现，不跨线 import）。

实证空档：金瓶梅 10 回只拆 1 回、红楼梦 120 回只拆序章——**没有系列级开发层**，
拆分/编剧直接从"眼前一话"开始，第 2 话就断供。n2d 的解法是 P-1 开发包 gate：拆集写词前
先落系列圣经、改编策略、追更弧、可行性与绿灯签收。漫画裁剪版保留四件套 + 签收
（删掉 n2d 的时长/配音/视频路由可行性——条漫无时长轴）：

  开发包/adaptation_strategy.json   改编策略：改编边界、爽点承诺账、因果链主干、伏笔账
                                    （补齐 source_semantics 只管语言归一化、不管理解的缺口）
  开发包/season_arc.json            前 3-5 话追更弧：每话核心冲突/结尾钩子/承诺兑现位
  脚本/split_blueprint.json         全书拆分蓝图：候选话次边界账（source_range/冲突/钩子/预计格数）
                                    （chapter_beat_audit 的 split_blueprint_missing 检查同一文件）
  开发包/signoff.json               绿灯签收：reviewer/role/time + 对上述文件的 SHA 绑定

默认 report-only；`check --strict` 对缺件/占位/签收过期 exit 2。scaffold 只补缺失文件、
永不覆盖已有内容（草稿由人/上层 agent 填，脚本不自我签收——与 n2d 同纪律）。

用法：
  cd skills/comic-script/scripts
  python3 development_pack.py <作品根> scaffold --write
  python3 development_pack.py <作品根> check [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

VERSION = 1
KIND = "comic_development_pack_check"
PLACEHOLDER_RE = re.compile(r"待补|待填|TODO|TBD|<[^>]*>|__待", re.IGNORECASE)

STRATEGY_TEMPLATE: Dict[str, Any] = {
    "kind": "comic_adaptation_strategy",
    "version": 1,
    "status": "draft",
    "adaptation_boundary": "待补：哪些内容不改编/如何镜外化（露骨/敏感/超纲情节的处理边界）",
    "promise_ledger": [
        {"promise_id": "PRM_001", "promise": "待补：向读者立的第一个核心悬念/欲望承诺",
         "opened_chapter": "第1话", "payoff_chapter": "待补", "status": "open"},
    ],
    "causality_spine": [
        "待补：全书因果链主干（事件A→导致B→逼出选择C…，改编时不可断的链）",
    ],
    "foreshadowing_ledger": [
        {"setup_id": "FSH_001", "setup": "待补：伏笔内容", "planted_chapter": "第1话",
         "payoff_chapter": "待补", "status": "planted"},
    ],
}

SEASON_ARC_TEMPLATE: Dict[str, Any] = {
    "kind": "comic_season_arc",
    "version": 1,
    "status": "draft",
    "chapters": [
        {"chapter": f"第{i}话", "core_conflict": "待补", "ending_hook": "待补",
         "promise_refs": []} for i in range(1, 4)
    ],
}

BLUEPRINT_TEMPLATE: Dict[str, Any] = {
    "kind": "comic_split_blueprint",
    "version": 1,
    "status": "draft",
    "policy": "按『冲突→爽点/揭示→钩子』闭环切话，不按字数/回目硬切；边界候选先粗后精，逐话精修时可调",
    "chapters": [
        {"chapter": "第1话", "source_range": "待补：对应源本回/章/段范围",
         "core_conflict": "待补", "ending_hook_candidate": "待补", "estimated_panels": 0},
    ],
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def pack_files(root: Path) -> Dict[str, Path]:
    return {
        "adaptation_strategy": root / "开发包" / "adaptation_strategy.json",
        "season_arc": root / "开发包" / "season_arc.json",
        "split_blueprint": root / "脚本" / "split_blueprint.json",
        "signoff": root / "开发包" / "signoff.json",
    }


def scaffold(root: Path, *, write: bool) -> List[str]:
    created: List[str] = []
    templates = {
        "adaptation_strategy": STRATEGY_TEMPLATE,
        "season_arc": SEASON_ARC_TEMPLATE,
        "split_blueprint": BLUEPRINT_TEMPLATE,
    }
    files = pack_files(root)
    for key, template in templates.items():
        path = files[key]
        if path.is_file():
            continue
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append(str(path.relative_to(root)))
    return created


def contains_placeholder(value: Any) -> bool:
    return bool(PLACEHOLDER_RE.search(json.dumps(value, ensure_ascii=False)))


def check_pack(root: Path) -> Dict[str, Any]:
    files = pack_files(root)
    gaps: List[Dict[str, str]] = []
    file_status: Dict[str, str] = {}
    hashes: Dict[str, str] = {}
    for key in ("adaptation_strategy", "season_arc", "split_blueprint"):
        path = files[key]
        if not path.is_file():
            gaps.append({"code": f"{key}_missing", "message": f"缺 {path.relative_to(root)}——先 scaffold --write 再填内容。"})
            file_status[key] = "missing"
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            gaps.append({"code": f"{key}_invalid", "message": f"{path.relative_to(root)} 不是合法 JSON。"})
            file_status[key] = "invalid"
            continue
        hashes[key] = sha256_file(path)
        status = str(data.get("status") or "draft")
        if status != "confirmed":
            gaps.append({"code": f"{key}_not_confirmed",
                         "message": f"{path.relative_to(root)} status={status}——内容填完后置 confirmed。"})
        elif contains_placeholder(data):
            gaps.append({"code": f"{key}_placeholder_in_confirmed",
                         "message": f"{path.relative_to(root)} 声明 confirmed 却仍含『待补/TODO』占位——反声明。"})
        file_status[key] = status
    # 签收：内容 confirmed ≠ 绿灯；还需 reviewer 对当前文件 SHA 签收（脚本不自我签收）
    signoff_path = files["signoff"]
    if not signoff_path.is_file():
        gaps.append({"code": "signoff_missing",
                     "message": "缺 开发包/signoff.json 绿灯签收（reviewer/role/time + 三件套 SHA 绑定）。"})
    else:
        try:
            signoff = json.loads(signoff_path.read_text(encoding="utf-8"))
        except Exception:
            signoff = {}
            gaps.append({"code": "signoff_invalid", "message": "signoff.json 不是合法 JSON。"})
        if signoff:
            if not str(signoff.get("reviewer") or "").strip() or not str(signoff.get("role") or "").strip():
                gaps.append({"code": "signoff_reviewer_missing", "message": "signoff 缺 reviewer/role。"})
            bound = signoff.get("file_sha256") if isinstance(signoff.get("file_sha256"), Mapping) else {}
            for key, digest in hashes.items():
                if str(bound.get(key) or "") != digest:
                    gaps.append({"code": f"signoff_stale_{key}",
                                 "message": f"signoff 对 {key} 的 SHA 已过期/缺失——内容改动后须重新签收。"})
    return {
        "kind": KIND, "version": VERSION, "generated_at": now_iso(),
        "files": file_status,
        "file_sha256": hashes,
        "status": "confirmed" if not gaps else "blocked",
        "gaps": gaps,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("command", choices=("scaffold", "check"))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="check 缺件/占位/签收过期时 exit 2")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    if ns.command == "scaffold":
        created = scaffold(root, write=ns.write)
        payload = {"created": created, "write": ns.write}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    report = check_pack(root)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"# 漫画开发包体检 · {report['status']}")
        for gap in report["gaps"]:
            print(f"- ⚠️ [{gap['code']}] {gap['message']}")
        if not report["gaps"]:
            print("- ✅ 四件套齐、内容 confirmed、签收 SHA 绑定当前版本")
    if ns.strict and report["status"] != "confirmed":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
