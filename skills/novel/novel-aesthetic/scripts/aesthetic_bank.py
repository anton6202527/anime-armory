#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Maintain positive craft samples for novel projects."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime


AUTHORIZED_RIGHTS = {"project-demo", "user-owned", "licensed", "public-domain"}
# novelty/surprise/premise：让审美库不只当"工艺正向标尺"，也当**新颖度正向信号源**——
# 登记"这段新在哪/违背了什么惯例/前提有多不落俗套"，供写章按意外性需求定向调用、score ⑧ 维参照。
KNOWN_DIMENSIONS = {"opening", "scene", "character", "dialogue", "prose", "structure",
                    "theme", "pacing", "hook", "novelty", "surprise", "premise"}
NOVELTY_DIMENSIONS = {"novelty", "surprise", "premise"}


def bank_path(root: str) -> str:
    return os.path.join(root, "设定", "aesthetic_bank.json")


def md_path(root: str) -> str:
    return os.path.join(root, "设定", "审美样本库.md")


def load_bank(root: str) -> dict:
    path = bank_path(root)
    if not os.path.exists(path):
        return {
            "schema_version": 1,
            "kind": "novel_aesthetic_bank",
            "updated_at": date.today().isoformat(),
            "samples": [],
        }
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if payload.get("kind") != "novel_aesthetic_bank":
        raise SystemExit(f"[err] 非审美样本库：{path}")
    payload.setdefault("samples", [])
    return payload


def write_bank(root: str, bank: dict) -> None:
    os.makedirs(os.path.dirname(bank_path(root)), exist_ok=True)
    bank["updated_at"] = date.today().isoformat()
    tmp = bank_path(root) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)
    os.replace(tmp, bank_path(root))
    write_markdown(root, bank)


