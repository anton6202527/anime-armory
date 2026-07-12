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


def test_register_ignores_unattributed_comments_that_name_character(tmp_path):
    _identity(tmp_path)
    payload = sc.scaffold(tmp_path)
    payload["status"] = "confirmed"
    payload["dialogue_registers"]["CHAR_01"].update({
        "formality": "克制",
        "anchors": ["我知道"],
        "forbidden_terms": [],
        "sentence_len_max": 4,
    })
    sc.path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sc.path(tmp_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text(
        "# 留存节拍：沈念在这一段完成一条很长的交易说明，但这不是台词。\n"
        "[镜头1·沈念] 我知道。",
        encoding="utf-8",
    )
    assert sc.validate(tmp_path, "第1集", phase="script") == []


def test_write_missing_merges_new_identity_rows_into_existing_contract(tmp_path):
    _identity(tmp_path)
    payload = sc.scaffold(tmp_path)
    payload["status"] = "confirmed"
    sc.path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    sc.path(tmp_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    identity_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    identity["characters"].append({"id": "BEAST_01", "name": "虎山神"})
    identity_path.write_text(json.dumps(identity, ensure_ascii=False), encoding="utf-8")

    sc.write_missing(tmp_path)
    merged = sc.load(tmp_path)

    assert merged["status"] == "confirmed"
    assert merged["canonical_names"]["BEAST_01"]["canonical_name"] == "虎山神"
    assert merged["dialogue_registers"]["BEAST_01"]["formality"]
