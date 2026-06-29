"""validate_state_files 单测。
cd tools && python3 -m pytest test_validate_state_files.py
"""
import os

import validate_state_files as v

GOOD = """# 进度

| 集 | 剧本改编 | 配音 | 分镜设计 | 出图 | 视频 | 成片 | 验收 |
|---|---|---|---|---|---|---|---|
| 第1集 | ✅ | ✅ | ✅ | 12/19 | ⬜ | ⬜ | ⬜ |
| 第2集 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
"""

# 表头被改坏（缺一列分隔 → 解析错位）
BAD = """# 进度

| 集 | 剧本改编 | 配音
|---|---|
| 第1集 | ✅ |
"""


def _mk(tmp, name, content, line="制漫剧"):
    root = os.path.join(str(tmp), "创作区", line, name)
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write(content)
    return root


def test_good_progress_passes(tmp_path):
    root = _mk(tmp_path, "好剧", GOOD)
    errors, warnings = v.validate_root(root)
    assert errors == [], errors


def test_missing_progress_is_error(tmp_path):
    root = os.path.join(str(tmp_path), "创作区", "制漫剧", "空")
    os.makedirs(root, exist_ok=True)
    errors, _ = v.validate_root(root)
    assert any("缺 _进度.md" in e for e in errors)


def test_legacy_common_path_warns(tmp_path):
    root = os.path.join(str(tmp_path), "创作区", "制漫剧", "旧布局")
    os.makedirs(os.path.join(root, "common"), exist_ok=True)
    with open(os.path.join(root, "common", "_进度.md"), "w", encoding="utf-8") as f:
        f.write(GOOD)
    errors, warnings = v.validate_root(root)
    assert errors == []
    assert any("common/_进度.md" in w for w in warnings)


def test_legacy_voice_manifest_warns(tmp_path):
    root = _mk(tmp_path, "迁移剧", GOOD)
    vd = os.path.join(root, "出视频", "第1集", "配音")
    os.makedirs(vd, exist_ok=True)
    open(os.path.join(vd, "时长清单.json"), "w").close()
    _, warnings = v.validate_root(root)
    assert any("出视频/配音" in w or "旧位时长清单" in w for w in warnings)


def test_strict_promotes_warning_to_failure(tmp_path):
    _mk(tmp_path, "迁移剧2", GOOD)
    vd = os.path.join(str(tmp_path), "创作区", "制漫剧", "迁移剧2", "出视频", "第1集", "配音")
    os.makedirs(vd, exist_ok=True)
    open(os.path.join(vd, "时长清单.json"), "w").close()
    # 用 main 走 --strict（指定单根）
    rc_warn = v.main([os.path.join(str(tmp_path), "创作区", "制漫剧", "迁移剧2")])
    rc_strict = v.main([os.path.join(str(tmp_path), "创作区", "制漫剧", "迁移剧2"), "--strict"])
    assert rc_warn == 0 and rc_strict == 1


if __name__ == "__main__":
    import tempfile
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn(tempfile.mkdtemp())
            print("ok", name)
