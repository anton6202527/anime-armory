#!/usr/bin/env python3
# n2d 确定性路由 + 进度回写：读/写 <作品根>/_进度.md
# 用法:
#   python3 progress.py <作品根> [--refresh-identity] # 全局：最小未完成集 + 各阶段卡集数
#   python3 progress.py <作品根> 第N集              # 查指定集所处阶段 + 推荐命令
#   python3 progress.py set <作品根> 第N集 <列名> <值>   # 回写某列(✅ / ⬜ / ⏳rough / 12/19)，各 skill 收尾调用
#   python3 progress.py ensure-col <作品根> <列名> [默认值] # 旧项目迁移：缺列则追加到「成片」前
#   python3 progress.py audit-placeholders <作品根> [--fix] # 扫/修旧项目「配音=✅ 但清单仍占位」
#   python3 progress.py audit-dag <作品根> [--json]         # 扫状态 DAG：下游已动但上游非法直接红灯
import contextlib, sys, os, re, time, json

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'n2d', '_lib'))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import contract_version_report, write_episode_manifest
from n2d_route import STAGES, cell_state, flow_columns, format_route, is_episode_row, parse_progress, progress_path, stage_of, summarize, voice_is_placeholder, is_progress_satisfied
try:
    from settings import is_hybrid_routing, is_native_av, is_video_first
except ImportError:
    from n2d_settings import is_hybrid_routing, is_native_av, is_video_first

# H1 fail-closed 兜底常量（2026-06-28）：gate_receipt 模块若导入失败仍需识别受闸列 + 写同一 waiver 账本。
# 与 gate_receipt.ENFORCED_COLUMN_GATE_STAGE / ALLOW_ENV / WAIVER_LEDGER 同源复刻，
# test_progress_receipt_failclosed 守护其与 gate_receipt 不漂移。
_GATED_COLUMN_STAGE_FALLBACK = {"出图": "image", "视频": "video", "成片": "compose", "验收": "review"}
_GATED_COLUMNS_FALLBACK = frozenset(_GATED_COLUMN_STAGE_FALLBACK)
_PROGRESS_ALLOW_ENV = "N2D_PROGRESS_ALLOW_UNVERIFIED"
_UNVERIFIED_WAIVER_LEDGER = "progress_unverified_waivers.jsonl"


