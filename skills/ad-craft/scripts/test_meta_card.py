import importlib.util
import json
from pathlib import Path


def _load(name):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"adcraft_{name}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


meta_card = _load("meta_card")


def _project(tmp_path, meta=None, brief=None):
    root = tmp_path / "ad-proj"
    (root / "需求").mkdir(parents=True)
    base_meta = {"kind": "ad_project", "line": "ad", "synopsis": "", "cover": None}
    if meta:
        base_meta.update(meta)
    (root / "_meta.json").write_text(json.dumps(base_meta, ensure_ascii=False), encoding="utf-8")
    if brief is not None:
        (root / "需求" / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    return root


def test_derive_synopsis_prefers_key_message_then_objective():
    assert meta_card.derive_synopsis({"key_message": "买它", "campaign_objective": "转化"}) == "买它"
    assert meta_card.derive_synopsis({"key_message": "", "campaign_objective": "转化"}) == "转化"
    assert meta_card.derive_synopsis({"key_message": "待补", "campaign_objective": ""}, "兜底") == "兜底"
    assert meta_card.derive_synopsis(None) == ""


def test_synopsis_truncated_to_limit():
    long = "字" * 400
    out = meta_card.derive_synopsis({"key_message": long})
    assert len(out) <= meta_card.SYNOPSIS_MAX


def test_initial_synopsis_is_objective_placeholder():
    assert meta_card.initial_synopsis("转化行动") == "转化行动"
    assert meta_card.initial_synopsis("") == ""


def test_backfill_overwrites_objective_placeholder_with_key_message(tmp_path):
    root = _project(tmp_path, meta={"synopsis": "转化行动"},
                    brief={"key_message": "一句真简介", "campaign_objective": "转化行动"})
    result = meta_card.backfill_synopsis(root)
    assert result["changed"] and result["synopsis"] == "一句真简介"
    assert json.loads((root / "_meta.json").read_text(encoding="utf-8"))["synopsis"] == "一句真简介"


def test_backfill_preserves_user_authored_synopsis(tmp_path):
    root = _project(tmp_path, meta={"synopsis": "用户手写独家简介"},
                    brief={"key_message": "机器派生", "campaign_objective": "转化行动"})
    result = meta_card.backfill_synopsis(root)
    assert not result["changed"] and result["reason"] == "user_authored"


def test_backfill_force_overrides_user_content(tmp_path):
    root = _project(tmp_path, meta={"synopsis": "用户手写"},
                    brief={"key_message": "机器派生"})
    result = meta_card.backfill_synopsis(root, force=True)
    assert result["changed"] and result["synopsis"] == "机器派生"


def test_backfill_empty_synopsis_from_brief(tmp_path):
    root = _project(tmp_path, brief={"key_message": "从空回填"})
    result = meta_card.backfill_synopsis(root)
    assert result["changed"] and result["synopsis"] == "从空回填"


def _portrait_png(path, w=720, h=1280):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (w, h), "#FF6600").save(path)


def test_set_cover_backfills_relative_path(tmp_path):
    root = _project(tmp_path)
    _portrait_png(root / "出图" / "封面" / "cover.png")
    result = meta_card.set_cover(root, "出图/封面/cover.png")
    assert result["changed"] and result["cover"] == "出图/封面/cover.png"
    assert json.loads((root / "_meta.json").read_text(encoding="utf-8"))["cover"] == "出图/封面/cover.png"


def test_set_cover_rejects_landscape(tmp_path):
    root = _project(tmp_path)
    _portrait_png(root / "出图" / "封面" / "wide.png", w=1280, h=720)
    result = meta_card.set_cover(root, "出图/封面/wide.png")
    assert not result["changed"] and result["reason"] == "not_portrait"
    result2 = meta_card.set_cover(root, "出图/封面/wide.png", allow_non_portrait=True)
    assert result2["changed"]


def test_set_cover_rejects_outside_root_and_missing(tmp_path):
    root = _project(tmp_path)
    outside = tmp_path / "elsewhere.png"
    _portrait_png(outside)
    assert meta_card.set_cover(root, str(outside))["reason"] == "outside_project_root"
    assert meta_card.set_cover(root, "出图/封面/none.png")["reason"] == "missing_file"


def test_set_cover_writes_progress_maintenance_note(tmp_path):
    root = _project(tmp_path)
    (root / "_进度.md").write_text("# p\n\n## 维护记录\n- 初始化\n", encoding="utf-8")
    _portrait_png(root / "出图" / "封面" / "cover.png")
    meta_card.set_cover(root, "出图/封面/cover.png")
    assert "封面回填" in (root / "_进度.md").read_text(encoding="utf-8")


def test_clear_cover(tmp_path):
    root = _project(tmp_path, meta={"cover": "出图/封面/cover.png"})
    result = meta_card.clear_cover(root)
    assert result["changed"] and result["cover"] is None
