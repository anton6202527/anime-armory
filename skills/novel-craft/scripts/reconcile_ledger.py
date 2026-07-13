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
import re
import sys
from datetime import date

from store import atomic_write_json, file_lock

try:
    import semantic_job
except ImportError:  # pragma: no cover - helper is optional for legacy direct use
    semantic_job = None

def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    atomic_write_json(path, payload)


# 线程回收模糊匹配：delta 写「查明沈念身世」而 open_thread 存「沈念的身世之谜」时，
# 精确串等匹配失败 → 原 open_thread 永不消除，变僵尸未收线程，污染检索 query 与 arc 快照。
# 用 CJK bigram Jaccard 做归一化匹配（阈值 0.5），把"同一条线程的不同措辞"判为同一条。
THREAD_MATCH_THRESHOLD = 0.5
# 归一化前剥离的功能词/标点：中文虚词让"同一条线程的不同措辞"bigram 交集虚低
# （「查明沈念身世」vs「沈念的身世之谜」剥掉 的/之 后共享 沈念/念身/身世，Jaccard 0.22→0.5）。
_THREAD_STOP = set("的地得了着过之其с与和跟同以为在是有个被把将对于与和，。、；：！？…—·「」“”（）()")


def _normalize_thread(text):
    return "".join(ch for ch in re.sub(r"\s", "", str(text or "")) if ch not in _THREAD_STOP)


def _cjk_bigrams(text):
    s = _normalize_thread(text)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else ({s} if s else set())


def thread_similarity(a, b):
    """两条线程描述的（剥虚词后）bigram Jaccard 相似度（0-1）。精确相等直接 1.0。纯函数。"""
    a, b = str(a or "").strip(), str(b or "").strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ga, gb = _cjk_bigrams(a), _cjk_bigrams(b)
    if not ga or not gb:
        return 0.0
    inter = len(ga & gb)
    return inter / len(ga | gb) if inter else 0.0


def find_matching_thread(open_threads, thread, threshold=THREAD_MATCH_THRESHOLD):
    """在 open_threads 里找与 thread 最相似且过阈值的一条，返回其索引；无 → None。"""
    best_i, best_sim = None, threshold
    for i, ot in enumerate(open_threads):
        sim = thread_similarity(ot.get("thread"), thread)
        if sim >= best_sim:
            best_i, best_sim = i, sim
    return best_i


def get_delta_path(root, chapter):
    return os.path.join(root, "审稿", f"state_delta_第{chapter:02d}章.json")


def get_chapter_path(root, chapter):
    return os.path.join(root, "章节", f"第{chapter:02d}章.md")


def get_ledger_path(root):
    return os.path.join(root, "审稿", "state_ledger.json")


def get_ledger_lock_path(root):
    return os.path.join(root, "审稿", "state_ledger.lock")


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


def load_verification(path, chapter, expected_hashes=None, stamp_missing=False):
    """校验 LLM 核对结论 JSON。

    默认严格：结论必须自带与当前正文/delta 匹配的 hash（防止复用旧版本的 verification）。
    `stamp_missing=True`（由 `--stamp-hashes` 触发，供写后即时对账用）时：结论**缺**某个 hash
    则按当前文件自动盖章并标 `hash_source=script_stamped`，省去手抄 sha256；但结论里**已写**的
    hash 仍照常严格比对，写错/写旧照样拦。完整性核心（LLM 必须出 status=ok 且章号绑定）不变。
    """
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
    stamped = []
    for key, expected in expected_hashes.items():
        got = str(payload.get(key) or "").strip()
        if not got:
            if stamp_missing:
                payload[key] = expected
                stamped.append(key)
                continue
            return False, payload, f"核对结论缺少 {key}；不能复用未绑定正文/delta 的 verification。"
        if got != expected:
            return False, payload, f"核对结论 {key} 不匹配：verification={got}, current={expected}"
    if stamped:
        payload["hash_source"] = "script_stamped"
        payload["stamped_hashes"] = stamped
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
  "conflicts": [],
  "notes": "具体差异；若无差异写明 delta 与正文一致"
}}

