#!/usr/bin/env python3
"""loudness_conform 纯数学单测。
cd skills/n2d-compose && python -m pytest test_loudness_conform.py -q
"""
import os

import loudness_conform as lc


# ---------- lufs_band ----------

def test_lufs_band_ok_exact_target():
    assert lc.lufs_band(-14.0, -14.0) == "ok"


def test_lufs_band_ok_within_tol():
    assert lc.lufs_band(-14.5, -14.0, tol=1.0) == "ok"
    assert lc.lufs_band(-13.2, -14.0, tol=1.0) == "ok"


def test_lufs_band_ok_boundary_eq_tol():
    # 恰好 tol → ok（含等号）
    assert lc.lufs_band(-15.0, -14.0, tol=1.0) == "ok"
    assert lc.lufs_band(-13.0, -14.0, tol=1.0) == "ok"


def test_lufs_band_warn_within_2tol():
    assert lc.lufs_band(-15.5, -14.0, tol=1.0) == "warn"
    assert lc.lufs_band(-12.5, -14.0, tol=1.0) == "warn"


def test_lufs_band_warn_boundary_eq_2tol():
    # 恰好 2*tol → warn（含等号）
    assert lc.lufs_band(-16.0, -14.0, tol=1.0) == "warn"
    assert lc.lufs_band(-12.0, -14.0, tol=1.0) == "warn"


def test_lufs_band_block_beyond_2tol():
    assert lc.lufs_band(-16.1, -14.0, tol=1.0) == "block"
    assert lc.lufs_band(-9.0, -14.0, tol=1.0) == "block"
    assert lc.lufs_band(-23.0, -14.0, tol=1.0) == "block"


def test_lufs_band_custom_tol():
    assert lc.lufs_band(-16.0, -14.0, tol=2.0) == "ok"     # |2| ≤ 2
    assert lc.lufs_band(-18.0, -14.0, tol=2.0) == "warn"   # |4| ≤ 4
    assert lc.lufs_band(-18.5, -14.0, tol=2.0) == "block"


# ---------- true_peak_band ----------

def test_true_peak_ok_below_ceiling():
    assert lc.true_peak_band(-2.0) == "ok"
    assert lc.true_peak_band(-1.5, ceiling=-1.0) == "ok"


def test_true_peak_ok_boundary_eq_ceiling():
    # 恰好 ceiling → ok（含等号，未超出）
    assert lc.true_peak_band(-1.0, ceiling=-1.0) == "ok"


def test_true_peak_block_above_ceiling():
    assert lc.true_peak_band(-0.9, ceiling=-1.0) == "block"
    assert lc.true_peak_band(0.0, ceiling=-1.0) == "block"
    assert lc.true_peak_band(1.2, ceiling=-1.0) == "block"


def test_true_peak_custom_ceiling():
    assert lc.true_peak_band(-1.5, ceiling=-2.0) == "block"
    assert lc.true_peak_band(-2.0, ceiling=-2.0) == "ok"


# ---------- worst_band ----------

def test_worst_band_escalates():
    assert lc.worst_band(["ok", "ok"]) == "ok"
    assert lc.worst_band(["ok", "warn"]) == "warn"
    assert lc.worst_band(["warn", "block"]) == "block"
    assert lc.worst_band([]) == "ok"


# ---------- resolve_target ----------

def test_resolve_target_known_platforms():
    assert lc.resolve_target("youtube") == -14.0
    assert lc.resolve_target("bilibili") == -14.0
    assert lc.resolve_target("tiktok") == -14.0
    assert lc.resolve_target("broadcast") == -23.0
    assert lc.resolve_target("default") == -16.0


def test_resolve_target_case_insensitive_and_unknown():
    assert lc.resolve_target("YouTube") == -14.0
    assert lc.resolve_target("  Broadcast ") == -23.0
    assert lc.resolve_target("weibo") == -16.0   # 未知 → default
    assert lc.resolve_target("") == -16.0


# ---------- _parse_loudnorm_json (parse-only, no ffmpeg) ----------

def test_parse_loudnorm_json_extracts_block():
    stderr = (
        "ffmpeg version ...\n[Parsed_loudnorm_0 @ 0x] \n"
        '{\n  "input_i" : "-18.42",\n  "input_tp" : "-1.20",\n'
        '  "input_lra" : "7.0",\n  "input_thresh" : "-28.0"\n}\n'
    )
    data = lc._parse_loudnorm_json(stderr)
    assert data is not None
    assert float(data["input_i"]) == -18.42
    assert float(data["input_tp"]) == -1.20


def test_parse_loudnorm_json_none_on_garbage():
    assert lc._parse_loudnorm_json("no json here") is None
    assert lc._parse_loudnorm_json('{"foo": "bar"}') is None  # 无 input_i


def test_measure_none_when_path_missing():
    assert lc.measure("/no/such/file.mp4") is None


def test_find_final_cut_prefers_master_over_newer_loudnorm_backup(tmp_path):
    ep = "第1集"
    out = tmp_path / "合成" / ep
    out.mkdir(parents=True)
    master = out / f"成片_{ep}_zh.mp4"
    backup = out / f"成片_{ep}_zh.pre_loudnorm_fix.mp4"
    master.write_bytes(b"master")
    backup.write_bytes(b"backup")
    os.utime(master, (100, 100))
    os.utime(backup, (200, 200))

    assert lc._find_final_cut(str(tmp_path), ep) == str(master)


def test_resolve_platform_key_prefers_cli_then_settings(tmp_path):
    import loudness_conform as lc
    root = tmp_path / "作品"
    root.mkdir()
    (root / "_设置.md").write_text("## 选择\n- 目标平台: 抖音\n", encoding="utf-8")
    assert lc.resolve_platform_key(str(root), "youtube") == ("youtube", "cli")
    key, source = lc.resolve_platform_key(str(root), None)
    assert key == "tiktok"
    assert source.startswith("settings:")
    empty = tmp_path / "空作品"
    empty.mkdir()
    assert lc.resolve_platform_key(str(empty), None) == ("default", "fallback")
