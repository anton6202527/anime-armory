import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_pack as pp  # noqa: E402


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps({
        "platforms": ["抖音", "小红书"],
        "deliverables": {"master_duration": "30s", "aspect": "9:16", "cutdowns": ["15s", "6s"]},
    }, ensure_ascii=False), encoding="utf-8")
    (root / "_设置.md").write_text("- 目标平台: 跨平台\n- 主片时长: 30s\n", encoding="utf-8")
    return root


def test_build_pack_includes_platform_specs_and_deliverables(tmp_path):
    root = _project(tmp_path)
    pack = pp.build_pack(root)

    assert pack["summary"]["platform_count"] == 2
    assert pack["summary"]["deliverable_count"] == 3
    assert pack["specs"]["抖音"]["safe_area"] == "center_6x6"
    assert [row["deliverable_id"] for row in pack["deliverables"]] == ["master", "cut_15s", "cut_6s"]


def test_write_pack_outputs_json(tmp_path):
    root = _project(tmp_path)
    pack = pp.write_pack(root)

    path = Path(pack["_json_path"])
    assert path.is_file()
    disk = json.loads(path.read_text(encoding="utf-8"))
    assert disk["kind"] == pp.KIND


def test_unknown_platform_warns(tmp_path):
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text(json.dumps({"platforms": ["新平台"]}, ensure_ascii=False), encoding="utf-8")

    pack = pp.build_pack(root)

    assert pack["summary"]["warn"] == 1
    assert pack["specs"]["新平台"]["platform_key"] == "manual"