如第 3 项发现正文/Delta 与 Master Ledger 既有约束**矛盾**（如已死角色再行动、能力代价被推翻、
设定自相矛盾），把每处冲突写进 `conflicts` 数组（如 `[{{"fact":"...","conflicts_with":"...","chapter":N}}]`）。
`conflicts` 非空时 status 不应为 ok——合并会被拒绝并落 `审稿/ledger_conflicts.json`，先解决冲突再对账。
"""
    return True, prompt


def merge_delta_to_ledger(root, chapter, verification=None):
    ledger_path = get_ledger_path(root)
    delta_path = get_delta_path(root, chapter)
    delta = load_json(delta_path)
    if not delta:
        return False, f"找不到增量文件：{delta_path}"

    # 冲突拦截：audit prompt 让 LLM 查一致性冲突，但此前 merge 只看 status=ok、从不读冲突结论，
    # 矛盾事实照单全收。若 verification 报了非空 conflicts，拒绝合并并落 审稿/ledger_conflicts.json，
    # 逼作者先解决冲突（而不是把矛盾事实写进 canonical 账本）。
    conflicts = (verification or {}).get("conflicts")
    if isinstance(conflicts, list) and conflicts:
        conflict_path = os.path.join(root, "审稿", "ledger_conflicts.json")
        os.makedirs(os.path.dirname(conflict_path), exist_ok=True)
        write_json(conflict_path, {
            "schema_version": 1,
            "kind": "novel_ledger_conflicts",
            "chapter": chapter,
            "recorded_at": date.today().isoformat(),
            "conflicts": conflicts,
        })
        return False, (f"核对结论报告了 {len(conflicts)} 处一致性冲突，已落 审稿/ledger_conflicts.json；"
                       "先解决冲突（改正文或 delta）再重新对账合并，避免矛盾事实进 canonical 账本。")

    with file_lock(get_ledger_lock_path(root)):
        ledger = load_json(ledger_path)
        if not ledger:
            # Initialize if missing.
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

        c_key = f"chapter_{chapter:02d}"
        if c_key in ledger.get("chapter_deltas", {}):
            print(f"[info] 第{chapter}章 已在账本中，正在覆盖更新...")

        # Merge facts.
        for fact in delta.get("new_facts", []):
            if fact not in ledger["setting_facts"]:
                ledger["setting_facts"].append(fact)

        # Merge characters.
        for char_change in delta.get("character_changes", []):
            name = char_change.get("name")
            if not name:
                continue
            if name not in ledger["characters"]:
                ledger["characters"][name] = {"history": [], "current_state": {}}
            ledger["characters"][name]["history"].append({
                "chapter": chapter,
                "change": char_change.get("change"),
                "state_update": char_change.get("state_update")
            })
            if char_change.get("state_update"):
                ledger["characters"][name]["current_state"].update(char_change["state_update"])

        # Merge threads.
        for thread in delta.get("open_threads_added", []):
            ledger["open_threads"].append({"chapter": chapter, "thread": thread})

        for thread in delta.get("threads_resolved", []):
            idx = find_matching_thread(ledger["open_threads"], thread)
            if idx is not None:
                matched = ledger["open_threads"].pop(idx)
                entry = {"chapter": chapter, "thread": thread}
                # 措辞不同但判为同一条时留痕，便于回溯是模糊匹配消解的
                if str(matched.get("thread")).strip() != str(thread).strip():
                    entry["matched_open_thread"] = matched.get("thread")
                    entry["match"] = "fuzzy"
                ledger["resolved_threads"].append(entry)
            else:
                ledger["resolved_threads"].append({"chapter": chapter, "thread": thread, "note": "direct resolve"})

        ledger["chapter_deltas"][c_key] = {
            "merged_at": date.today().isoformat(),
            "summary": delta,
            "verification": verification or {},
        }

        # 非线性改写检测：如果本次合并的章节号 < 已存在的最大章节号，
        # 说明这是一次回溯改写——标记所有下游章节的 delta 为 stale，
        # 提示需要重新对账（下游 delta 是基于旧版本上游状态合并的）。
        existing_keys = [k for k in ledger.get("chapter_deltas", {}) if k != c_key]
        downstream = sorted(
            int(m.group(1)) for key in existing_keys
            if (m := re.match(r"chapter_(\d+)", key)) and int(m.group(1)) > chapter
        )
        if downstream:
            for ds_ch in downstream:
                ds_key = f"chapter_{ds_ch:02d}"
                entry = ledger["chapter_deltas"].get(ds_key)
                if isinstance(entry, dict):
                    entry["stale"] = True
                    stale_sources = entry.setdefault("stale_sources", [])
                    if chapter not in stale_sources:
                        stale_sources.append(chapter)
            print(f"[info] 第{chapter}章非线性改写：已标记下游 "
                  f"第{downstream[0]}章–第{downstream[-1]}章 为 stale，建议重新对账。")

        ledger["updated_at"] = date.today().isoformat()

        write_json(ledger_path, ledger)
    return True, "合并完成"


def _compact_delta_summary(summary):
    """把一章 delta 大 blob 压成计数摘要（rollup 用）。"""
    if not isinstance(summary, dict):
        return {"rolled": True}
    def _count(key):
        v = summary.get(key)
        return len(v) if isinstance(v, list) else 0
    chars = sorted({cc["name"] for cc in (summary.get("character_changes") or [])
                    if isinstance(cc, dict) and cc.get("name")})
    return {
        "rolled": True,
        "new_facts": _count("new_facts"),
        "character_changes": _count("character_changes"),
        "characters_touched": chars,
        "open_threads_added": _count("open_threads_added"),
        "threads_resolved": _count("threads_resolved"),
    }


def rollup_ledger(root, before):
    """把章号 < before 的 chapter_deltas 大 blob 压成计数摘要（canonical 状态——
    characters/setting_facts/threads——一律不动），控制几百章后 state_ledger.json 线性膨胀。
    幂等：已 rolled 的章跳过。返回 (rolled_count, msg)。"""
    ledger_path = get_ledger_path(root)
    with file_lock(get_ledger_lock_path(root)):
        ledger = load_json(ledger_path)
        if not ledger:
            return 0, "无 state_ledger.json 可 rollup"
        deltas = ledger.get("chapter_deltas") or {}
        rolled = 0
        for key, entry in deltas.items():
            m = re.search(r"(\d+)", key)
            if not m or int(m.group(1)) >= before:
                continue
            if not isinstance(entry, dict):
                continue
            summary = entry.get("summary")
            if not isinstance(summary, dict) or summary.get("rolled"):
                continue
            entry["summary"] = _compact_delta_summary(summary)
            v = entry.get("verification")
            if isinstance(v, dict):
                # Keep hash bindings: qa_gate uses them to prove rolled chapters still
                # match the current chapter/delta files. Dropping them creates false
                # STATE-LEDGER-UNVERIFIED blockers after maintenance rollup.
                keep = {}
                for key in (
                    "chapter",
                    "status",
                    "verdict",
                    "result",
                    "chapter_file_hash",
                    "delta_hash",
                    "hash_source",
                    "stamped_hashes",
                ):
                    if key in v:
                        keep[key] = v[key]
                entry["verification"] = keep
            rolled += 1
        if rolled:
            ledger.setdefault("rollups", []).append(
                {"before_chapter": before, "rolled": rolled, "at": date.today().isoformat()})
            ledger["updated_at"] = date.today().isoformat()
            write_json(ledger_path, ledger)
        return rolled, f"已 rollup {rolled} 章逐章明细（canonical 状态保留）"


def main():
    ap = argparse.ArgumentParser(description="对账并合并小说状态账本")
    ap.add_argument("project_root")
    ap.add_argument("--chapter", type=int, help="章节号（audit/merge 必填）")
    ap.add_argument("--audit", action="store_true", help="输出对账 Prompt（需结合 LLM 使用）")
    ap.add_argument("--merge", action="store_true", help="将已验证 delta 合并入 master ledger")
    ap.add_argument("--verified", help="核对结论 JSON；需含 status/verdict/result=ok|passed|verified|通过")
    ap.add_argument("--stamp-hashes", action="store_true",
                    help="写后即时对账用：结论缺 hash 时按当前正文/delta 自动盖章合并，省去手抄 sha256（结论已写的 hash 仍严格比对）")
    ap.add_argument("--auto", action="store_true",
                    help="已废弃：只输出 audit prompt，不再自动合并未经验证的 delta")
    ap.add_argument("--rollup", action="store_true",
                    help="维护：压缩旧章逐章明细控制账本膨胀（canonical 状态不动），需配 --before")
    ap.add_argument("--before", type=int, help="rollup：压缩章号 < 此值的逐章明细")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    # rollup 是账本维护操作，不针对单章，单独处理（不要求 --chapter / 章节文件存在）。
    if args.rollup:
        if args.before is None:
            print("[err] --rollup 需配 --before <章号>：压缩章号 < 该值的逐章明细。", file=sys.stderr)
            sys.exit(2)
        rolled, msg = rollup_ledger(root, args.before)
        print(f"[ok] {msg}")
        return

    if args.chapter is None:
        print("[err] audit/merge 需 --chapter <章号>。", file=sys.stderr)
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
        job = None
        if semantic_job is not None:
            delta_path = get_delta_path(root, args.chapter)
            expected_hashes = expected_verification_hashes(root, args.chapter)
            response_rel = os.path.join("审稿", f"state_verify_第{args.chapter:02d}章.json")
            complete_cmd = (
                f'python3 skills/novel-craft/scripts/reconcile_ledger.py "{root}" '
                f'--chapter {args.chapter} --merge --verified "{os.path.join(root, response_rel)}" --stamp-hashes'
            )
            job = semantic_job.create_job(
                root,
                semantic_kind="ledger_reconcile",
                prompt=res,
                response_out=response_rel,
                required_fields=["chapter", "status", "notes"],
                schema_ref="ledger_reconcile",
                source_snapshot={
                    "chapter": args.chapter,
                    "chapter_path": os.path.relpath(chapter_file, root).replace(os.sep, "/"),
                    "delta_path": os.path.relpath(delta_path, root).replace(os.sep, "/"),
                    **expected_hashes,
                },
                complete_command=complete_cmd,
                metadata={
                    "chapter": args.chapter,
                    "delta_path": os.path.relpath(delta_path, root).replace(os.sep, "/"),
                },
            )
        print("--- LEDGER RECONCILE PROMPT ---")
        print(res)
        print("--- END PROMPT ---")
        if job:
            print(f"[info] 语义任务已写入：{job['job_path']}")
            print(f"[info] 让 AI 代理读取 {os.path.join(root, job['prompt_path'])} 并写回 {os.path.join(root, job['response_out'])}。")
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
        verified, verification, msg = load_verification(
            args.verified, args.chapter, expected_hashes, stamp_missing=args.stamp_hashes)
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
