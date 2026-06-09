#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcile and synchronize the novel state ledger with chapter deltas.

The script prepares the audit prompt deterministically. It only merges a delta
after an explicit verification artifact says the chapter/delta match; this
prevents a hand-written delta from becoming canonical without review.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import date


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def get_delta_path(root, chapter):
    return os.path.join(root, "审稿", f"state_delta_第{chapter:02d}章.json")


def get_chapter_path(root, chapter):
    return os.path.join(root, "章节", f"第{chapter:02d}章.md")


def get_ledger_path(root):
    return os.path.join(root, "审稿", "state_ledger.json")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_verification_hashes(root, chapter):
    chapter_file = get_chapter_path(root, chapter)
    delta_file = get_delta_path(root, chapter)
    return {
        "chapter_file_hash": sha256_file(chapter_file),
        "delta_hash": sha256_file(delta_file),
    }


def _verification_status(value):
    text = str(value or "").strip().lower()
    return text in {"ok", "passed", "pass", "verified", "true", "通过"}


def load_verification(path, chapter, expected_hashes=None):
    if not path:
        return False, None, "缺少 --verified <核对结论.json>；不能合并未经验证的状态增量。"
    if not os.path.exists(path):
        return False, None, f"找不到核对结论文件：{path}"
    try:
        payload = load_json(path)
    except json.JSONDecodeError as exc:
        return False, None, f"核对结论不是合法 JSON：{exc}"
    if not isinstance(payload, dict):
        return False, None, "核对结论必须是 JSON object。"
    payload_chapter = payload.get("chapter")
    if payload_chapter is None:
        return False, None, "核对结论缺少 chapter 字段；不能复用泛化 verification。"
    try:
        payload_chapter_num = int(payload_chapter)
    except (TypeError, ValueError):
        return False, None, f"核对结论 chapter 必须是数字：{payload_chapter!r}"
    if payload_chapter_num != int(chapter):
        return False, None, f"核对结论章节不匹配：verification chapter={payload_chapter}, requested={chapter}"
    status = payload.get("status") or payload.get("verdict") or payload.get("result")
    if not _verification_status(status):
        return False, payload, f"核对未通过：status/verdict/result={status!r}"
    expected_hashes = expected_hashes or {}
    for key, expected in expected_hashes.items():
        got = str(payload.get(key) or "").strip()
        if not got:
            return False, payload, f"核对结论缺少 {key}；不能复用未绑定正文/delta 的 verification。"
        if got != expected:
            return False, payload, f"核对结论 {key} 不匹配：verification={got}, current={expected}"
    return True, payload, "核对通过"


def audit_delta_with_content(root, chapter, content):
    delta_path = get_delta_path(root, chapter)
    delta = load_json(delta_path)
    if not delta:
        return False, f"找不到增量文件：{delta_path}"
    hashes = expected_verification_hashes(root, chapter)

    # In a real industrial pipeline, this would call an LLM to verify:
    # 1. Are the 'new_facts' actually in the text?
    # 2. Are there hidden new facts in the text NOT in 'new_facts'?
    # 3. Do 'character_changes' match the behavior in the text?
    
    # For the script framework, we provide the prompt and instructions.
    prompt = f"""# 状态账本对账任务

请对比以下章节正文与对应的「状态增量（Delta）」，核对一致性。

## 章节正文（第{chapter}章）
{content[:2000]}...

## 状态增量 (JSON)
```json
{json.dumps(delta, ensure_ascii=False, indent=2)}
```

## 本次核对指纹（必须原样写回 verification JSON）
- chapter_file_hash: {hashes['chapter_file_hash']}
- delta_hash: {hashes['delta_hash']}

## 任务要求
1. **核实归位**：Delta 中提到的新事实、人设变动、新线索，是否在正文中确实发生了？
2. **漏报检查**：正文中是否出现了重要的新设定、新角色、重大伏笔，但 Delta 中漏记了？
3. **逻辑冲突**：正文中的表现是否违背了 Delta 或 Master Ledger 中的既有约束？

请输出 JSON 对账结论，必须包含：
{{
  "chapter": {chapter},
  "status": "ok",
  "chapter_file_hash": "{hashes['chapter_file_hash']}",
  "delta_hash": "{hashes['delta_hash']}",
  "notes": "具体差异；若无差异写明 delta 与正文一致"
}}
"""
    return True, prompt


