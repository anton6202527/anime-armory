"""object_presence_runner / appearance_judge_runner manifest 构建单测。
cd skills/n2d-review/scripts && python -m pytest test_presence_appearance_runners.py
"""
import importlib.util
import json
import os

import object_presence_runner as opr
import appearance_judge_runner as ajr
import resident_presence as rp


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


def _img(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n")


def test_presence_manifest_lists_expected_assets(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_PRESENCE_CMD", raising=False)
    root = str(tmp_path)
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_01", "loc": "LOC_hall", "desc": "大殿全景"}]})
    _w(os.path.join(root, "出图", "共享", "asset_registry.json"),
       {"assets": [{"id": "PROP_throne", "location": "LOC_hall", "persistent": True, "外观": "鎏金龙椅"}]})
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_01.png"))
    m = opr.fill_findings(root, opr.build_manifest(root, "第1集"))
    assert m["kind"] == "n2d_object_presence"
    assert m["probes"] and m["probes"][0]["expected_assets"][0]["asset"] == "PROP_throne"
    assert m["probes"][0]["image"].endswith("Clip_01.png")
    assert m["findings"] == []  # 无检测器命令 → 不臆造在场结论


def test_presence_exempt_view_skipped(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_PRESENCE_CMD", raising=False)
    root = str(tmp_path)
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_01", "loc": "LOC_hall", "desc": "特写细节，龙椅扶手"}]})
    _w(os.path.join(root, "出图", "共享", "asset_registry.json"),
       {"assets": [{"id": "PROP_throne", "location": "LOC_hall", "persistent": True}]})
    m = opr.build_manifest(root, "第1集")
    assert m["probes"] == []  # 特写豁免


def test_presence_write_uses_batch_backend(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_PRESENCE_CMD", raising=False)
    root = str(tmp_path)
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_01", "loc": "LOC_hall", "desc": "大殿全景"}]})
    _w(os.path.join(root, "出图", "共享", "asset_registry.json"),
       {"assets": [{"id": "PROP_throne", "location": "LOC_hall", "persistent": True, "外观": "鎏金龙椅"}]})
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_01.png"))
    fake = tmp_path / "presence_batch.py"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "path = sys.argv[1]\n"
        "with open(path, encoding='utf-8') as fh:\n"
        "    data = json.load(fh)\n"
        "data['detector'] = 'fake-batch'\n"
        "data['findings'] = [{'shot': 'Clip_01', 'asset': 'PROP_throne', 'present': False}]\n"
        "with open(path, 'w', encoding='utf-8') as fh:\n"
        "    json.dump(data, fh, ensure_ascii=False)\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    monkeypatch.setenv("N2D_PRESENCE_BATCH_CMD", str(fake))
    path = opr.write(root, "第1集")
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    assert payload["detector"] == "fake-batch"
    assert payload["findings"][0]["asset"] == "PROP_throne"


def test_presence_owlv2_backend_no_probes_writes_manifest(tmp_path):
    backend_path = os.path.join(os.path.dirname(__file__), "backends", "presence_owlv2.py")
    spec = importlib.util.spec_from_file_location("presence_owlv2_backend", backend_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    manifest_path = tmp_path / "object_presence.json"
    manifest_path.write_text(json.dumps({"root": str(tmp_path), "probes": []}, ensure_ascii=False), encoding="utf-8")
    assert mod.main([str(manifest_path)]) == 0
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["findings"] == []
    assert payload["detector"].endswith("(no-probes)")


def test_resident_assets_accept_structured_detect_phrase():
    reg = {
        "LOC_01": {
            "scene_dna": {
                "resident_assets": [
                    {"asset": "乱石", "phrase": "rocks"},
                    "低雾",
                ]
            }
        }
    }
    assert rp.scene_resident_assets(reg) == {
        "LOC_01": [
            {"asset": "乱石", "phrase": "rocks"},
            {"asset": "低雾", "phrase": "低雾"},
        ]
    }


def test_appearance_manifest_pairs_reference_and_shot(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_APPEARANCE_CMD", raising=False)
    monkeypatch.delenv("N2D_VLM_CMD", raising=False)
    root = str(tmp_path)
    _w(os.path.join(root, "出图", "共享", "identity_registry.json"),
       {"characters": {"CHAR_shen": {"reference_group": {"face_anchor": "出图/共享/图片/定妆_shen.png"}}}})
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_02", "desc": "CHAR_shen 近景"}]})
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_02.png"))
    m = ajr.fill_findings(root, ajr.build_manifest(root, "第1集"))
    assert m["kind"] == "n2d_appearance_judge"
    assert m["pairs"] and m["pairs"][0]["character"] == "CHAR_shen"
    assert m["pairs"][0]["reference"].endswith("定妆_shen.png")
    assert m["findings"] == []  # 无 VLM 命令 → 不臆造分


def test_appearance_fill_uses_env_command(tmp_path, monkeypatch):
    root = str(tmp_path)
    _w(os.path.join(root, "出图", "共享", "identity_registry.json"),
       {"characters": {"CHAR_shen": {"reference_png": "ref.png"}}})
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_02", "desc": "CHAR_shen 近景"}]})
    _img(os.path.join(root, "ref.png"))
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_02.png"))
    # 假 VLM 判官：raw similarity 0.4 命中 block 档，但自动结论封顶 warn。
    fake = tmp_path / "judge.sh"
    fake.write_text('#!/bin/sh\necho \'{"similarity": 0.4}\'\n')
    fake.chmod(0o755)
    monkeypatch.setenv("N2D_APPEARANCE_CMD", f"sh {fake}")
    m = ajr.fill_findings(root, ajr.build_manifest(root, "第1集"))
    assert m["findings"] and m["findings"][0]["verdict"] == "warn"
    assert m["findings"][0]["vlm_raw_verdict"] == "block"
    assert m["findings"][0]["similarity"] == 0.4


def test_appearance_write_uses_batch_backend(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_APPEARANCE_CMD", raising=False)
    monkeypatch.delenv("N2D_VLM_CMD", raising=False)
    root = str(tmp_path)
    _w(os.path.join(root, "出图", "共享", "identity_registry.json"),
       {"characters": {"CHAR_shen": {"reference_png": "ref.png"}}})
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_02", "desc": "CHAR_shen 近景"}]})
    _img(os.path.join(root, "ref.png"))
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_02.png"))
    fake = tmp_path / "appearance_batch.py"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "path = sys.argv[1]\n"
        "with open(path, encoding='utf-8') as fh:\n"
        "    data = json.load(fh)\n"
        "data['judge'] = 'fake-batch'\n"
        "data['findings'] = [{'shot': 'Clip_02', 'character': 'CHAR_shen', 'verdict': 'block'}]\n"
        "with open(path, 'w', encoding='utf-8') as fh:\n"
        "    json.dump(data, fh, ensure_ascii=False)\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    monkeypatch.setenv("N2D_APPEARANCE_BATCH_CMD", str(fake))
    path = ajr.write(root, "第1集")
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    assert payload["judge"] == "fake-batch"
    assert payload["findings"][0]["character"] == "CHAR_shen"
    assert payload["findings"][0]["verdict"] == "warn"
    assert payload["findings"][0]["vlm_raw_verdict"] == "block"


def test_appearance_auto_mlxvlm_batch_off_by_default(monkeypatch):
    monkeypatch.delenv("N2D_APPEARANCE_BATCH_CMD", raising=False)
    monkeypatch.delenv("N2D_APPEARANCE_AUTO", raising=False)
    monkeypatch.setattr(ajr, "_n2dvlm_env_exists", lambda: True)
    assert ajr._appearance_batch_cmd() == ""


def test_appearance_auto_mlxvlm_batch_template_when_opted_in(monkeypatch):
    monkeypatch.delenv("N2D_APPEARANCE_BATCH_CMD", raising=False)
    monkeypatch.setenv("N2D_APPEARANCE_AUTO", "1")
    monkeypatch.setattr(ajr, "_n2dvlm_env_exists", lambda: True)
    cmd = ajr._appearance_batch_cmd()
    assert "appearance_mlxvlm.py" in cmd
    assert "conda run -n n2dvlm" in cmd


def test_appearance_auto_batch_can_disable(monkeypatch):
    monkeypatch.setenv("N2D_APPEARANCE_BATCH_CMD", "off")
    monkeypatch.setattr(ajr, "_n2dvlm_env_exists", lambda: True)
    assert ajr._appearance_batch_cmd() == ""


def test_appearance_mlxvlm_backend_no_pairs_writes_manifest(tmp_path):
    backend_path = os.path.join(os.path.dirname(__file__), "backends", "appearance_mlxvlm.py")
    spec = importlib.util.spec_from_file_location("appearance_mlxvlm_backend", backend_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    manifest_path = tmp_path / "appearance_judge.json"
    manifest_path.write_text(json.dumps({"root": str(tmp_path), "pairs": []}, ensure_ascii=False), encoding="utf-8")
    assert mod.main([str(manifest_path)]) == 0
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["findings"] == []
    assert payload["judge"].endswith("(no-pairs)")


def test_appearance_mlxvlm_backend_caps_self_reported_block_to_warn():
    backend_path = os.path.join(os.path.dirname(__file__), "backends", "appearance_mlxvlm.py")
    spec = importlib.util.spec_from_file_location("appearance_mlxvlm_backend_policy", backend_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    row = mod._verdict_from({"similarity": 0.1, "verdict": "block", "message": "不像"})
    assert row["verdict"] == "warn"
    assert row["vlm_raw_verdict"] == "block"
