#!/usr/bin/env python3
"""Tests for progress.py side effects."""
import json
import os
import subprocess
import sys


PROG = """# demo — 生产进度

已粗切 **1** 集。

| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 第1集 | 100 | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
"""


def test_progress_set_writes_episode_manifest(tmp_path):
    root = tmp_path / "demo"
    root.mkdir()
    (root / "_进度.md").write_text(PROG, encoding="utf-8")
    script = os.path.join(os.path.dirname(__file__), "progress.py")

    result = subprocess.run(
        [sys.executable, script, "set", str(root), "第1集", "配音", "✅"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert "回写 第1集" in result.stdout
    manifest = root / "脚本" / "第1集" / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_episode_manifest"
    assert data["episode"] == "第1集"
    assert data["last_progress_column"] == "配音"
    assert data["last_progress_value"] == "✅"
    assert (root / "_进度.lock").exists()
    assert not list(root.glob("._进度.md.tmp.*"))


def test_ensure_col_updates_fullwidth_and_chinese_episode_rows(tmp_path):
    root = tmp_path / "demo"
    root.mkdir()
    progress = """# demo

| 集 | 字数 | raw | 剧本改编 | 成片 |
|---|---|---|---|---|
| 第1集 | 100 | ✅ | ✅ | ⬜ |
| 第２集 | 100 | ✅ | ⬜ | ⬜ |
| 第三集 | 100 | ✅ | ⬜ | ⬜ |
"""
    (root / "_进度.md").write_text(progress, encoding="utf-8")
    script = os.path.join(os.path.dirname(__file__), "progress.py")

    subprocess.run(
        [sys.executable, script, "ensure-col", str(root), "视频prompt", "⬜"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    lines = (root / "_进度.md").read_text(encoding="utf-8").splitlines()
    episode_rows = [ln for ln in lines if ln.startswith("| 第")]
    assert len(episode_rows) == 3
    assert all(len(row.split("|")[1:-1]) == 6 for row in episode_rows)
    assert (root / "_进度.lock").exists()
    assert not list(root.glob("._进度.md.tmp.*"))


def test_audit_placeholders_can_downgrade_old_fake_done(tmp_path):
    root = tmp_path / "demo"
    root.mkdir()
    progress = PROG.replace("| 第1集 | 100 | ✅ | ✅ | ✅ | ✅ | ⬜ |", "| 第1集 | 100 | ✅ | ✅ | ✅ | ✅ | ✅ |")
    (root / "_进度.md").write_text(progress, encoding="utf-8")
    voice_dir = root / "合成" / "第1集" / "配音"
    voice_dir.mkdir(parents=True)
    (voice_dir / "时长清单.json").write_text(json.dumps([{"idx": 0, "占位": True}], ensure_ascii=False), encoding="utf-8")
    script = os.path.join(os.path.dirname(__file__), "progress.py")

    result = subprocess.run(
        [sys.executable, script, "audit-placeholders", str(root), "--fix"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert "旧占位配音伪完成" in result.stdout
    assert "⏳rough" in (root / "_进度.md").read_text(encoding="utf-8")
