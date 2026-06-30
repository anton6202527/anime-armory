#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Maintain a living-material observation bank for novel projects."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime


VALID_SOURCES = {"observation", "interview", "memory", "field-note", "user-note", "research-shadow"}
REQUIRED_USES = {"conflict", "pressure", "character_detail", "setting", "dialogue", "subtext", "sensory", "metaphor", "profession"}


def material_dir(root: str) -> str:
    return os.path.join(root, "素材")


def jsonl_path(root: str) -> str:
    return os.path.join(material_dir(root), "观察札记.jsonl")


def md_path(root: str) -> str:
    return os.path.join(material_dir(root), "观察素材库.md")


def read_records(root: str) -> list[dict]:
    path = jsonl_path(root)
    records: list[dict] = []
    if not os.path.isfile(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict) and payload.get("kind") == "novel_observation":
                records.append(payload)
    return records


def write_records(root: str, records: list[dict]) -> None:
    os.makedirs(material_dir(root), exist_ok=True)
    tmp = jsonl_path(root) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, jsonl_path(root))


def split_csv(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").replace("，", ",").split(",") if x.strip()]


def next_id(records: list[dict]) -> str:
    today = date.today().strftime("%Y%m%d")
    count = sum(1 for r in records if str(r.get("id", "")).startswith(f"OBS-{today}-"))
    return f"OBS-{today}-{count + 1:03d}"


def scaffold(root: str) -> None:
    os.makedirs(material_dir(root), exist_ok=True)
    if not os.path.exists(jsonl_path(root)):
        open(jsonl_path(root), "a", encoding="utf-8").close()
    if not os.path.exists(md_path(root)):
        write_markdown(root, [])
    print(f"[ok] observation bank: {jsonl_path(root)}")


def add_record(args: argparse.Namespace) -> dict:
    root = os.path.abspath(args.project_root)
    records = read_records(root)
    source = args.source if args.source in VALID_SOURCES else "user-note"
    dramatic_use = split_csv(args.dramatic_use)
    record = {
        "schema_version": 1,
        "kind": "novel_observation",
        "id": next_id(records),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "domain": args.domain or "",
        "text": args.text.strip(),
        "sensory": args.sensory or "",
        "behavior": args.behavior or "",
        "dramatic_use": dramatic_use,
        "tags": split_csv(args.tags),
        "scene_hint": args.scene or "",
        "privacy": args.privacy,
        "consent_note": args.consent_note or "",
        "transfer_rule": args.transfer_rule or "",
    }
    records.append(record)
    write_records(root, records)
    write_markdown(root, records)
    return record


def check_records(root: str) -> dict:
    records = read_records(root)
    findings = []
    for rec in records:
        missing = []
        if not str(rec.get("text") or "").strip():
            missing.append("text")
        if not rec.get("dramatic_use"):
            missing.append("dramatic_use")
        if not (str(rec.get("sensory") or "").strip() or str(rec.get("behavior") or "").strip()):
            missing.append("sensory/behavior")
        if missing:
            findings.append({
                "id": "OBS-MISSING-FIELDS",
                "record_id": rec.get("id"),
                "severity": "warning",
                "reason": "缺少可转写字段：" + "、".join(missing),
            })
        uses = set(rec.get("dramatic_use") or [])
        if uses and not uses.intersection(REQUIRED_USES):
            findings.append({
                "id": "OBS-WEAK-DRAMATIC-USE",
                "record_id": rec.get("id"),
                "severity": "warning",
                "reason": "dramatic_use 未命中推荐用途词，写章时可能难调用。",
            })
        if rec.get("privacy") == "raw-identifiable":
            findings.append({
                "id": "OBS-PRIVACY-RISK",
                "record_id": rec.get("id"),
                "severity": "blocking",
                "reason": "真实人物素材未匿名化；请改为 anonymized 或删除敏感信息。",
            })
    return {
        "schema_version": 1,
        "kind": "novel_observation_check",
        "records": len(records),
        "blocking": sum(1 for f in findings if f["severity"] == "blocking"),
        "warnings": sum(1 for f in findings if f["severity"] != "blocking"),
        "findings": findings,
    }


def record_matches(rec: dict, *, tag: str, domain: str, dramatic_use: str) -> bool:
    if tag and tag not in set(rec.get("tags") or []):
        return False
    if domain and domain not in str(rec.get("domain") or ""):
        return False
    if dramatic_use and dramatic_use not in set(rec.get("dramatic_use") or []):
        return False
    return True


def select_records(root: str, *, tag: str = "", domain: str = "", dramatic_use: str = "", limit: int = 8) -> list[dict]:
    records = [r for r in read_records(root) if record_matches(r, tag=tag, domain=domain, dramatic_use=dramatic_use)]
    return records[: max(1, limit)]


def write_markdown(root: str, records: list[dict]) -> None:
    lines = [
        "# 观察素材库",
        "",
        f"- 更新日期：{date.today().isoformat()}",
        f"- 条目数：{len(records)}",
        "",
        "## 使用规则",
        "- 只转化行为、感官、空间和情绪机制，不照搬真实隐私。",
        "- 每条素材进入正文前，要服务场景目标、人物选择或潜台词。",
        "",
        "## 条目",
        "",
    ]
    for rec in records:
        uses = ", ".join(rec.get("dramatic_use") or [])
        tags = ", ".join(rec.get("tags") or [])
        lines.extend([
            f"### {rec.get('id')} · {rec.get('domain') or '未分类'}",
            f"- 来源：{rec.get('source')}；隐私：{rec.get('privacy')}",
            f"- 用途：{uses or '待补'}；标签：{tags or '待补'}",
            f"- 观察：{rec.get('text') or ''}",
            f"- 五感：{rec.get('sensory') or '待补'}",
            f"- 行为：{rec.get('behavior') or '待补'}",
            f"- 转写规则：{rec.get('transfer_rule') or '提取机制，不照搬真人隐私。'}",
            "",
        ])
    os.makedirs(material_dir(root), exist_ok=True)
    with open(md_path(root), "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="维护 novel 观察素材库")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scaffold")
    sc.add_argument("project_root")
    add = sub.add_parser("add")
    add.add_argument("project_root")
    add.add_argument("--source", default="observation", choices=sorted(VALID_SOURCES))
    add.add_argument("--domain", default="")
    add.add_argument("--text", required=True)
    add.add_argument("--sensory", default="")
    add.add_argument("--behavior", default="")
    add.add_argument("--dramatic-use", required=True)
    add.add_argument("--tags", default="")
    add.add_argument("--scene", default="")
    add.add_argument("--privacy", default="anonymized", choices=("anonymized", "fictionalized", "raw-identifiable"))
    add.add_argument("--consent-note", default="")
    add.add_argument("--transfer-rule", default="")
    ck = sub.add_parser("check")
    ck.add_argument("project_root")
    ck.add_argument("--json", action="store_true")
    sel = sub.add_parser("select")
    sel.add_argument("project_root")
    sel.add_argument("--tag", default="")
    sel.add_argument("--domain", default="")
    sel.add_argument("--dramatic-use", default="")
    sel.add_argument("--limit", type=int, default=8)
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if args.cmd == "scaffold":
        scaffold(root)
        return 0
    if args.cmd == "add":
        rec = add_record(args)
        print(f"[ok] added {rec['id']} -> {md_path(root)}")
        return 0
    if args.cmd == "check":
        result = check_records(root)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[summary] records={result['records']} blocking={result['blocking']} warnings={result['warnings']}")
            for item in result["findings"]:
                print(f"- {item['severity']} {item['record_id']}: {item['reason']}")
        return 1 if result["blocking"] else 0
    records = select_records(root, tag=args.tag, domain=args.domain, dramatic_use=args.dramatic_use, limit=args.limit)
    print("# 可注入写章任务包的观察素材")
    for rec in records:
        print(f"- {rec['id']} [{rec.get('domain')}] {rec.get('text')}")
        if rec.get("sensory"):
            print(f"  五感：{rec['sensory']}")
        if rec.get("behavior"):
            print(f"  行为：{rec['behavior']}")
        if rec.get("transfer_rule"):
            print(f"  转写：{rec['transfer_rule']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