def merge_delta_to_ledger(root, chapter, verification=None):
    ledger_path = get_ledger_path(root)
    ledger = load_json(ledger_path)
    if not ledger:
        # Initialize if missing
        ledger = {
            "schema_version": 1,
            "kind": "novel_state_ledger",
            "updated_at": date.today().isoformat(),
            "characters": {},
            "setting_facts": [],
            "open_threads": [],
            "resolved_threads": [],
            "chapter_deltas": {},
        }

    delta_path = get_delta_path(root, chapter)
    delta = load_json(delta_path)
    if not delta:
        return False, f"找不到增量文件：{delta_path}"

    c_key = f"chapter_{chapter:02d}"
    if c_key in ledger.get("chapter_deltas", {}):
        print(f"[info] 第{chapter}章 已在账本中，正在覆盖更新...")

    # Merge facts
    for fact in delta.get("new_facts", []):
        if fact not in ledger["setting_facts"]:
            ledger["setting_facts"].append(fact)

    # Merge characters
    for char_change in delta.get("character_changes", []):
        name = char_change.get("name")
        if not name: continue
        if name not in ledger["characters"]:
            ledger["characters"][name] = {"history": [], "current_state": {}}
        ledger["characters"][name]["history"].append({
            "chapter": chapter,
            "change": char_change.get("change"),
            "state_update": char_change.get("state_update")
        })
        if char_change.get("state_update"):
            ledger["characters"][name]["current_state"].update(char_change["state_update"])

    # Merge threads
    for thread in delta.get("open_threads_added", []):
        ledger["open_threads"].append({"chapter": chapter, "thread": thread})
    
    for thread in delta.get("threads_resolved", []):
        # Move from open to resolved
        found = False
        for i, ot in enumerate(ledger["open_threads"]):
            if ot["thread"] == thread:
                ledger["open_threads"].pop(i)
                ledger["resolved_threads"].append({"chapter": chapter, "thread": thread})
                found = True
                break
        if not found:
            ledger["resolved_threads"].append({"chapter": chapter, "thread": thread, "note": "direct resolve"})

    # Record the delta snapshot
    ledger["chapter_deltas"][c_key] = {
        "merged_at": date.today().isoformat(),
        "summary": delta,
        "verification": verification or {},
    }
    ledger["updated_at"] = date.today().isoformat()
    
    write_json(ledger_path, ledger)
    return True, "合并完成"


def main():
    ap = argparse.ArgumentParser(description="对账并合并小说状态账本")
    ap.add_argument("project_root")
    ap.add_argument("--chapter", type=int, required=True, help="章节号")
    ap.add_argument("--audit", action="store_true", help="输出对账 Prompt（需结合 LLM 使用）")
    ap.add_argument("--merge", action="store_true", help="将已验证 delta 合并入 master ledger")
    ap.add_argument("--verified", help="核对结论 JSON；需含 status/verdict/result=ok|passed|verified|通过")
    ap.add_argument("--auto", action="store_true",
                    help="已废弃：只输出 audit prompt，不再自动合并未经验证的 delta")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    chapter_file = os.path.join(root, "章节", f"第{args.chapter:02d}章.md")
    if not os.path.exists(chapter_file):
        print(f"[err] 找不到章节文件：{chapter_file}", file=sys.stderr)
        sys.exit(2)

    if args.audit or args.auto:
        content = open(chapter_file, encoding="utf-8").read()
        success, res = audit_delta_with_content(root, args.chapter, content)
        if not success:
            print(f"[err] Audit 准备失败: {res}", file=sys.stderr)
            sys.exit(2)
        print("--- LEDGER RECONCILE PROMPT ---")
        print(res)
        print("--- END PROMPT ---")
        if args.auto and not args.merge:
            print("[err] --auto 已废弃：不会合并未经验证的 delta。请保存核对结论 JSON 后重跑 "
                  "`--merge --verified <verification.json>`。", file=sys.stderr)
            sys.exit(1)

    if args.merge or args.auto:
        try:
            expected_hashes = expected_verification_hashes(root, args.chapter)
        except FileNotFoundError as exc:
            print(f"[err] 计算核对 hash 失败：{exc}", file=sys.stderr)
            sys.exit(2)
        verified, verification, msg = load_verification(args.verified, args.chapter, expected_hashes)
        if not verified:
            print(f"[err] {msg}", file=sys.stderr)
            sys.exit(2)
        success, msg = merge_delta_to_ledger(root, args.chapter, verification=verification)
        if success:
            print(f"[ok] 第{args.chapter}章 状态已成功合并至 state_ledger.json")
        else:
            print(f"[err] 合并失败: {msg}", file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
