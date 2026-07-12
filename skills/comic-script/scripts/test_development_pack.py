"""comic development_pack 单测。运行：cd skills/comic-script/scripts && python -m pytest test_development_pack.py"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("development_pack.py")
spec = importlib.util.spec_from_file_location("comic_development_pack", SCRIPT)
dp = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(dp)


def test_scaffold_creates_but_never_overwrites(tmp_path):
    created = dp.scaffold(tmp_path, write=True)
    assert len(created) == 3
    strategy = tmp_path / "开发包" / "adaptation_strategy.json"
    strategy.write_text('{"kind":"comic_adaptation_strategy","status":"confirmed","custom":1}', encoding="utf-8")
    again = dp.scaffold(tmp_path, write=True)
    assert again == []
    assert json.loads(strategy.read_text(encoding="utf-8"))["custom"] == 1


def test_check_blocks_on_placeholder_confirmed(tmp_path):
    dp.scaffold(tmp_path, write=True)
    strategy = tmp_path / "开发包" / "adaptation_strategy.json"
    data = json.loads(strategy.read_text(encoding="utf-8"))
    data["status"] = "confirmed"
    strategy.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report = dp.check_pack(tmp_path)
    assert report["status"] == "blocked"
    assert any(g["code"] == "adaptation_strategy_placeholder_in_confirmed" for g in report["gaps"])


def _fill_confirmed(tmp_path):
    dp.scaffold(tmp_path, write=True)
    for key, path in dp.pack_files(tmp_path).items():
        if key == "signoff":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False).replace("待补", "已填内容").replace("待填", "已填")
        data = json.loads(text)
        data["status"] = "confirmed"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_check_requires_signoff_with_current_sha(tmp_path):
    _fill_confirmed(tmp_path)
    report = dp.check_pack(tmp_path)
    assert any(g["code"] == "signoff_missing" for g in report["gaps"])
    hashes = report["file_sha256"]
    (tmp_path / "开发包" / "signoff.json").write_text(json.dumps({
        "reviewer": "编辑甲", "role": "creative", "time": "2026-07-12",
        "file_sha256": hashes}, ensure_ascii=False), encoding="utf-8")
    report2 = dp.check_pack(tmp_path)
    assert report2["status"] == "confirmed"
    strategy = tmp_path / "开发包" / "adaptation_strategy.json"
    data = json.loads(strategy.read_text(encoding="utf-8"))
    data["adaptation_boundary"] = "改了边界"
    strategy.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report3 = dp.check_pack(tmp_path)
    assert any(g["code"] == "signoff_stale_adaptation_strategy" for g in report3["gaps"])
