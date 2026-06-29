#!/usr/bin/env python3
# n2d 确定性路由 + 进度回写：读/写 <作品根>/_进度.md
# 用法:
#   python3 progress.py <作品根> [--refresh-identity] # 全局：最小未完成集 + 各阶段卡集数
#   python3 progress.py <作品根> 第N集              # 查指定集所处阶段 + 推荐命令
#   python3 progress.py set <作品根> 第N集 <列名> <值>   # 回写某列(✅ / ⬜ / ⏳rough / 12/19)，各 skill 收尾调用
#   python3 progress.py ensure-col <作品根> <列名> [默认值] # 旧项目迁移：缺列则追加到「成片」前
#   python3 progress.py audit-placeholders <作品根> [--fix] # 扫/修旧项目「配音=✅ 但清单仍占位」
import contextlib, sys, os, re, time

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'n2d', '_lib'))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import contract_version_report, write_episode_manifest
from n2d_route import STAGES, cell_state, format_route, is_episode_row, parse_progress, progress_path, stage_of, summarize, voice_is_placeholder

# H1 fail-closed 兜底常量（2026-06-28）：gate_receipt 模块若导入失败仍需识别受闸列 + 写同一 waiver 账本。
# 与 gate_receipt.ENFORCED_COLUMN_GATE_STAGE / ALLOW_ENV / WAIVER_LEDGER 同源复刻，
# test_progress_receipt_failclosed 守护其与 gate_receipt 不漂移。
_GATED_COLUMN_STAGE_FALLBACK = {"出图": "image", "视频": "video", "成片": "compose", "验收": "review"}
_GATED_COLUMNS_FALLBACK = frozenset(_GATED_COLUMN_STAGE_FALLBACK)
_PROGRESS_ALLOW_ENV = "N2D_PROGRESS_ALLOW_UNVERIFIED"
_UNVERIFIED_WAIVER_LEDGER = "progress_unverified_waivers.jsonl"


def _append_unverified_waiver_fallback(root, ep, col, val, reason):
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
        "code": "gate_receipt_unavailable",
        "reason": reason,
        "message": f"gate_receipt 模块不可加载，{_PROGRESS_ALLOW_ENV}=1 强行回写「{col}」={val}（欠债）。",
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


def do_set(root, ep, col, val):
    _verify_gate_receipt(root, ep, col, val)
    p = prog_path(root)
    with progress_lock(root):
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
    keys = ["制作模式", "生图AI", "生视频模型", "生视频渠道", "视频模型路由", "配音后端", "字幕语言"]
    
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
    print(f"成片完成: {done}/{len(rows)}")
    if first:
        print(f"下一步（最小未完成集）: {format_route(root, first)}")
        if first.get('note'):
            print(f"  ⚠️ {first['note']}")
    else: print("🎉 全部成片完成")
    if bottleneck:
        order = [s[1] for s in STAGES] + ['补真实配音', '✅已验收']
        items = sorted(bottleneck.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
        print("各阶段卡集数: " + " · ".join(f"{k}={v}" for k, v in items))


if __name__ == '__main__':
    main()
