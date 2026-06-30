#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prework_cache 单测。 cd skills/n2d/_lib && python3 -m pytest test_prework_cache.py"""
import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prework_cache as pc  # noqa: E402


def _mk_episode(tmp_path, ep="第1集", voiceover="台词A", storyboard=None):
    root = str(tmp_path)
    epdir = os.path.join(root, "脚本", ep)
    os.makedirs(epdir, exist_ok=True)
    with open(os.path.join(epdir, "voiceover.txt"), "w", encoding="utf-8") as f:
        f.write(voiceover)
    if storyboard is not None:
        with open(os.path.join(epdir, "storyboard.json"), "w", encoding="utf-8") as f:
            json.dump(storyboard, f)
    return root


# ── 指纹 ────────────────────────────────────────────────────────────────────
def test_fingerprint_changes_when_input_changes(tmp_path):
    root = _mk_episode(tmp_path, voiceover="原台词")
    fp1 = pc.episode_input_fingerprint(root, "第1集")
    with open(os.path.join(root, "脚本", "第1集", "voiceover.txt"), "w", encoding="utf-8") as f:
        f.write("改了台词")
    fp2 = pc.episode_input_fingerprint(root, "第1集")
    assert fp1 != fp2


def test_fingerprint_stable_when_unchanged(tmp_path):
    root = _mk_episode(tmp_path)
    assert pc.episode_input_fingerprint(root, "第1集") == pc.episode_input_fingerprint(root, "第1集")


def test_fingerprint_includes_script_paths(tmp_path):
    root = _mk_episode(tmp_path)
    script = os.path.join(str(tmp_path), "audit.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write("# v1\n")
    fp1 = pc.episode_input_fingerprint(root, "第1集", [script])
    # 改脚本 mtime/size → 指纹变（缓存自动失效，已修的审计会重跑）
    with open(script, "w", encoding="utf-8") as f:
        f.write("# v2 longer content\n")
    fp2 = pc.episode_input_fingerprint(root, "第1集", [script])
    assert fp1 != fp2


def test_fingerprint_never_raises_on_missing(tmp_path):
    # 全缺也不抛
    assert isinstance(pc.episode_input_fingerprint(str(tmp_path), "第9集"), str)


# ── 缓存命中/失效 ────────────────────────────────────────────────────────────
def test_cache_roundtrip(tmp_path):
    root = _mk_episode(tmp_path)
    fp = pc.episode_input_fingerprint(root, "第1集")
    c = pc.PreworkCache(root, "第1集", "image_prompt", fp)
    assert c.get("beat_audit") is None
    c.put("beat_audit", {"status": "pass", "detail": ""})
    c.save()
    c2 = pc.PreworkCache(root, "第1集", "image_prompt", fp)
    hit = c2.get("beat_audit")
    assert hit and hit["status"] == "pass"


def test_cache_invalidated_on_fingerprint_change(tmp_path):
    root = _mk_episode(tmp_path)
    c = pc.PreworkCache(root, "第1集", "image_prompt", "fp-old")
    c.put("beat_audit", {"status": "pass"})
    c.save()
    # 新指纹 → 旧 steps 作废
    c2 = pc.PreworkCache(root, "第1集", "image_prompt", "fp-new")
    assert c2.get("beat_audit") is None


def test_cache_disabled_env(tmp_path, monkeypatch):
    root = _mk_episode(tmp_path)
    c = pc.PreworkCache(root, "第1集", "image_prompt", "fp")
    c.put("x", {"status": "pass"})
    c.save()
    monkeypatch.setenv("N2D_PREWORK_NOCACHE", "1")
    c2 = pc.PreworkCache(root, "第1集", "image_prompt", "fp")
    assert c2.get("x") is None  # 关闭后永不命中


# ── 顺序保持并行 ─────────────────────────────────────────────────────────────
def test_parallel_preserves_order():
    steps = [(f"s{i}", i) for i in range(20)]

    def run_one(i):
        return {"status": "pass", "n": i}

    out = pc.run_cached_parallel(steps, run_one, cache=None, max_workers=8)
    assert [o["n"] for o in out] == list(range(20))


def test_parallel_actually_concurrent():
    # 用 barrier 证明确实并发：若串行，barrier 永远凑不齐会超时。
    n = 6
    barrier = threading.Barrier(n, timeout=5)
    steps = [(f"s{i}", i) for i in range(n)]

    def run_one(i):
        barrier.wait()  # 串行执行时这里会 BrokenBarrier/timeout
        return {"status": "pass", "n": i}

    out = pc.run_cached_parallel(steps, run_one, cache=None, max_workers=n)
    assert sorted(o["n"] for o in out) == list(range(n))


def test_parallel_uses_cache_and_skips_run(tmp_path):
    root = _mk_episode(tmp_path)
    fp = pc.episode_input_fingerprint(root, "第1集")
    cache = pc.PreworkCache(root, "第1集", "image_prompt", fp)
    cache.put("s1", {"status": "block", "detail": "cached"})
    calls = []

    def run_one(obj):
        calls.append(obj)
        return {"status": "pass", "detail": "fresh"}

    steps = [("s1", "obj1"), ("s2", "obj2")]
    out = pc.run_cached_parallel(steps, run_one, cache=cache, max_workers=4)
    assert out[0]["status"] == "block" and out[0].get("_cached")  # 命中缓存，跳过执行
    assert out[1]["status"] == "pass"
    assert calls == ["obj2"]  # 只跑了未命中的 s2


def test_parallel_writes_fresh_to_cache(tmp_path):
    root = _mk_episode(tmp_path)
    fp = pc.episode_input_fingerprint(root, "第1集")
    cache = pc.PreworkCache(root, "第1集", "image_prompt", fp)

    def run_one(obj):
        return {"status": "pass", "detail": obj}

    pc.run_cached_parallel([("s1", "a")], run_one, cache=cache)
    cache.save()
    reopened = pc.PreworkCache(root, "第1集", "image_prompt", fp)
    assert reopened.get("s1") == {"status": "pass", "detail": "a"}


def test_lib_contract_modules_in_fingerprint(tmp_path):
    # 共享 _lib 契约模块改了 → 指纹必须变（否则审计行为变了、缓存仍吐陈旧结果）。
    root = _mk_episode(tmp_path)
    libs = pc._lib_contract_module_paths()
    assert any(os.path.basename(p) == "n2d_const.py" for p in libs)
    assert all(not os.path.basename(p).startswith("test_") for p in libs)
    fp1 = pc.episode_input_fingerprint(root, "第1集")
    target = os.path.join(os.path.dirname(os.path.abspath(pc.__file__)), "n2d_const.py")
    st = os.stat(target)
    try:
        os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
        fp2 = pc.episode_input_fingerprint(root, "第1集")
        assert fp1 != fp2
    finally:
        os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns))


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
