#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small locked/atomic file helpers shared by novel-craft scripts."""
import contextlib
import json
import os
import time


try:
    import fcntl
except ImportError:  # pragma: no cover - macOS/Linux path uses fcntl.
    fcntl = None


@contextlib.contextmanager
def file_lock(lock_path, *, poll_seconds=0.05):
    """Acquire an exclusive file lock, with a mkdir fallback on non-POSIX hosts."""
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    if fcntl is not None:
        with open(lock_path, "a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield lock_path
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        return

    lock_dir = f"{lock_path}.d"
    while True:
        try:
            os.mkdir(lock_dir)
            break
        except FileExistsError:
            time.sleep(poll_seconds)
    try:
        yield lock_dir
    finally:
        try:
            os.rmdir(lock_dir)
        except OSError:
            pass


def atomic_write_text(path, text, *, encoding="utf-8"):
    """Write text via same-directory temp file, fsync, atomic replace, then fsync dir.

    fsync 让「崩溃/断电后要么旧内容要么新内容、绝不半截写」真正成立（B2·crash-atomic，
    非仅 atomic-visibility）：临时文件 flush+fsync 落盘后才 os.replace；rename 后再 fsync 目录项，
    保证 rename 本身持久。非 POSIX / 不支持 fsync 目录的平台优雅跳过（退化为 atomic-visibility）。
    """
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        try:
            dir_fd = os.open(d, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except (OSError, AttributeError):  # pragma: no cover - 非 POSIX 目录 fsync 不可用
            pass
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, payload, *, indent=2):
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=indent) + "\n")