def split_csv(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").replace("，", ",").split(",") if x.strip()]


def scaffold(root: str) -> None:
    bank = load_bank(root)
    write_bank(root, bank)
    print(f"[ok] aesthetic bank: {bank_path(root)}")


def add_sample(args: argparse.Namespace) -> dict:
    if args.source_rights not in AUTHORIZED_RIGHTS:
        raise SystemExit("[err] 审美样本必须是 project-demo/user-owned/licensed/public-domain")
    root = os.path.abspath(args.project_root)
    bank = load_bank(root)
    sample_id = args.sample_id or f"AES-{date.today().strftime('%Y%m%d')}-{len(bank['samples']) + 1:03d}"
    bank["samples"] = [s for s in bank["samples"] if s.get("sample_id") != sample_id]
    dimensions = split_csv(args.dimension)
    sample = {
        "sample_id": sample_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_title": args.source_title,
        "source_path": args.source_path or "",
        "source_rights": args.source_rights,
        "authorization_note": args.authorization_note or "",
        "genre": args.genre or "",
        "dimensions": dimensions,
        "why_it_works": args.why_it_works.strip(),
        "why_it_is_new": (getattr(args, "why_it_is_new", "") or "").strip(),
        "transfer_rule": args.transfer_rule.strip(),
        "anti_copy_note": args.anti_copy_note or "只迁移机制，不复用原句、专名或独特表达。",
        "applicable_when": args.applicable_when or "",
        "avoid_when": args.avoid_when or "",
    }
    bank["samples"].append(sample)
    bank["samples"].sort(key=lambda s: s.get("sample_id") or "")
    write_bank(root, bank)
    return sample


def check_bank(root: str) -> dict:
    bank = load_bank(root)
    findings = []
    for sample in bank.get("samples") or []:
        missing = [field for field in ("source_title", "source_rights", "why_it_works", "transfer_rule") if not str(sample.get(field) or "").strip()]
        if missing:
            findings.append({
                "id": "AES-MISSING-FIELDS",
                "sample_id": sample.get("sample_id"),
                "severity": "blocking",
                "reason": "缺少字段：" + "、".join(missing),
            })
        if sample.get("source_rights") not in AUTHORIZED_RIGHTS:
            findings.append({
                "id": "AES-RIGHTS-BLOCK",
                "sample_id": sample.get("sample_id"),
                "severity": "blocking",
                "reason": "样本权利来源不允许。",
            })
        dims = set(sample.get("dimensions") or [])
        if dims and not dims.intersection(KNOWN_DIMENSIONS):
            findings.append({
                "id": "AES-WEAK-DIMENSION",
                "sample_id": sample.get("sample_id"),
                "severity": "warning",
                "reason": "dimension 未命中推荐审美维度，后续检索可能弱。",
            })
    return {
        "schema_version": 1,
        "kind": "novel_aesthetic_bank_check",
        "samples": len(bank.get("samples") or []),
        "blocking": sum(1 for f in findings if f["severity"] == "blocking"),
        "warnings": sum(1 for f in findings if f["severity"] != "blocking"),
        "findings": findings,
    }


def prompt_samples(root: str, *, dimension: str = "", limit: int = 5) -> list[dict]:
    samples = load_bank(root).get("samples") or []
    if dimension:
        samples = [s for s in samples if dimension in set(s.get("dimensions") or [])]
    return samples[: max(1, limit)]


def write_markdown(root: str, bank: dict) -> None:
    lines = [
        "# 审美样本库",
        "",
        f"- 更新日期：{bank.get('updated_at')}",
        f"- 样本数：{len(bank.get('samples') or [])}",
        "",
        "## 使用规则",
        "- 样本只用于拆解“为什么有效”，不得复制原句、专名或在世作者风格。",
        "- 写章时迁移 `transfer_rule`，审稿时用 `why_it_works` 做正向标尺。",
        "",
    ]
    for sample in bank.get("samples") or []:
        lines.extend([
            f"## {sample.get('sample_id')} · {sample.get('source_title')}",
            f"- 权利：{sample.get('source_rights')}；维度：{', '.join(sample.get('dimensions') or [])}",
            f"- 为什么有效：{sample.get('why_it_works')}",
            f"- 可迁移规则：{sample.get('transfer_rule')}",
            f"- 禁抄说明：{sample.get('anti_copy_note')}",
        ])
        if sample.get("applicable_when"):
            lines.append(f"- 适用：{sample.get('applicable_when')}")
        if sample.get("avoid_when"):
            lines.append(f"- 避免：{sample.get('avoid_when')}")
        lines.append("")
    os.makedirs(os.path.dirname(md_path(root)), exist_ok=True)
    with open(md_path(root), "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="维护 novel 正向审美样本库")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scaffold")
    sc.add_argument("project_root")
    add = sub.add_parser("add")
    add.add_argument("project_root")
    add.add_argument("--sample-id", default="")
    add.add_argument("--source-title", required=True)
    add.add_argument("--source-path", default="")
    add.add_argument("--source-rights", required=True, choices=sorted(AUTHORIZED_RIGHTS))
    add.add_argument("--authorization-note", default="")
    add.add_argument("--genre", default="")
    add.add_argument("--dimension", required=True)
    add.add_argument("--why-it-works", required=True)
    add.add_argument("--why-it-is-new", default="",
                     help="（novelty/surprise/premise 维度建议填）这段新在哪/违背了什么读者惯例")
    add.add_argument("--transfer-rule", required=True)
    add.add_argument("--anti-copy-note", default="")
    add.add_argument("--applicable-when", default="")
    add.add_argument("--avoid-when", default="")
    ck = sub.add_parser("check")
    ck.add_argument("project_root")
    ck.add_argument("--json", action="store_true")
    pr = sub.add_parser("prompt")
    pr.add_argument("project_root")
    pr.add_argument("--dimension", default="")
    pr.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if args.cmd == "scaffold":
        scaffold(root)
        return 0
    if args.cmd == "add":
        sample = add_sample(args)
        print(f"[ok] added {sample['sample_id']} -> {md_path(root)}")
        return 0
    if args.cmd == "check":
        result = check_bank(root)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[summary] samples={result['samples']} blocking={result['blocking']} warnings={result['warnings']}")
            for item in result["findings"]:
                print(f"- {item['severity']} {item.get('sample_id')}: {item['reason']}")
        return 1 if result["blocking"] else 0
    print("# 正向审美对照")
    for sample in prompt_samples(root, dimension=args.dimension, limit=args.limit):
        print(f"- {sample['sample_id']} [{', '.join(sample.get('dimensions') or [])}] {sample.get('source_title')}")
        print(f"  为什么有效：{sample.get('why_it_works')}")
        print(f"  迁移规则：{sample.get('transfer_rule')}")
        print(f"  禁抄：{sample.get('anti_copy_note')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
