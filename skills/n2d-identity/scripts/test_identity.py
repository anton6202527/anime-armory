import hashlib
import json
from pathlib import Path

import identity

MODEL_BYTES = b"fake-lora-model"
MODEL_HASH = hashlib.sha256(MODEL_BYTES).hexdigest()


def _registry():
    return {
        "kind": "n2d_asset_identity_registry",
        "version": 1,
        "characters": [
            {
                "id": "CHAR_WANG",
                "name": "王敦",
                "scope": "全篇",
                "forms": [
                    {
                        "form": "常态",
                        "asset_key": "王敦",
                        "anchor_phrase": "圆脸微胖·短束发·旧青袍",
                        "reference_group": {
                            "front": "出图/共享/图片/定妆_王敦.png",
                            "side": "出图/共享/图片/定妆_王敦_侧.png",
                            "back": "出图/共享/图片/定妆_王敦_背.png",
                            "outfit": "出图/共享/图片/定妆_王敦_半身.png",
                            "turnaround": "出图/共享/图片/定妆_王敦_三视图.png",
                        },
                        "identity_adapters": {
                            "image": {
                                "codex": {"mode": "reference_group", "status": "fallback_reference_group"},
                                "kling": {"mode": "character_id", "status": "registered", "id": "img_klg_wang"},
                            },
                            "video": {
                                "dreamina": {"mode": "first_last_frame", "status": "fallback_reference_group"},
                                "kling": {"mode": "character_id", "status": "registered", "id": "vid_klg_wang"},
                                "seedance": {"mode": "face_lock", "status": "unregistered", "reference": ""},
                                "veo": {"mode": "reference_controls", "status": "unregistered", "id": ""},
                            },
                            "lora": {
                                "status": "ready",
                                "base_model": "flux",
                                "model_path": "models/wang.safetensors",
                                "trigger": "wangdun_char",
                                "dataset": "datasets/wang/dataset_manifest.json",
                                "model_hash": MODEL_HASH,
                                "validation_report": "models/wang_validation_report.json",
                            },
                        },
                        "angle_policy": {"allowed": ["front"], "risky": ["deep_shadow"], "requires_extra_reference": ["side"]},
                        "drift_forbidden": ["face_shape", "hairstyle", "outfit_palette"],
                    }
                ],
            }
        ],
    }


