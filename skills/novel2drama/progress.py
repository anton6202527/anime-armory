#!/usr/bin/env python3
# novel2drama 确定性路由 + 进度回写：读/写 <作品根>/_进度.md
# 用法:
#   python3 progress.py <作品根>                    # 全局：最小未完成集 + 各阶段卡集数
#   python3 progress.py <作品根> 第N集              # 查指定集所处阶段 + 推荐命令
#   python3 progress.py set <作品根> 第N集 <列名> <值>   # 回写某列(✅ / ⬜ / ⏳rough / 12/19)，各 skill 收尾调用
#   python3 progress.py ensure-col <作品根> <列名> [默认值] # 旧项目迁移：缺列则追加到「成片」前
#   python3 progress.py audit-placeholders <作品根> [--fix] # 扫/修旧项目「配音=✅ 但清单仍占位」
import contextlib, sys, os, re, time

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common'))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import write_episode_manifest
from n2d_route import STAGES, cell_state, format_route, is_episode_row, parse_progress, progress_path, stage_of, summarize, voice_is_placeholder

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

def do_set(root, ep, col, val):
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
        preferred_before = {'视频prompt': '视频'}
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
    root = sys.argv[1].rstrip('/'); only = sys.argv[2] if len(sys.argv) > 2 else None
    header, rows = parse(root)
    if only:
        r = next((x for x in rows if x['_ep'] == only), None)
        if not r: print(f"{only} 不在进度表"); sys.exit(1)
        route = stage_of(root, r, header)
        print(format_route(root, route))
        if route.get('note'):
            print(f"  ⚠️ {route['note']}")
        return
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
        order = [s[1] for s in STAGES] + ['补真实配音', '✅已成片']
        items = sorted(bottleneck.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
        print("各阶段卡集数: " + " · ".join(f"{k}={v}" for k, v in items))

if __name__ == '__main__':
    main()
