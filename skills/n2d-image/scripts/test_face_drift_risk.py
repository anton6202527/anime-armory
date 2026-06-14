"""face_drift_risk 单测——评分纯函数 + 角色匹配 + 端到端 analyze。

cd skills/n2d-image/scripts && python3 -m pytest test_face_drift_risk.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("face_drift_risk.py")
spec = importlib.util.spec_from_file_location("face_drift_risk", SCRIPT)
fdr = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fdr)


def test_is_closeup() -> None:
    assert fdr.is_closeup("ECU 面部特写")
    assert fdr.is_closeup("OTS 过肩反打")
    assert fdr.is_closeup("CU 50mm")
    assert not fdr.is_closeup("LS 35mm 慢推")
    assert not fdr.is_closeup("远景全景建制")


def test_has_strong_emotion() -> None:
    assert fdr.has_strong_emotion("沈念崩溃落泪")
    assert fdr.has_strong_emotion("暴怒嘶吼")
    assert not fdr.has_strong_emotion("沈念平静地走过")


def test_extreme_angle_tokens_maps_text_to_risky() -> None:
    risky = ["extreme_top", "extreme_low", "face_too_small", "deep_shadow"]
    assert fdr.extreme_angle_tokens("俯拍顶光", "", risky) == ["extreme_top"]
    assert "face_too_small" in fdr.extreme_angle_tokens("ELS 大全", "群像站位", risky)
    assert "deep_shadow" in fdr.extreme_angle_tokens("", "逆光剪影", risky)
    # risky 不含的项不命中（角色 angle_policy 没声明就不算高危）
    assert fdr.extreme_angle_tokens("俯拍", "", ["face_too_small"]) == []


def test_lock_tier() -> None:
    # Codex 默认：多图参考/图生图可用，但无持久主体 ID。
    assert fdr.lock_tier("codex", {"codex": {"status": "fallback_reference_group"}}, {"status": "not_needed"}) == "multi_reference"
    # Dreamina/即梦官方 CLI 可多参考，但无 n2d 持久主体 ID；不要误判 native。
    assert fdr.lock_tier("dreamina", {"dreamina": {"status": "registered"}}, {"status": "not_needed"}) == "multi_reference"
    # 可灵原生主体库 registered → native_subject。
    assert fdr.lock_tier("kling", {"kling": {"status": "registered"}}, {"status": "not_needed"}) == "native_subject"
    # 可灵但未注册 → native_unregistered，风险建议应提示先注册。
    assert fdr.lock_tier("kling", {"kling": {"status": "unregistered"}}, {}) == "native_unregistered"
    # LoRA ready 压倒一切 → lora
    assert fdr.lock_tier("codex", {"codex": {"status": "fallback_reference_group"}}, {"status": "ready"}) == "lora"


def test_score_reference_group_closeup_emotion_is_high() -> None:
    # multi_reference 底色 22 + 近景全占 30 + 大表情 3 镜(24) → high
    s = fdr.score_character({"appear": 4, "closeup": 4, "emotion": 3, "multi": 0, "angle": 0}, "multi_reference")
    assert s["band"] == "high"
    assert s["score"] >= fdr.BAND_HIGH
    assert s["drivers"][0]["points"] >= s["drivers"][-1]["points"]   # 已按贡献降序


def test_score_lora_low_signal_is_low() -> None:
    # LoRA 档（base 0）+ 极少高危信号 → low
    s = fdr.score_character({"appear": 5, "closeup": 1, "emotion": 0, "multi": 0, "angle": 0}, "lora")
    assert s["band"] == "low"


def test_score_native_midrange() -> None:
    s = fdr.score_character({"appear": 4, "closeup": 2, "emotion": 1, "multi": 0, "angle": 1}, "native_subject")
    assert s["band"] in {"medium", "high"}


def test_suggestions_align_with_expression_gate_and_lora() -> None:
    scored = {"tier": "multi_reference", "band": "high"}
    sig = {"appear": 4, "closeup": 3, "emotion": 2, "multi": 2, "angle": 1}
    sug = fdr.suggestions_for("沈念", scored, sig, "CHAR_01", "常态", "/r/剧",
                              {"canonical": "dreamina", "label": "Dreamina/即梦官方 CLI"})
    joined = " ".join(sug)
    assert "expressions" in joined            # 对齐 ④ 表情库 gate
    assert "lora.py init" in joined           # 对齐 n2d-lora 事前升档
    assert "多人同框" in joined
    assert "清空参考图" in joined              # Dreamina 的粘性参考框要单独提醒
    # 阈值化：单镜 multi（<2）不应触发"多人同框"样板话
    sug_thin = fdr.suggestions_for("沈念", scored, {"appear": 4, "closeup": 0, "emotion": 0, "multi": 1, "angle": 0},
                                   "CHAR_01", "常态")
    assert not any("多人同框" in s for s in sug_thin)
    # 低危角色（lora 档、无信号）→ 不强推 LoRA
    sug_low = fdr.suggestions_for("配角", {"tier": "lora", "band": "low"}, {"appear": 2}, "CHAR_X", "常态")
    assert not any("lora.py init" in s for s in sug_low)


def test_project_default_backend_keeps_nano_banana_separate(tmp_path: Path) -> None:
    root = tmp_path / "剧"
    root.mkdir()
    (root / "_设置.md").write_text("- 生图AI：Nano Banana\n", encoding="utf-8")
    assert fdr.project_default_backend(root) == "nano_banana"
    (root / "_设置.md").write_text("- 生图AI：Gemini\n", encoding="utf-8")
    assert fdr.project_default_backend(root) == "nano_banana"


def test_present_characters_matches_aliases() -> None:
    chars = [
        {"id": "CHAR_01", "aliases": {"沈念", "林婉儿"}},
        {"id": "CHAR_03", "aliases": {"柳娘子"}},
    ]
    present = fdr.present_characters("沈念抬手，柳娘子在画右冷笑", chars)
    assert {c["id"] for c in present} == {"CHAR_01", "CHAR_03"}
    assert fdr.present_characters("空镜，残烛摇曳", chars) == []


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "剧"
    reg = root / "出图" / "共享"
    reg.mkdir(parents=True)
    (reg / "identity_registry.json").write_text(json.dumps({"characters": [
        {"id": "CHAR_01", "name": "沈念 / 林婉儿", "forms": [{
            "form": "常态", "asset_key": "沈念_常态",
            "angle_policy": {"risky": ["face_too_small", "deep_shadow"]},
            "identity_adapters": {"image": {"codex": {"status": "fallback_reference_group"}},
                                  "lora": {"status": "not_needed"}},
        }]},
        {"id": "CHAR_03", "name": "柳娘子", "forms": [{
            "form": "人皮态", "asset_key": "柳娘子_人皮态",
            "angle_policy": {"risky": ["extreme_top"]},
            "identity_adapters": {"image": {"codex": {"status": "fallback_reference_group"}},
                                  "lora": {"status": "ready"}},
        }]},
    ]}, ensure_ascii=False), encoding="utf-8")
    (root / "_设置.md").write_text("- 生图AI：Codex\n", encoding="utf-8")
    sb = root / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "EP01_CLIP01", "label": "沈念崩溃", "scene": "冷宫/夜",
         "continuity": {"start_state": "沈念落泪", "end_state": "沈念失控"},
         "shots": [{"lens": "ECU 面部特写", "desc": "沈念崩溃落泪，柳娘子在画右冷笑"}]},
        {"id": "EP01_CLIP02", "label": "对峙", "scene": "冷宫",
         "shots": [{"lens": "CU 反打", "desc": "沈念怒视柳娘子"}]},
        {"id": "EP01_CLIP03", "label": "空镜", "scene": "庭院",
         "shots": [{"lens": "LS 远景", "desc": "残烛摇曳，无人物"}]},
    ]}, ensure_ascii=False), encoding="utf-8")
    return root


def test_analyze_end_to_end(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    rep = fdr.analyze(root, "第1集")
    assert rep["default_backend"] == "codex"
    by = {r["character_id"]: r for r in rep["characters"]}
    # 沈念：近景+大表情+多人同框，reference_group 底色 → high
    assert by["CHAR_01"]["band"] == "high"
    assert by["CHAR_01"]["signals"]["closeup"] == 2
    assert by["CHAR_01"]["signals"]["multi"] == 2   # CLIP01+CLIP02 都与柳娘子同框
    # 柳娘子：LoRA ready → 档位 lora，分被压低
    assert by["CHAR_03"]["tier"] == "lora"
    assert by["CHAR_03"]["score"] < by["CHAR_01"]["score"]
    # 排序：分高在前
    assert rep["characters"][0]["score"] >= rep["characters"][-1]["score"]


def test_run_writes_reports(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    rep = fdr.run(root, "第1集")
    assert Path(rep["json_path"]).is_file()
    assert Path(rep["markdown_path"]).is_file()
    assert "脸漂风险" in Path(rep["markdown_path"]).read_text(encoding="utf-8")
