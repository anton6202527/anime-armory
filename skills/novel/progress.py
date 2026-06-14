#!/usr/bin/env python3
# novel 确定性路由 + 进度回写：读/写 <作品根>/_进度.md
import contextlib, sys, os, re, time

try:
    import fcntl
except ImportError:
    fcntl = None

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '_lib'))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from novel_route import STAGES, cell_state, format_route, parse_progress, progress_path, stage_of, summarize, chapter_number

def prog_path(root):
    return progress_path(root)

@contextlib.contextmanager
def progress_lock(root, timeout=30.0, poll=0.1):
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
    directory = os.path.dirname(path) or "."
    tmp = os.path.join(directory, f".{os.path.basename(path)}.tmp.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)

def do_set(root, ch, col, val):
    p = prog_path(root)
    with progress_lock(root):
        if not os.path.exists(p):
            print(f"找不到 {p}"); sys.exit(1)
        lines = open(p, encoding='utf-8').read().split('\n')
        header = None; hidx = {}
        for i, ln in enumerate(lines):
            if ln.startswith('| 章节 |') or ln.startswith('| 章 |'):
                header = [c.strip() for c in ln.split('|')[1:-1]]
                hidx = {name: j for j, name in enumerate(header)}
                break
        if header is None or col not in hidx:
            print(f"列名 '{col}' 不在表头：{header}"); sys.exit(1)
        ci = hidx[col]
        out = []; hit = False
        for ln in lines:
            m = re.match(r'^\|\s*' + re.escape(ch) + r'\s*\|', ln)
            if m:
                parts = ln.split('|')
                tgt = ci + 1
                if tgt < len(parts):
                    parts[tgt] = f' {val} '
                    ln = '|'.join(parts); hit = True
            out.append(ln)
        if not hit:
            print(f"{ch} 不在进度表"); sys.exit(1)
        atomic_write_text(p, '\n'.join(out))
    print(f"✅ 回写 {ch} 「{col}」= {val}")

def _split_row(ln):
    return [c.strip() for c in ln.split('|')[1:-1]]

def _row_trailing(ln):
    parts = ln.split('|')
    return parts[-1] if len(parts) >= 2 else ''

def do_ensure_col(root, col, default='⬜'):
    p = prog_path(root)
    with progress_lock(root):
        if not os.path.exists(p):
            print(f"找不到 {p}"); sys.exit(1)
        lines = open(p, encoding='utf-8').read().split('\n')
        header = None
        for ln in lines:
            if ln.startswith('| 章节 |') or ln.startswith('| 章 |'):
                header = _split_row(ln)
                break
        if header is None:
            print("未找到表头（| 章节 | …）"); sys.exit(1)
        if col in header:
            print(f"✅ 列已存在：{col}"); return
        
        insert_at = len(header) # Default to end

        out = []
        for ln in lines:
            if (ln.startswith('| 章节 |') or ln.startswith('| 章 |')) or re.match(r'^\|\s*-+', ln):
                cells = _split_row(ln); trailing = _row_trailing(ln)
                filler = '---' if re.match(r'^\|\s*-+', ln) else col
                cells.insert(insert_at, filler)
                out.append('| ' + ' | '.join(cells) + ' |' + trailing)
            elif re.match(r'^\|\s*第\s*.*章\s*\|', ln):
                cells = _split_row(ln); trailing = _row_trailing(ln)
                while len(cells) < len(header):
                    cells.append('')
                cells.insert(insert_at, default)
                out.append('| ' + ' | '.join(cells) + ' |' + trailing)
            else:
                out.append(ln)
        atomic_write_text(p, '\n'.join(out))
    print(f"✅ 已追加列「{col}」（默认 {default}）")

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == 'set':
        if len(sys.argv) != 6:
            print("用法: progress.py set <作品根> 第N章 <列名> <值>"); sys.exit(1)
        do_set(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]); return
    if len(sys.argv) >= 2 and sys.argv[1] == 'ensure-col':
        if len(sys.argv) not in (4, 5):
            print("用法: progress.py ensure-col <作品根> <列名> [默认值]"); sys.exit(1)
        do_ensure_col(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else '⬜'); return
    
    if len(sys.argv) < 2:
        print("用法: progress.py <作品根> [第N章]"); sys.exit(1)
        
    root = sys.argv[1].rstrip('/'); only = sys.argv[2] if len(sys.argv) > 2 else None
    
    res = summarize(root)
    if "error" in res:
        print(f"错误: {res['error']}"); sys.exit(1)
        
    header = res["header"]
    rows = res["rows"]
    
    if only:
        r = next((x for x in rows if x['_ch'] == only), None)
        if not r: print(f"{only} 不在进度表"); sys.exit(1)
        route = stage_of(root, r, header)
        print(format_route(root, route))
        return
    
    done = res["done"]; bottleneck = res["bottleneck"]; first = res["first"]
    print(f"作品: {os.path.basename(root)}（共 {len(rows)} 章）")
    print(f"完结章数: {done}/{len(rows)}")
    if first:
        print(f"下一步（最小未完结章）: {format_route(root, first)}")
    else:
        print("🎉 全部完结")
        
    if bottleneck:
        order = STAGES + ['✅已完结']
        items = sorted(bottleneck.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
        print("各阶段卡章数: " + " · ".join(f"{k}={v}" for k, v in items))

if __name__ == '__main__':
    main()
