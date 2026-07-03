"""音色跨集漂移检测测试。

跑法：cd skills/n2d-identity/scripts && python3 -m pytest test_voice_consistency.py
"""
import json
from pathlib import Path

import voice_consistency as vc


def _write_manifest(root: Path, ep: str, entries):
    path = root / "合成" / ep / "配音" / "时长清单.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _entry(idx, char, key, shot=None, key_field="音色键"):
    item = {"idx": idx, "角色": char, "文本": f"第{idx}句", "时长": 1.0, "镜头": shot or f"镜头{idx + 1}"}
    if key is not None:
        item[key_field] = key
    return item


def _root(tmp_path: Path) -> Path:
    return tmp_path / "制漫剧" / "测试剧"


def test_missing_voice_key_marks_episode_insufficient_and_no_fake_drift(tmp_path):
    root = _root(tmp_path)
    # 第1集逐句条目没有任何音色键字段（老 manifest）；第2集正常
    _write_manifest(root, "第1集", [_entry(0, "沈念", None), _entry(1, "旁白", None)])
    _write_manifest(root, "第2集", [_entry(0, "沈念", "SHEN"), _entry(1, "旁白", "NARR")])

    report = vc.build_report(root, generated_at="x")

    by_ep = {e["episode"]: e for e in report["episodes"]}
    assert by_ep["第1集"]["status"] == "insufficient_data"
    assert by_ep["第2集"]["status"] == "ok"
    assert report["drifts"] == []  # 数据不足不报假漂移
    assert report["summary"]["episodes_insufficient"] == 1
    assert report["summary"]["episodes_checked"] == 1


def test_cross_episode_voice_key_change_is_drift_with_batch_fields(tmp_path):
    root = _root(tmp_path)
    _write_manifest(root, "第1集", [_entry(0, "沈念", "SHEN"), _entry(1, "旁白", "NARR")])
    _write_manifest(root, "第2集", [
        _entry(0, "旁白", "NARR"),
        _entry(1, "沈念", "SHEN_NEW", shot="镜头2"),
        _entry(2, "沈念", "SHEN_NEW", shot="镜头3"),
    ])

    report = vc.build_report(root, generated_at="x")

    assert report["kind"] == "n2d_identity_voice_drift_report"
    assert len(report["drifts"]) == 1
    drift = report["drifts"][0]
    assert drift["character"] == "沈念"
    assert drift["episode_from"] == "第1集"
    assert drift["episode_to"] == "第2集"
    assert drift["voice_from"] == "SHEN"
    assert drift["voice_to"] == "SHEN_NEW"
    assert drift["first_affected_line_idx"] == 1
    # batch 回流建议字段
    assert drift["return_to_stage"] == "voice"
    assert drift["affected_shots"] == ["镜头2", "镜头3"]
    assert "沈念" in drift["scope"]


def test_intra_episode_voice_key_change_is_drift(tmp_path):
    root = _root(tmp_path)
    _write_manifest(root, "第1集", [
        _entry(0, "沈念", "SHEN"),
        _entry(1, "沈念", "SHEN_B"),
    ])

    report = vc.build_report(root, generated_at="x")

    assert len(report["drifts"]) == 1
    drift = report["drifts"][0]
    assert drift["episode_from"] == drift["episode_to"] == "第1集"
    assert (drift["voice_from"], drift["voice_to"]) == ("SHEN", "SHEN_B")


def test_voicemap_mismatch_is_reported(tmp_path):
    root = _root(tmp_path)
    _write_manifest(root, "第1集", [_entry(0, "沈念", "SHEN_X"), _entry(1, "旁白", "NARR")])
    voicemap = root / "设定库" / "voicemap.json"
    voicemap.parent.mkdir(parents=True, exist_ok=True)
    voicemap.write_text(json.dumps({"沈念": {"key": "SHEN"}, "旁白": {"key": "NARR"}}, ensure_ascii=False), encoding="utf-8")

    report = vc.build_report(root, generated_at="x")

    assert report["drifts"] == []  # 单集内自身稳定，不算跨集漂移
    assert len(report["voicemap_mismatches"]) == 1
    mismatch = report["voicemap_mismatches"][0]
    assert mismatch["character"] == "沈念"
    assert mismatch["voice_key_used"] == "SHEN_X"
    assert mismatch["voice_key_registered"] == "SHEN"
    assert mismatch["return_to_stage"] == "voice"


def test_contract_voice_key_field_also_accepted(tmp_path):
    root = _root(tmp_path)
    _write_manifest(root, "第1集", [_entry(0, "沈念", "SHEN", key_field="voice_key")])
    _write_manifest(root, "第2集", [_entry(0, "沈念", "SHEN2", key_field="voice_key")])

    report = vc.build_report(root, generated_at="x")

    assert report["summary"]["episodes_checked"] == 2
    assert len(report["drifts"]) == 1


