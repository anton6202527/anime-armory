import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compliance_manifest as cm  # noqa: E402


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "ad"
    (root / "合规").mkdir(parents=True)
    (root / "需求").mkdir()
    (root / "合规" / "ai_usage.json").write_text(json.dumps({
        "visual_mode": "AI-generated", "video_mode": "AI-generated",
    }), encoding="utf-8")
    (root / "需求" / "brief.json").write_text(json.dumps({
        "platforms": ["抖音"], "platform_safe_zone_evidence": {"抖音": "合规/抖音版位安全区.png"},
    }), encoding="utf-8")
    return root


def test_ai_release_requires_platform_declaration_evidence(tmp_path):
    root = _project(tmp_path)
    pending = cm.build(root)
    assert pending["summary"]["release_ready"] is False
    assert any(f["code"] == "platform_declaration_pending" for f in pending["findings"])

    done = cm.build(root, "completed", "合规/平台回执.png", "platform_managed", "preserve")
    assert done["summary"]["release_ready"] is True


def test_stripped_metadata_blocks_ai_release(tmp_path):
    root = _project(tmp_path)
    payload = cm.build(root, "completed", "合规/平台回执.png", "platform_managed", "stripped")
    assert any(f["code"] == "metadata_stripped" for f in payload["findings"])
