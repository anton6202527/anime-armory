import json

import series_consistency as sc


def _identity(root):
    path = root / "出图" / "共享" / "identity_registry.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"characters": [{"id": "CHAR_01", "name": "沈念"}]}, ensure_ascii=False), encoding="utf-8")


def test_scaffold_and_forbidden_name_variant(tmp_path):
    _identity(tmp_path)
    payload = sc.scaffold(tmp_path)
    payload["status"] = "confirmed"
    payload["canonical_names"]["CHAR_01"]["forbidden_variants"] = ["沈恋"]
    payload["dialogue_registers"]["CHAR_01"].update({"formality": "克制", "anchors": ["我知道"], "forbidden_terms": []})
    sc.path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sc.path(tmp_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text("旁白：沈恋走进门。", encoding="utf-8")
    codes = {row["code"] for row in sc.validate(tmp_path, "第1集", phase="script")}
    assert "forbidden_name_variant" in codes


def test_required_for_multi_episode(tmp_path):
    (tmp_path / "_进度.md").write_text("| 集 | raw |\n|---|---|\n| 第1集 | ✅ |\n| 第2集 | ⬜ |\n", encoding="utf-8")
    assert sc.required(tmp_path) is True


def test_register_terms_apply_only_to_attributed_character(tmp_path):
    _identity(tmp_path)
    payload = sc.scaffold(tmp_path)
    payload["status"] = "confirmed"
    payload["dialogue_registers"]["CHAR_01"].update({
        "formality": "克制",
        "anchors": ["我知道"],
        "forbidden_terms": ["绝绝子"],
    })
    sc.path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sc.path(tmp_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text("[镜头1·路人] 绝绝子\n[镜头2·沈念] 我知道。", encoding="utf-8")
    assert sc.validate(tmp_path, "第1集", phase="script") == []
    (ep / "voiceover.txt").write_text("[镜头1·沈念] 绝绝子", encoding="utf-8")
    assert "dialogue_register_forbidden_term" in {
        row["code"] for row in sc.validate(tmp_path, "第1集", phase="script")
    }