def test_placeholder_keys_go_to_revoice_list_not_drift_or_mismatch(tmp_path):
    root = _root(tmp_path)
    # 第1集占位应急轨（say:Tingting#placeholder，n2d-voice voice_manifest 的留痕约定），第2集真音色
    _write_manifest(root, "第1集", [_entry(0, "沈念", "say:Tingting#placeholder", key_field="voice_key")])
    _write_manifest(root, "第2集", [_entry(0, "沈念", "SHEN", key_field="voice_key")])
    voicemap = root / "设定库" / "voicemap.json"
    voicemap.parent.mkdir(parents=True, exist_ok=True)
    voicemap.write_text(json.dumps({"沈念": {"key": "SHEN"}}, ensure_ascii=False), encoding="utf-8")

    report = vc.build_report(root, generated_at="x")

    # 占位→真音色不算漂移、也不算 voicemap 不符；单列待重配
    assert report["drifts"] == []
    assert report["voicemap_mismatches"] == []
    assert len(report["placeholder_revoice"]) == 1
    item = report["placeholder_revoice"][0]
    assert item["character"] == "沈念"
    assert item["episode"] == "第1集"
    assert item["return_to_stage"] == "voice"
    assert report["summary"]["placeholder_revoice"] == 1


def test_write_outputs_atomic_and_md(tmp_path):
    root = _root(tmp_path)
    _write_manifest(root, "第1集", [_entry(0, "沈念", "SHEN")])

    report = vc.build_report(root, generated_at="x")
    paths = vc.write_outputs(root, report)

    assert paths["json"].is_file()
    assert "音色跨集漂移报表" in paths["md"].read_text(encoding="utf-8")
    assert list((root / "生产数据").glob("*.tmp.*")) == []
    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_identity_voice_drift_report"


# ── ⑥ 配音前 pre-flight ────────────────────────────────────────────
def _write_voiceover(root: Path, ep: str, roles):
    path = root / "脚本" / ep / "voiceover.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"[镜头{i + 1}·{r}·平静·常速] 台词{i}" for i, r in enumerate(roles)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_voicemap(root: Path, mapping):
    path = root / "设定库" / "voicemap.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: {"key": v} for k, v in mapping.items()}, ensure_ascii=False), encoding="utf-8")


def test_parse_voiceover_roles_dedupes_in_order(tmp_path):
    root = _root(tmp_path)
    _write_voiceover(root, "第2集", ["沈念", "柳娘子", "沈念"])
    assert vc.parse_voiceover_roles(root, "第2集") == ["沈念", "柳娘子"]


def test_resolve_intended_key_substring():
    vm = {"沈念": "SHEN", "旁白": "NARR"}
    assert vc.resolve_intended_key("沈念旁白", vm) == "SHEN"   # 子串匹配（与 vm_match 同语义）
    assert vc.resolve_intended_key("柳娘子", vm) == ""          # 未登记 → 空


def test_preflight_flags_cross_episode_drift(tmp_path):
    root = _root(tmp_path)
    # 前集已渲染 沈念=SHEN；但 voicemap 被改成 沈念→LIU；本集 voiceover 有 沈念 → 跨集换声预警
    _write_manifest(root, "第1集", [_entry(0, "沈念", "SHEN")])
    _write_voicemap(root, {"沈念": "LIU"})
    _write_voiceover(root, "第2集", ["沈念"])

    rep = vc.preflight(root, "第2集")
    assert rep["summary"]["drift"] == 1
    w = rep["warnings"][0]
    assert w["type"] == "cross_episode_drift" and w["intended_key"] == "LIU" and w["prior_key"] == "SHEN"
    assert w["prior_episode"] == "第1集"


def test_preflight_flags_unregistered_role(tmp_path):
    root = _root(tmp_path)
    _write_voicemap(root, {"沈念": "SHEN"})
    _write_voiceover(root, "第1集", ["小禾"])   # 小禾 不在 voicemap

    rep = vc.preflight(root, "第1集")
    assert rep["summary"]["unregistered"] == 1
    assert rep["warnings"][0]["type"] == "unregistered_in_voicemap"


def test_preflight_clean_when_consistent(tmp_path):
    root = _root(tmp_path)
    _write_manifest(root, "第1集", [_entry(0, "沈念", "SHEN")])
    _write_voicemap(root, {"沈念": "SHEN"})
    _write_voiceover(root, "第2集", ["沈念"])

    rep = vc.preflight(root, "第2集")
    assert rep["summary"]["warnings"] == 0
    assert "✅" in vc.render_preflight_md(rep)


def test_preflight_excludes_target_and_later_episodes(tmp_path):
    root = _root(tmp_path)
    # 目标集自己已有 manifest（重跑场景）不应被当作"前集"用来比对
    _write_manifest(root, "第2集", [_entry(0, "沈念", "SHEN")])
    _write_voicemap(root, {"沈念": "SHEN"})
    _write_voiceover(root, "第2集", ["沈念"])

    rep = vc.preflight(root, "第2集")
    assert rep["summary"]["warnings"] == 0