def _root(tmp_path: Path):
    root = tmp_path / "制漫剧" / "测试剧"
    for rel in _registry()["characters"][0]["forms"][0]["reference_group"].values():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
    model = root / "models/wang.safetensors"
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_bytes(MODEL_BYTES)
    report = {
        "kind": "n2d_lora_validation_report",
        "verdict": "pass",
        "model_path": "models/wang.safetensors",
        "model_sha256": MODEL_HASH,
        "warnings": [],
        "manual_review": {"approved": True},
    }
    (root / "models/wang_validation_report.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return root


def test_adapter_matrix_links_reference_group_native_video_and_lora(tmp_path):
    root = _root(tmp_path)
    matrix = identity.build_adapter_matrix(root, _registry(), generated_at="2026-06-08T00:00:00Z")

    form = matrix["forms"][0]
    assert form["reference_group_ready"] is True
    assert form["image_bindings"]["kling"]["ready"] is True
    assert form["image_bindings"]["kling"]["binding"] == "character_id"
    assert form["image_bindings"]["codex"]["binding"] == "reference_group"
    assert form["video_bindings"]["kling"]["ready"] is True
    assert form["video_bindings"]["kling"]["binding"] == "character_id"
    assert form["video_bindings"]["seedance"]["binding"] == "fallback_reference_group"
    assert form["lora_binding"]["ready"] is True
    assert form["gaps"] == []
    assert matrix["summary"]["forms_with_native_image_ready"] == 1
    assert matrix["summary"]["forms_with_native_video_ready"] == 1


def test_lora_ready_dataset_warning_override_requires_notes(tmp_path):
    root = _root(tmp_path)
    report_path = root / "models" / "wang_validation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["warnings"] = ["dataset_has_warnings"]
    report["manual_review"] = {"approved": True, "allow_dataset_warnings": True, "notes": ""}
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    matrix = identity.build_adapter_matrix(root, _registry())
    form = matrix["forms"][0]

    assert form["lora_binding"]["ready"] is False
    assert "lora:ready_dataset_warnings_override_notes_missing" in form["gaps"]
    assert matrix["summary"]["forms_with_lora_ready"] == 0


def test_registered_adapter_without_handle_is_gap(tmp_path):
    root = _root(tmp_path)
    data = _registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["video"]["kling"] = {
        "mode": "character_id",
        "status": "registered",
        "id": "",
    }

    matrix = identity.build_adapter_matrix(root, data)
    gaps = matrix["forms"][0]["gaps"]

    assert "video.kling:ready_without_handle" in gaps


def test_invalid_backend_mode_is_gap(tmp_path):
    root = _root(tmp_path)
    data = _registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["video"]["seedance"] = {
        "mode": "character_id",
        "status": "registered",
        "id": "wrong",
    }

    matrix = identity.build_adapter_matrix(root, data)
    assert "video.seedance:invalid_mode:seedance.character_id" in matrix["forms"][0]["gaps"]


def test_drift_summary_finds_first_bad_episode(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    face_results = {
        "第1集": {"available": True, "shots": [{"char": "王敦", "verdict": "ok", "score": 0.8, "floor": 0.7}]},
        "第2集": {"available": True, "shots": [{"char": "王敦", "verdict": "block", "score": 0.5, "floor": 0.7}]},
    }

    report = identity.summarize_face_results(root, ["第1集", "第2集"], face_results, generated_at="x")

    assert report["characters"]["王敦"]["first_bad_episode"] == "第2集"
    assert report["characters"]["王敦"]["total_block"] == 1


def test_summarize_captures_per_episode_mean_score(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    # face_consistency.analyze 把每角色本集质心接近度放在 result["characters"][char]["ep_mean_score"]
    face_results = {
        "第1集": {"available": True, "shots": [{"char": "王敦", "verdict": "ok", "score": 0.75, "floor": 0.6}],
                  "characters": {"王敦": {"ep_mean_score": 0.75, "ep_n_shots": 4}}},
        "第2集": {"available": True, "shots": [{"char": "王敦", "verdict": "ok", "score": 0.55, "floor": 0.45}],
                  "characters": {"王敦": {"ep_mean_score": 0.55, "ep_n_shots": 5}}},
    }
    report = identity.summarize_face_results(root, ["第1集", "第2集"], face_results, generated_at="x")
    assert report["characters"]["王敦"]["episodes"]["第1集"]["mean_score"] == 0.75
    assert report["characters"]["王敦"]["episodes"]["第2集"]["mean_score"] == 0.55


def test_build_embedding_drift_flags_cross_episode_decline(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    face_results = {
        "第1集": {"available": True, "shots": [{"char": "王敦", "verdict": "ok", "score": 0.75, "floor": 0.45}],
                  "characters": {"王敦": {"ep_mean_score": 0.75, "ep_n_shots": 4}}},
        "第2集": {"available": True, "shots": [{"char": "王敦", "verdict": "ok", "score": 0.55, "floor": 0.45}],
                  "characters": {"王敦": {"ep_mean_score": 0.55, "ep_n_shots": 5}}},
    }
    report = identity.summarize_face_results(root, ["第1集", "第2集"], face_results, generated_at="x")
    fc = identity.load_face_consistency()
    emb = identity.build_embedding_drift(fc, report)
    # 每集各自过 floor(0.45)，但质心从 0.75 掉到 0.55 → 跨集 embedding 漂移 high
    assert "王敦" in emb
    d = emb["王敦"][0]
    assert d["episode_from"] == "第1集" and d["episode_to"] == "第2集" and d["severity"] == "high"


# ── ⑤ 标定地板（不再用全局硬 0.45）─────────────────────────────────
def test_calibrated_abs_low_median_and_empty():
    assert identity.calibrated_abs_low([0.4, 0.4]) == 0.4
    assert identity.calibrated_abs_low([0.6, 0.5, 0.4]) == 0.5      # 奇数取中位
    assert identity.calibrated_abs_low([0.4, 0.6]) == 0.5          # 偶数取均值
    assert identity.calibrated_abs_low([None, None]) is None        # 无 floor → 回退默认
    assert identity.calibrated_abs_low([0.5, None]) == 0.5


def test_build_embedding_drift_calibrated_floor_avoids_false_high(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    # 风格化脸：同人地板 0.40；质心 0.50→0.42（掉 0.08）。全局 0.45 会判 high（0.42<0.45）误报；
    # 用标定地板 0.40 则 0.42≥0.40、掉幅 0.08 → medium（不冤判 high）。
    face_results = {
        "第1集": {"available": True, "shots": [{"char": "柳", "verdict": "ok", "score": 0.50, "floor": 0.40}],
                  "characters": {"柳": {"ep_mean_score": 0.50, "ep_n_shots": 4}}},
        "第2集": {"available": True, "shots": [{"char": "柳", "verdict": "ok", "score": 0.42, "floor": 0.40}],
                  "characters": {"柳": {"ep_mean_score": 0.42, "ep_n_shots": 4}}},
    }
    report = identity.summarize_face_results(root, ["第1集", "第2集"], face_results, generated_at="x")
    fc = identity.load_face_consistency()
    emb = identity.build_embedding_drift(fc, report)
    assert emb["柳"][0]["severity"] == "medium"
    # 对照：同样的均值若用全局 0.45（cross_episode_drift 默认）会被判 high
    assert fc.cross_episode_drift([("第1集", 0.50), ("第2集", 0.42)])[0]["severity"] == "high"


# ── P1 tier 感知漂移标注（升档≠崩脸）─────────────────────────────────
def test_character_current_tier():
    reg = _registry()  # 王敦 lora ready
    assert identity.character_current_tier(reg, "王敦") == "lora"
    # 改成无 lora、有原生主体（kling registered）→ native_subject
    reg2 = _registry()
    reg2["characters"][0]["forms"][0]["identity_adapters"]["lora"] = {"status": "candidate"}
    assert identity.character_current_tier(reg2, "王敦") == "native_subject"
    # 无 lora、无原生（全 fallback）→ reference_group
    reg3 = _registry()
    reg3["characters"][0]["forms"][0]["identity_adapters"]["lora"] = {"status": "candidate"}
    reg3["characters"][0]["forms"][0]["identity_adapters"]["image"] = {
        "codex": {"mode": "reference_group", "status": "fallback_reference_group"}}
    assert identity.character_current_tier(reg3, "王敦") == "reference_group"
    # 对不上号 → ''
    assert identity.character_current_tier(reg, "查无此人") == ""


def test_build_embedding_drift_tier_confound_annotation(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    face_results = {
        "第1集": {"available": True, "shots": [{"char": "王敦", "verdict": "ok", "score": 0.75, "floor": 0.45}],
                  "characters": {"王敦": {"ep_mean_score": 0.75, "ep_n_shots": 4}}},
        "第2集": {"available": True, "shots": [{"char": "王敦", "verdict": "ok", "score": 0.55, "floor": 0.45}],
                  "characters": {"王敦": {"ep_mean_score": 0.55, "ep_n_shots": 5}}},
    }
    report = identity.summarize_face_results(root, ["第1集", "第2集"], face_results, generated_at="x")
    fc = identity.load_face_consistency()
    # 王敦 lora ready → 漂移条目带 tier_confound（提示升档可能致偏移，非崩脸）
    emb = identity.build_embedding_drift(fc, report, _registry())
    assert emb["王敦"][0]["tier_confound"] == "lora"
    assert "升档" in emb["王敦"][0]["tier_confound_note"]
    # 无 registry → 不标注（向后兼容）
    emb2 = identity.build_embedding_drift(fc, report)
    assert "tier_confound" not in emb2["王敦"][0]


# ── P2：embedding 漂移 + 主动升档 + 一角一后端 ─────────────────────────
def _weak_registry(lora_status="candidate", native=False):
    image = {"codex": {"mode": "reference_group", "status": "fallback_reference_group"}}
    if native:
        image["kling"] = {"mode": "character_id", "status": "registered", "id": "x"}
    return {
        "kind": "n2d_asset_identity_registry",
        "characters": [{"id": "CHAR_WANG", "name": "王敦", "forms": [{
            "form": "常态", "asset_key": "王敦",
            "identity_adapters": {"image": image, "lora": {"status": lora_status}},
        }]}],
    }


def _drift(root, episodes, *, embedding_drift=None):
    rep = {"kind": "x", "available": True, "root": str(root),
           "episodes": list(episodes.keys()), "characters": {"王敦": {
               "episodes": episodes, "total_warn": 0, "total_block": 0, "first_bad_episode": ""}}}
    if embedding_drift:
        rep["embedding_drift"] = embedding_drift
    return rep


def test_form_has_native_image_subject():
    assert identity._form_has_native_image_subject(_weak_registry(native=True)["characters"][0]["forms"][0]) is True
    assert identity._form_has_native_image_subject(_weak_registry(native=False)["characters"][0]["forms"][0]) is False


def test_embedding_drift_high_triggers_lora_upgrade(tmp_path):
    # 无 verdict 级漂移，但跨集 embedding 质心 high → 也建议升档
    root = _root(tmp_path)
    eps = {"第1集": {"ok": 4, "warn": 0, "block": 0}, "第2集": {"ok": 5, "warn": 0, "block": 0}}
    drift = _drift(root, eps, embedding_drift={"王敦": [
        {"episode_from": "第1集", "episode_to": "第2集", "drop": 0.2, "severity": "high"}]})
    recs = identity.lora_upgrade_candidates(_weak_registry(), drift)
    assert len(recs) == 1 and recs[0]["embedding_drift_high"] == 1 and recs[0]["proactive"] is False


def test_proactive_upgrade_for_long_line_weak_backend(tmp_path):
    # 0 漂移，但角色跨 3 集 × 无原生主体锁 → 烧积分前主动建议升档
    root = _root(tmp_path)
    eps = {f"第{i}集": {"ok": 3, "warn": 0, "block": 0} for i in (1, 2, 3)}
    recs = identity.lora_upgrade_candidates(_weak_registry(), _drift(root, eps))
    assert len(recs) == 1 and recs[0]["proactive"] is True and recs[0]["episode_count"] == 3


def test_proactive_skips_when_native_subject_registered(tmp_path):
    root = _root(tmp_path)
    eps = {f"第{i}集": {"ok": 3, "warn": 0, "block": 0} for i in (1, 2, 3)}
    assert identity.lora_upgrade_candidates(_weak_registry(native=True), _drift(root, eps)) == []


def test_proactive_skips_below_episode_threshold(tmp_path):
    root = _root(tmp_path)
    eps = {f"第{i}集": {"ok": 3, "warn": 0, "block": 0} for i in (1, 2)}  # 仅 2 集 < 阈值 3
    assert identity.lora_upgrade_candidates(_weak_registry(), _drift(root, eps)) == []


def test_parse_episodes_accepts_chinese_and_fullwidth_numbers():
    available = ["第1集", "第二集", "第３集"]

    assert identity.parse_episodes("一-三", available) == ["第1集", "第二集", "第３集"]
    assert identity.parse_episodes("第２集,第三集", available) == ["第二集", "第３集"]


def _drift_with_blocks(root, char="王敦"):
    face_results = {
        "第1集": {"available": True, "shots": [{"char": char, "verdict": "warn", "score": 0.62, "floor": 0.7}]},
        "第2集": {"available": True, "shots": [{"char": char, "verdict": "block", "score": 0.5, "floor": 0.7}]},
    }
    return identity.summarize_face_results(root, ["第1集", "第2集"], face_results, generated_at="x")


def test_lora_upgrade_candidates_recommends_when_drift_and_lora_not_ready(tmp_path):
    root = _root(tmp_path)
    data = _registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["lora"] = {"status": "candidate"}
    drift = _drift_with_blocks(root)

    recs = identity.lora_upgrade_candidates(data, drift)

    assert len(recs) == 1
    rec = recs[0]
    assert rec["character_id"] == "CHAR_WANG"
    assert rec["lora_status"] == "candidate"
    assert rec["first_bad_episode"] == "第2集"
    assert rec["bad_episodes"] == ["第1集", "第2集"]
    assert "skills/n2d-lora/scripts/lora.py init" in rec["next_command"]
    assert "--character-id CHAR_WANG" in rec["next_command"]


def test_lora_upgrade_candidates_skips_ready_training_and_insufficient_data(tmp_path):
    root = _root(tmp_path)
    drift = _drift_with_blocks(root)

    # lora 已 ready → 不再建议升档
    assert identity.lora_upgrade_candidates(_registry(), drift) == []
    # 已 training → 同样豁免
    data = _registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["lora"] = {"status": "training"}
    assert identity.lora_upgrade_candidates(data, drift) == []
    # 机检不可用（available=false）→ 数据不足，空列表
    skipped = identity.build_drift_report(root, ["第1集"], skip_face=True, registry=data)
    assert skipped["recommendations"] == []
    assert identity.lora_upgrade_candidates(data, skipped) == []


def test_matrix_summary_lists_characters_needing_lora_upgrade(tmp_path):
    root = _root(tmp_path)
    data = _registry()
    data["characters"][0]["forms"][0]["identity_adapters"]["lora"] = {"status": "candidate"}
    drift = _drift_with_blocks(root)

    matrix = identity.build_adapter_matrix(root, data, drift_report=drift)
    assert matrix["summary"]["characters_needing_lora_upgrade"] == ["CHAR_WANG"]

    # 无 drift 数据时为空列表（与判定同源，不瞎编）
    matrix_no_drift = identity.build_adapter_matrix(root, data)
    assert matrix_no_drift["summary"]["characters_needing_lora_upgrade"] == []


# ── ①b 跨集锚点版本快照（registry_anchor_fingerprint）────────────────
def test_anchor_fingerprint_stable_and_sensitive():
    reg = _registry()
    fp0 = identity.registry_anchor_fingerprint(reg)
    assert len(fp0) == 64
    # 同内容 → 同指纹（稳定·可比对）
    assert identity.registry_anchor_fingerprint(_registry()) == fp0
    # 锚点被改（anchor_sha 变）→ 指纹变（diff 里看得见）
    reg2 = _registry()
    reg2["characters"][0]["forms"][0]["anchor_sha"] = "deadbeef" * 8
    assert identity.registry_anchor_fingerprint(reg2) != fp0
    # 表情锚 sha 变也要反映
    reg3 = _registry()
    reg3["characters"][0]["forms"][0]["expression_anchors"] = [{"emotion": "怒", "anchor_sha": "abc"}]
    assert identity.registry_anchor_fingerprint(reg3) != fp0


def test_count_pinned_anchors():
    reg = _registry()
    assert identity.count_pinned_anchors(reg) == 0
    reg["characters"][0]["forms"][0]["anchor_sha"] = "x" * 64
    assert identity.count_pinned_anchors(reg) == 1


def test_matrix_stamps_anchor_fingerprint(tmp_path):
    root = _root(tmp_path)
    reg = _registry()
    reg["characters"][0]["forms"][0]["anchor_sha"] = "y" * 64
    matrix = identity.build_adapter_matrix(root, reg)
    assert matrix["summary"]["anchor_fingerprint"] == identity.registry_anchor_fingerprint(reg)
    assert matrix["summary"]["forms_with_anchor_pinned"] == 1
    # md 渲染带上指纹留痕
    assert "anchor_fingerprint" in identity.render_matrix_md(matrix)


def test_write_outputs(tmp_path):
    root = _root(tmp_path)
    matrix = identity.build_adapter_matrix(root, _registry())
    drift = identity.summarize_face_results(root, ["第1集"], {"第1集": {"available": True, "shots": []}})

    paths = identity.write_outputs(root, matrix, drift)

    assert paths["matrix_json"].is_file()
    assert paths["drift_md"].is_file()
    assert "角色身份 Adapter Matrix" in paths["matrix_md"].read_text(encoding="utf-8")
    assert list((root / "生产数据").glob("*.tmp.*")) == []
