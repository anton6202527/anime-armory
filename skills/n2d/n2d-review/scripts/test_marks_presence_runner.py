"""marks_presence_runner 单测——manifest 构建 + 图片归并 + phrase；无后端时 findings 空。

cd skills/n2d/n2d-review/scripts && python3 -m pytest test_marks_presence_runner.py
"""
from __future__ import annotations

import json
from pathlib import Path

import marks_presence_runner as r


def _make(root: Path, *, marks, clips, images=(), ep="第1集"):
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "forms": [
            {"form": "常态", "asset_key": "沈念_常态", "identity_marks": marks}]}]
    }, ensure_ascii=False), encoding="utf-8")
    (root / "脚本" / ep).mkdir(parents=True)
    (root / "脚本" / ep / "storyboard.json").write_text(json.dumps({"clips": clips},
                                                                   ensure_ascii=False), encoding="utf-8")
    imgdir = root / "出图" / ep / "图片"
    imgdir.mkdir(parents=True)
    for name in images:
        (imgdir / name).write_bytes(b"\x89PNG\r\n")


def test_detect_phrase_prefers_explicit_then_desc():
    m = r.mc.normalize_mark({"type": "瞳色", "region": "双眼", "detect_phrase": "golden eyes",
                             "keywords": ["金瞳"]})
    assert r._detect_phrase(m) == "golden eyes"
    m2 = r.mc.normalize_mark({"color": "淡", "type": "疤痕", "region": "左腕", "keywords": ["左腕旧疤"]})
    assert r._detect_phrase(m2) == "淡左腕疤痕"   # color+region+type 描述兜底


def test_episode_images_prefers_main_frame(tmp_path: Path):
    root = tmp_path / "剧"
    (root / "出图" / "第1集" / "图片").mkdir(parents=True)
    for n in ("EP01_CLIP01.png", "EP01_CLIP01_end.png", "EP01_CLIP01_a1.png"):
        (root / "出图" / "第1集" / "图片" / n).write_bytes(b"x")
    imgs = r._episode_images(str(root), "第1集")
    assert imgs["EP01_CLIP01"].endswith("EP01_CLIP01.png")   # 主帧优先于 _end/_a1


def test_build_manifest_probes_expected_marks(tmp_path: Path):
    root = tmp_path / "剧"
    _make(root,
          marks=[{"mark_id": "MARK_左腕旧疤", "type": "疤痕", "region": "左腕",
                  "persistence": "permanent", "keywords": ["左腕旧疤"], "detect_phrase": "scar on wrist"}],
          clips=[{"id": "EP01_CLIP01", "label": "镜中脸", "shots": [{"desc": "沈念按住左腕"}]},
                 {"id": "EP01_CLIP02", "label": "空镜", "shots": [{"desc": "残烛摇曳，无人物"}]}],
          images=["EP01_CLIP01.png"])
    man = r.build_manifest(str(root), "第1集")
    assert man["kind"] == "n2d_marks_presence" and man["findings"] == []
    probes = {p["shot"]: p for p in man["probes"]}
    assert "EP01_CLIP01" in probes               # 沈念在场 → 有 probe
    assert "EP01_CLIP02" not in probes           # 空镜无角色 → 无 probe
    ea = probes["EP01_CLIP01"]["expected_assets"][0]
    assert ea["asset"] == "MARK_左腕旧疤" and ea["phrase"] == "scar on wrist"
    assert probes["EP01_CLIP01"]["image"].endswith("EP01_CLIP01.png")


def test_build_manifest_excludes_not_yet_acquired_mark(tmp_path: Path):
    root = tmp_path / "剧"
    _make(root,
          marks=[{"mark_id": "MARK_金瞳", "type": "瞳色", "region": "双眼",
                  "persistence": {"acquired_at": "第3集"}, "keywords": ["金瞳"]}],
          clips=[{"id": "EP01_CLIP01", "label": "睁眼", "shots": [{"desc": "沈念睁眼"}]}],
          images=["EP01_CLIP01.png"])
    # 第1集 < 获得集第3集 → 该镜没有应在场标记 → 无 probe
    man1 = r.build_manifest(str(root), "第1集")
    assert man1["probes"] == []
    # 第4集（获得后）→ 应在场 → 有 probe
    (root / "脚本" / "第4集").mkdir(parents=True)
    (root / "脚本" / "第4集" / "storyboard.json").write_text(json.dumps(
        {"clips": [{"id": "EP04_CLIP01", "label": "睁眼", "shots": [{"desc": "沈念睁眼"}]}]},
        ensure_ascii=False), encoding="utf-8")
    (root / "出图" / "第4集" / "图片").mkdir(parents=True)
    (root / "出图" / "第4集" / "图片" / "EP04_CLIP01.png").write_bytes(b"x")
    man4 = r.build_manifest(str(root), "第4集")
    assert len(man4["probes"]) == 1