def _append_unverified_waiver_fallback(root, ep, col, val, reason, code="gate_receipt_unavailable"):
    """gate_receipt 不可加载时的最小留痕：往同一 waiver 账本 append 一行（schema 兼容 gate_receipt
    的 unresolved_waivers：带 episode + gate_stage，使日后模块恢复跑闸能自动销账）。"""
    import json as _json
    from datetime import datetime, timezone
    d = os.path.join(root, "生产数据")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, _UNVERIFIED_WAIVER_LEDGER)
    rec = {
        "kind": "n2d_progress_unverified_waiver",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "episode": ep,
        "column": col,
        "gate_stage": _GATED_COLUMN_STAGE_FALLBACK.get(col, ""),
        "code": code,
        "reason": reason,
        "message": f"{_PROGRESS_ALLOW_ENV}=1 强行回写「{col}」={val}（欠债·{code}）。",
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(_json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def prog_path(root):
    return progress_path(root)


@contextlib.contextmanager
def progress_lock(root, timeout=30.0, poll=0.1):
    """Serialize read-modify-write of `_进度.md` for single-machine multi-worker runs."""
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, "_进度.lock")
    start = time.time()
    if fcntl is not None:
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() - start > timeout:
                        raise TimeoutError(f"progress lock timeout ({timeout}s): {path}")
                    time.sleep(poll)
            yield path
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
    else:
        lock_dir = path + ".d"
        acquired = False
        try:
            while True:
                try:
                    os.mkdir(lock_dir)
                    acquired = True
                    break
                except FileExistsError:
                    if time.time() - start > timeout:
                        raise TimeoutError(f"progress lock timeout ({timeout}s): {path}")
                    time.sleep(poll)
            open(path, "a", encoding="utf-8").close()
            yield path
        finally:
            if acquired:
                try:
                    os.rmdir(lock_dir)
                except OSError:
                    pass


def atomic_write_text(path, text):
    """Same-directory temp + replace; readers never see half-written progress."""
    directory = os.path.dirname(path) or "."
    tmp = os.path.join(directory, f".{os.path.basename(path)}.tmp.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)

def parse(root):
    try:
        return parse_progress(root)
    except FileNotFoundError as e:
        print(f"找不到 {e.args[0]}"); sys.exit(1)
    except ValueError as e:
        print(str(e)); sys.exit(1)

def _verify_gate_receipt(root, ep, col, val):
    """凭据耦合：受闸列写 ✅ 前必须有「真跑过 + 真绿 + 指纹新鲜」的闸门凭据。

    fail-closed——缺/陈旧/无指纹凭据都拒绝回写；唯一逃生口 N2D_PROGRESS_ALLOW_UNVERIFIED=1
    会留痕 waiver（不静默放行）。consistency 只收紧不松动。
    """
    try:
        from gate_receipt import allow_override, check_advance, record_waiver
    except Exception as e:  # 凭据模块缺失不应静默放行受闸列，但也不能误伤非受闸列
        # H1 fail-closed（2026-06-28）：此前这里直接 return，等于凭据模块一坏整条受闸耦合静默失效
        # ——"闸在但不响"。改成：受闸列(出图/视频/成片/验收)的完成态(✅)写入必须拒绝；非受闸列/非完成态
        # 照常放行不误伤。唯一逃生口仍是 N2D_PROGRESS_ALLOW_UNVERIFIED=1（留痕欠债，验收 reconcile 会再抓）。
        gated_done = col in _GATED_COLUMNS_FALLBACK and cell_state(val) == "done"
        if not gated_done:
            return
        if os.environ.get(_PROGRESS_ALLOW_ENV) == "1":
            wpath = _append_unverified_waiver_fallback(root, ep, col, val, f"gate_receipt 不可加载（{e}）")
            print(f"⚠️ gate_receipt 不可加载，但 {_PROGRESS_ALLOW_ENV}=1 强行回写「{col}」✅；"
                  f"已留痕欠债 → {os.path.relpath(wpath, root)}（验收 reconcile 会复核）。")
            return
        print(f"⛔ 拒绝回写 {ep}「{col}」= {val}：gate_receipt 凭据模块不可加载（{e}）；"
              f"受闸列不静默放行（H1 fail-closed·一致性只收紧不松动）。")
        print(f"   修复模块后重试；确属离线兜底可设 {_PROGRESS_ALLOW_ENV}=1 强行回写并留痕。")
        sys.exit(2)
    verdict = check_advance(root, ep, col, val)
    if verdict.ok:
        if verdict.code == "verified":
            print(f"  🔒 {verdict.message}")
        return
    if allow_override():
        path = record_waiver(root, ep, col, verdict)
        print(f"⚠️ 未验证强行回写「{col}」✅（{verdict.code}）：{verdict.message}")
        print(f"   已留痕 waiver → {os.path.relpath(path, root)}（这是欠下的一致性债，验收会汇总）。")
        return
    print(f"⛔ 拒绝回写 {ep}「{col}」= {val}：{verdict.message}")
    print("   （确属误判/离线兜底可设 N2D_PROGRESS_ALLOW_UNVERIFIED=1 强行回写并留痕，但默认不松动一致性。）")
    sys.exit(2)


def _verify_dag_prereqs(root, ep, col, val):
    """DAG 前驱校验：向任何列写「完成态 ✅」前，STAGE_GRAPH 前驱列必须已满足。

    audit-dag 只能事后抓乱序，这里把同一判据前移到回写时 fail-closed——上游未完成时
    拒绝置下游 ✅。非完成态（⬜/⏳rough/12/19/—/na）不拦；逃生口与凭据耦合同一口径：
    N2D_PROGRESS_ALLOW_UNVERIFIED=1 强行回写并留痕 waiver（欠债，验收 reconcile 复核）。
    """
    if cell_state(val) != "done":
        return
    prereqs = _dag_prereqs_for(col)
    if not prereqs:
        return
    try:
        header, rows = parse_progress(root)
    except Exception:
        return  # 表读不出/不存在时交给 do_set 自身按原路径报错
    ep_norm = str(ep).strip()
    row = next((r for r in rows
                if str(r.get("_ep") or r.get("集") or "").strip() == ep_norm), None)
    if row is None:
        return  # ep 不在表里由 do_set 报错
    colset = set(header)
    gaps = []
    for prereq in prereqs:
        if prereq not in colset:
            continue  # 旧项目缺列不误伤（ensure-col 迁移前按不存在处理）
        if not _dag_prereq_satisfied(root, row, col, prereq):
            gaps.append((prereq, row.get(prereq, ""), _dag_expected_for(root, col, prereq)))
    if not gaps:
        return
    detail = "；".join(f"「{p}」当前={v or '⬜'}（要求：{exp}）" for p, v, exp in gaps)
    if os.environ.get(_PROGRESS_ALLOW_ENV) == "1":
        wpath = _append_unverified_waiver_fallback(
            root, ep, col, val, f"DAG 前驱未满足强行回写：{detail}", code="dag_prereq_unsatisfied")
        print(f"⚠️ DAG 前驱未满足，但 {_PROGRESS_ALLOW_ENV}=1 强行回写 {ep}「{col}」={val}；"
              f"已留痕欠债 → {os.path.relpath(wpath, root)}（验收 reconcile 会复核）。")
        return
    print(f"⛔ 拒绝回写 {ep}「{col}」= {val}：上游前驱未满足——{detail}")
    print(f"   先完成前驱列，或确属特殊路线时设 {_PROGRESS_ALLOW_ENV}=1 强行回写并留痕（欠债）。")
    sys.exit(2)


def do_set(root, ep, col, val):
    p = prog_path(root)
    with progress_lock(root):
        # 凭据/DAG 校验移入锁内：`_verify_dag_prereqs` 读 `_进度.md` 判上游列，必须与随后的
        # 写入对**同一快照**原子。否则并发 worker（batch runner --limit>1）或 update_plan 回滚
        # 会在「读校验」与「加锁写入」之间改动上游列 → 校验基于陈旧快照通过，却写下压在非法
        # 上游之上的下游 ✅（TOCTOU）。progress_lock 文档承诺 serialize read-modify-write——
        # read（校验读表）此前漏在锁外，此处补齐。两个校验均不自持锁、失败 sys.exit(2)（经 finally
        # 正常释放锁），移入安全。
        _verify_gate_receipt(root, ep, col, val)
        _verify_dag_prereqs(root, ep, col, val)
        lines = open(p, encoding='utf-8').read().split('\n')
        header = None; hidx = {}
        for i, ln in enumerate(lines):
            if ln.startswith('| 集 |'):
                header = [c.strip() for c in ln.split('|')[1:-1]]
                hidx = {name: j for j, name in enumerate(header)}
        if header is None or col not in hidx:
            print(f"列名 '{col}' 不在表头：{header}"); sys.exit(1)
        ci = hidx[col]  # 含 集/字数 在内的列下标
        out = []; hit = False
        for ln in lines:
            m = re.match(r'^\|\s*' + re.escape(ep) + r'\s*\|', ln)
            if m:
                parts = ln.split('|')  # ['', 集, 字数, cells..., (note)]
                # parts[1]=集, parts[2]=字数, 物料列从 parts[3] 起；header[0]=集 → ci 对应 parts[ci+1]
                tgt = ci + 1
                if tgt < len(parts):
                    parts[tgt] = f' {val} '
                    ln = '|'.join(parts); hit = True
            out.append(ln)
        if not hit: print(f"{ep} 不在进度表"); sys.exit(1)
        atomic_write_text(p, '\n'.join(out))
        # manifest 快照写在锁内：与表格写入原子，避免并发 set 交错产生错配快照
        try:
            write_episode_manifest(
                root,
                ep,
                extra={"last_progress_column": col, "last_progress_value": val, "last_progress_state": cell_state(val)},
            )
        except Exception as e:
            print(f"⚠️ manifest 快照写入失败：{e}")
    print(f"✅ 回写 {ep} 「{col}」= {val}")

def _split_row(ln):
    return [c.strip() for c in ln.split('|')[1:-1]]

def _row_trailing(ln):
    # 末尾 `|` 之后的行尾备注（如 `|（开局即高潮）`）；ensure-col 重建行时原样保回，避免吞注释
    parts = ln.split('|')
    return parts[-1] if len(parts) >= 2 else ''

def do_ensure_col(root, col, default='⬜'):
    p = prog_path(root)
    with progress_lock(root):
        lines = open(p, encoding='utf-8').read().split('\n')
        header = None
        insert_at = None
        for ln in lines:
            if ln.startswith('| 集 |'):
                header = _split_row(ln)
                break
        if header is None:
            print("未找到表头（| 集 | …）"); sys.exit(1)
        if col in header:
            print(f"✅ 列已存在：{col}"); return
        preferred_before = {'视频prompt': '视频', '出图prompt': '出图'}
        preferred_after = {'验收': '成片'}
        if col in preferred_after and preferred_after[col] in header:
            insert_at = header.index(preferred_after[col]) + 1
        else:
            before = preferred_before.get(col, '成片')
            insert_at = header.index(before) if before in header else (header.index('成片') if '成片' in header else len(header))

        out = []
        for ln in lines:
            if ln.startswith('| 集 |') or re.match(r'^\|\s*-+', ln):
                cells = _split_row(ln); trailing = _row_trailing(ln)
                filler = '---' if re.match(r'^\|\s*-+', ln) else col
                cells.insert(insert_at, filler)
                out.append('| ' + ' | '.join(cells) + ' |' + trailing)
            elif is_episode_row(ln):
                cells = _split_row(ln); trailing = _row_trailing(ln)
                while len(cells) < len(header):
                    cells.append('')
                cells.insert(insert_at, default)
                out.append('| ' + ' | '.join(cells) + ' |' + trailing)
            else:
                out.append(ln)
        atomic_write_text(p, '\n'.join(out))
    print(f"✅ 已追加列「{col}」（默认 {default}）")

def do_audit_placeholders(root, fix=False):
    header, rows = parse(root)
    if "配音" not in header:
        print("未找到「配音」列"); return
    issues = []
    for row in rows:
        ep = row.get("_ep") or row.get("集") or ""
        if row.get("配音") == "✅" and voice_is_placeholder(root, ep) is True:
            issues.append(ep)
    if not issues:
        print("✅ 未发现旧占位配音伪完成（配音=✅ 且 manifest 占位）"); return
    print("⚠️ 发现旧占位配音伪完成：" + "、".join(issues))
    if not fix:
        print("提示：加 --fix 可把这些集的「配音」降级为 ⏳rough。")
        return
    for ep in issues:
        do_set(root, ep, "配音", "⏳rough")

def _acceptance_state_issues(root, header, rows):
    if "验收" not in header:
        return []
    meta = {"集", "字数", "序号", "#"}
    required = [c for c in header if c not in meta and c != "验收"]
    issues = []
    native_av = is_native_av(root)
    for row in rows:
        ep = row.get("_ep") or row.get("集") or ""
        if cell_state(row.get("验收", "")) != "done":
            continue
        missing = []
        for col in required:
            # 原生音画的逐句配音是可选旁白层；其他制作模式下，验收必须是真配音完成，
            # video-first 的 ⏳rough 只允许推进到视频，不能算最终验收完成。
            if col == "配音":
                if native_av:
                    continue
                if cell_state(row.get(col, "")) not in ("done", "na"):
                    missing.append(col)
                continue
            if not is_progress_satisfied(root, row, col):
                missing.append(col)
        if missing:
            issues.append({"episode": ep, "missing": missing})
    return issues


_DAG_STARTED_STATES = {"done", "partial", "rough", "manual-waived", "stale"}
_DAG_STRICT_VOICE_TARGETS = {"成片", "验收"}
_DAG_CORE_ORDER = [
    "raw",
    "剧本改编",
    "bgm",
    "封面",
    "配音",
    "分镜设计",
    "素材清单",
    "字幕中",
    "字幕英",
    "奇观连续性",
    "出图prompt",
    "出图",
    "视频prompt",
    "视频",
    "成片",
    "验收",
]
_DAG_PREREQS = {
    "剧本改编": ["raw"],
    "bgm": ["raw"],
    "封面": ["raw"],
    "配音": ["剧本改编", "bgm", "封面"],
    "分镜设计": ["剧本改编", "bgm", "封面", "配音"],
    "素材清单": ["剧本改编", "bgm", "封面", "配音", "分镜设计"],
    "字幕中": ["剧本改编", "配音"],
    "字幕英": ["剧本改编", "配音"],
    "奇观连续性": ["分镜设计", "素材清单"],
    "出图prompt": ["分镜设计", "素材清单", "字幕中", "奇观连续性"],
    "出图": ["出图prompt"],
    "视频prompt": ["出图", "出图prompt"],
    "视频": ["视频prompt", "出图"],
    "成片": ["视频", "配音"],
    "验收": ["成片", "配音"],
}


def progress_audit_state(value):
    """Cell state for audits, preserving user-visible exception markers.

    The router keeps unknown text as todo.  Audits need finer labels so humans can
    see whether a column is truly complete, rough, explicitly waived, or stale.
    """
    text = (value or "").strip()
    low = text.lower()
    if any(token in low for token in ("manual-waived", "manual_waived", "waived")) or "豁免" in text or "人工放行" in text:
        return "manual-waived"
    if "stale" in low or "过期" in text or "陈旧" in text:
        return "stale"
    return cell_state(text)


def _dag_columns(header):
    available = [c for c in _DAG_CORE_ORDER if c in header]
    extras = [c for c in flow_columns(header) if c not in available]
    return available + extras


def _dag_expected_for(root, target_col, prereq):
    if prereq == "配音":
        if is_native_av(root):
            return "可选（原生音画模式）"
        if (is_video_first(root) or is_hybrid_routing(root)) and target_col not in _DAG_STRICT_VOICE_TARGETS:
            return "✅ 或 ⏳rough（前中段可用无 WAV 时间基准；最终交付仍需声音签收）"
        return "✅ 真完成（最终交付不得用 ⏳rough）"
    return "✅ / N/A"


def _dag_prereq_satisfied(root, row, target_col, prereq):
    state = progress_audit_state(row.get(prereq, ""))
    if prereq == "配音":
        if is_native_av(root):
            return True
        if state == "stale":
            return False
        if (is_video_first(root) or is_hybrid_routing(root)) and target_col not in _DAG_STRICT_VOICE_TARGETS:
            return state in ("done", "rough", "na")
        return state in ("done", "na")
    if state in ("stale", "manual-waived"):
        return False
    return state in ("done", "na")


def _dag_prereqs_for(col):
    return list(_DAG_PREREQS.get(col, []))


def _dag_state_issues(root, header, rows):
    """Return downstream-started/upstream-illegal progress DAG issues.

    This is intentionally stricter than routing: a routing frontier can say "go do
    voice now", while a DAG audit says "do not trust downstream ✅ already written
    under an illegal upstream state".
    """
    cols = _dag_columns(header)
    colset = set(cols)
    issues = []
    for row in rows:
        ep = row.get("_ep") or row.get("集") or ""
        for col in cols:
            state = progress_audit_state(row.get(col, ""))
            if state not in _DAG_STARTED_STATES:
                continue
            prereqs = [p for p in _dag_prereqs_for(col) if p in colset]
            if state == "stale":
                issues.append({
                    "episode": ep,
                    "column": col,
                    "value": row.get(col, ""),
                    "column_state": state,
                    "prereq": col,
                    "prereq_value": row.get(col, ""),
                    "prereq_state": state,
                    "expected": "当前列证据新鲜",
                    "severity": "block",
                    "reason": "stale_progress_cell",
                })
            if state == "manual-waived":
                issues.append({
                    "episode": ep,
                    "column": col,
                    "value": row.get(col, ""),
                    "column_state": state,
                    "prereq": col,
                    "prereq_value": row.get(col, ""),
                    "prereq_state": state,
                    "expected": "真实完成凭据或显式 waiver 账本",
                    "severity": "warn",
                    "reason": "manual_waiver_needs_reconcile",
                })
            for prereq in prereqs:
                if _dag_prereq_satisfied(root, row, col, prereq):
                    continue
                issues.append({
                    "episode": ep,
                    "column": col,
                    "value": row.get(col, ""),
                    "column_state": state,
                    "prereq": prereq,
                    "prereq_value": row.get(prereq, ""),
                    "prereq_state": progress_audit_state(row.get(prereq, "")),
                    "expected": _dag_expected_for(root, col, prereq),
                    "severity": "block",
                    "reason": "downstream_started_before_prereq",
                })
    return issues


def _dag_summary(issues):
    out = {"total": len(issues), "block": 0, "warn": 0, "rough": 0, "manual-waived": 0, "stale": 0}
    for item in issues:
        sev = item.get("severity") or "warn"
        out[sev] = out.get(sev, 0) + 1
        state = item.get("column_state")
        if state in ("rough", "manual-waived", "stale"):
            out[state] = out.get(state, 0) + 1
        pstate = item.get("prereq_state")
        if pstate in ("rough", "manual-waived", "stale"):
            out[pstate] = out.get(pstate, 0) + 1
    return out


def do_audit_dag(root, json_out=False):
    header, rows = parse(root)
    issues = _dag_state_issues(root, header, rows)
    payload = {
        "kind": "n2d_progress_dag_audit",
        "version": 1,
        "root": root,
        "status": "blocked" if any(i.get("severity") == "block" for i in issues) else ("warn" if issues else "pass"),
        "summary": _dag_summary(issues),
        "issues": issues,
    }
    if json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif not issues:
        print("✅ progress DAG 通过：未发现下游已动但上游非法的状态。")
    else:
        print("⛔ progress DAG 红灯：" if payload["status"] == "blocked" else "⚠️ progress DAG 有人工豁免待复核：")
        for item in issues[:20]:
            print(
                f"  - {item['episode']}「{item['column']}」={item.get('value') or '∅'} "
                f"({item['column_state']}) 依赖「{item['prereq']}」={item.get('prereq_value') or '∅'} "
                f"({item['prereq_state']})，期望 {item['expected']}。"
            )
        if len(issues) > 20:
            print(f"  ... 另有 {len(issues) - 20} 条，使用 --json 查看全量。")
    if payload["status"] == "blocked":
        sys.exit(2)

def do_audit_acceptance(root, fix=False):
    header, rows = parse(root)
    issues = _acceptance_state_issues(root, header, rows)
    if not issues:
        print("✅ 未发现验收假绿（验收=✅ 但上游列未完成）"); return
    print("⚠️ 发现验收假绿：")
    for item in issues:
        print(f"  - {item['episode']}: 验收=✅，但未完成/未满足：{', '.join(item['missing'])}")
    if not fix:
        print("提示：加 --fix 可把这些集的「验收」降级为 ⬜，重新进入 n2d-review。")
        return
    for item in issues:
        do_set(root, item["episode"], "验收", "⬜")

def warn_acceptance_consistency(root, header, rows):
    issues = _acceptance_state_issues(root, header, rows)
    if not issues:
        return
    chunks = [f"{i['episode']}缺 {','.join(i['missing'])}" for i in issues[:3]]
    more = f" 等 {len(issues)} 集" if len(issues) > 3 else ""
    print("⚠️ 验收状态不一致：" + "；".join(chunks) + more)
    print(f"   可运行：python3 skills/n2d/progress.py audit-acceptance '{root}' --fix")


def warn_dag_consistency(root, header, rows):
    issues = _dag_state_issues(root, header, rows)
    blocking = [i for i in issues if i.get("severity") == "block"]
    if not issues:
        return
    source = blocking or issues
    chunks = [f"{i['episode']}「{i['column']}」缺/非法「{i['prereq']}」" for i in source[:3]]
    more = f" 等 {len(source)} 条" if len(source) > 3 else ""
    prefix = "⛔ progress DAG 红灯：" if blocking else "⚠️ progress DAG 待复核："
    print(prefix + "；".join(chunks) + more)
    print(f"   可运行：python3 skills/n2d/progress.py audit-dag '{root}' --json")


def warn_contract_version(root):
    try:
        report = contract_version_report(root)
    except Exception:
        return
    if report.get("status") == "current":
        return
    stale = report.get("stale_or_missing", 0)
    future = report.get("future", 0)
    if future:
        print(f"⚠️ 发现 {future} 个 manifest schema_version 高于当前代码契约；请先更新 skills 后再继续。")
    elif stale:
        print(f"⚠️ 发现 {stale} 个 manifest 缺失或 schema_version 落后；建议先跑：python3 skills/n2d/_lib/n2d_contract.py migrate-version '{root}'")

def print_active_settings(root):
    try:
        from settings import load_settings, get_setting, DEFAULTS
    except ImportError:
        from n2d_settings import load_settings, get_setting, DEFAULTS
    
    # 核心关注的选择点
    keys = ["制作模式", "合成阶段", "生图AI", "生视频模型", "生视频渠道", "视频模型路由", "配音后端", "字幕语言"]
    
    print("\n--- 生效设置 (Active Settings) ---")
    for k in keys:
        val = get_setting(root, k)
        is_default = (val == DEFAULTS.get(k))
        suffix = " (默认)" if is_default else ""
        print(f"  {k}: {val}{suffix}")
    print("----------------------------------\n")

def auto_update_identity_matrix(root):
    """静默检查并更新身份矩阵，减少 image/video 阶段前的人工操作。"""
    matrix_path = os.path.join(root, "生产数据", "identity_adapter_matrix.json")
    registry_path = os.path.join(root, "出图", "共享", "identity_registry.json")
    
    if not os.path.exists(registry_path):
        return

    # 检查矩阵是否过期（按修改时间）
    stale = False
    if not os.path.exists(matrix_path):
        stale = True
    elif os.path.getmtime(registry_path) > os.path.getmtime(matrix_path):
        stale = True
        
    if stale:
        print("  🔄 检测到身份注册表更新，正在静默刷新身份矩阵...")
        script = os.path.join(os.path.dirname(__file__), "..", "n2d-identity", "scripts", "identity.py")
        if os.path.exists(script):
            import subprocess
            try:
                subprocess.run([sys.executable, script, root, "--write"], capture_output=True, check=True)
                print("  ✅ 身份矩阵已同步。")
            except Exception as e:
                print(f"  ⚠️ 身份矩阵同步失败：{e}")

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == 'set':
        if len(sys.argv) != 6:
            print("用法: progress.py set <作品根> 第N集 <列名> <值>"); sys.exit(1)
        do_set(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]); return
    if len(sys.argv) >= 2 and sys.argv[1] == 'ensure-col':
        if len(sys.argv) not in (4, 5):
            print("用法: progress.py ensure-col <作品根> <列名> [默认值]"); sys.exit(1)
        do_ensure_col(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else '⬜'); return
    if len(sys.argv) >= 2 and sys.argv[1] == 'audit-placeholders':
        if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != '--fix'):
            print("用法: progress.py audit-placeholders <作品根> [--fix]"); sys.exit(1)
        do_audit_placeholders(sys.argv[2], fix=len(sys.argv) == 4); return
    if len(sys.argv) >= 2 and sys.argv[1] == 'audit-acceptance':
        if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != '--fix'):
            print("用法: progress.py audit-acceptance <作品根> [--fix]"); sys.exit(1)
        do_audit_acceptance(sys.argv[2], fix=len(sys.argv) == 4); return
    if len(sys.argv) >= 2 and sys.argv[1] == 'audit-dag':
        if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != '--json'):
            print("用法: progress.py audit-dag <作品根> [--json]"); sys.exit(1)
        do_audit_dag(sys.argv[2], json_out=len(sys.argv) == 4); return
    args = sys.argv[1:]
    refresh_identity = False
    if "--refresh-identity" in args:
        refresh_identity = True
        args.remove("--refresh-identity")
    if not args:
        print("用法: progress.py <作品根> [第N集] [--refresh-identity]"); sys.exit(1)
    root = args[0].rstrip('/'); only = args[1] if len(args) > 1 else None
    header, rows = parse(root)
    warn_contract_version(root)
    warn_acceptance_consistency(root, header, rows)
    warn_dag_consistency(root, header, rows)
    
    if refresh_identity:
        auto_update_identity_matrix(root)

    if only:
        r = next((x for x in rows if x['_ep'] == only), None)
        if not r: print(f"{only} 不在进度表"); sys.exit(1)
        route = stage_of(root, r, header)
        print(format_route(root, route))
        if route.get('note'):
            print(f"  ⚠️ {route['note']}")
        return
    
    # 打印全局状态前先显示设置概览
    print_active_settings(root)
    
    summary = summarize(root)
    done = summary["done"]; bottleneck = summary["bottleneck"]; first = summary["first"]
    print(f"作品: {os.path.basename(root)}（共 {len(rows)} 集）")
    print(f"主流程完成: {done}/{len(rows)}")
    if first:
        print(f"下一步（最小未完成集）: {format_route(root, first)}")
        if first.get('note'):
            print(f"  ⚠️ {first['note']}")
    else: print("🎉 全部主流程完成")
    if bottleneck:
        order = [s[1] for s in STAGES] + ['补真实配音', '✅已验收']
        items = sorted(bottleneck.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
        print("各阶段卡集数: " + " · ".join(f"{k}={v}" for k, v in items))


if __name__ == '__main__':
    main()
