from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("cache_policy.py")
SPEC = importlib.util.spec_from_file_location("cache_policy", SCRIPT)
cache_policy = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(cache_policy)


def project(tmp_path: Path) -> Path:
    ep = "第1集"
    (tmp_path / "出视频" / ep / "视频").mkdir(parents=True)
    (tmp_path / "出视频" / ep / "视频" / "Clip_01.mp4").write_bytes(b"clip")
    (tmp_path / "合成" / ep / "_work").mkdir(parents=True)
    (tmp_path / "合成" / ep / "_work" / "concat.mp4").write_bytes(b"work")
    (tmp_path / "合成" / ep / "_clipcache").mkdir(parents=True)
    (tmp_path / "合成" / ep / "_clipcache" / "n.mp4").write_bytes(b"cache")
    (tmp_path / "合成" / ep / "成片_第1集_zh.mp4").write_bytes(b"master")
    return tmp_path


def test_manifest_marks_rebuildable_caches(tmp_path: Path) -> None:
    root = project(tmp_path)
    payload = cache_policy.refresh(root, "第1集")
    assert payload["retention"] == "手动清理"
    assert payload["summary"]["cache_bytes"] == 9
    assert payload["summary"]["safe_to_delete_bytes"] == 9
    assert (root / "生产数据" / "cache_manifests" / "compose_cache_第1集.json").is_file()


def test_clean_is_dry_run_then_apply(tmp_path: Path) -> None:
    root = project(tmp_path)
    dry = cache_policy.clean(root, "第1集", apply=False)
    assert dry["action"]["removed"] == []
    assert (root / "合成" / "第1集" / "_work").is_dir()
    done = cache_policy.clean(root, "第1集", apply=True)
    assert done["status"] == "ready"
    assert not (root / "合成" / "第1集" / "_work").exists()
    assert not (root / "合成" / "第1集" / "_clipcache").exists()


def test_legacy_timeline_blocks_work_cleanup(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "合成" / "第1集" / "_work" / "timeline.json").write_text("{}", encoding="utf-8")
    result = cache_policy.clean(root, "第1集", target="work", apply=True)
    assert result["status"] == "block"
    assert (root / "合成" / "第1集" / "_work").exists()


def test_after_success_policy_auto_cleans(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "_设置.md").write_text("- 合成缓存保留: 成片后清理\n", encoding="utf-8")
    result = cache_policy.auto(root, "第1集")
    assert result["status"] == "ready"
    assert not (root / "合成" / "第1集" / "_work").exists()
