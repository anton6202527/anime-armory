"""shot_scale_contract 单测——景别分级解析 + 脸占比矛盾判定 + 端到端（注入假人脸检测器）。
cd skills/n2d-image/scripts && python3 -m pytest test_shot_scale_contract.py
"""
import json
import os
import types

import shot_scale_contract as ssc


# ── 纯函数 ────────────────────────────────────────────────────────────────────

def test_scale_class_from_text():
    assert ssc.scale_class_from_text("CU 浅景深") == "CU"
    assert ssc.scale_class_from_text("大特写 金瞳") == "ECU"
    assert ssc.scale_class_from_text("LS 建制镜") == "LS"
    assert ssc.scale_class_from_text("远景群像") == "LS"
    assert ssc.scale_class_from_text("MS 中景") == "MS"
    assert ssc.scale_class_from_text("无景别信息") is None
    assert ssc.scale_class_from_text("FOCUS") is None         # CU 词边界：不被 FOCUS 误命中


def test_clip_num_of():
    assert ssc.clip_num_of("Clip_01") == 1
    assert ssc.clip_num_of("镜头 13") == 13
    assert ssc.clip_num_of("Clip-7_end.png") == 7
    assert ssc.clip_num_of("封面.png") is None


def test_clip_declared_scales():
    sb = {"clips": [
        {"id": "Clip_01", "shots": [{"lens": "LS 建制"}]},
        {"id": "Clip_02", "shots": [{"lens": "CU 特写"}]},
        {"id": "镜头3", "label": "大特写 金瞳", "shots": [{}]},
        {"id": "Clip_04", "shots": [{"lens": "无景别"}]},   # 抽不到 → 不入表
    ]}
    out = ssc.clip_declared_scales(sb)
    assert out == {1: "LS", 2: "CU", 3: "ECU"}


def test_scale_ratio_contradiction_truth_table():
    # 声明特写但脸极小 → 矛盾
    assert ssc.scale_ratio_contradiction("CU", 0.02)["code"] == "shot_scale_closeup_tiny_face"
    assert ssc.scale_ratio_contradiction("ECU", 0.01)["code"] == "shot_scale_closeup_tiny_face"
    # 声明远景但脸占满 → 矛盾
    assert ssc.scale_ratio_contradiction("LS", 0.40)["code"] == "shot_scale_wide_big_face"
    assert ssc.scale_ratio_contradiction("ELS", 0.30)["code"] == "shot_scale_wide_big_face"
    # 一致 → None
    assert ssc.scale_ratio_contradiction("CU", 0.35) is None       # 特写脸大，正常
    assert ssc.scale_ratio_contradiction("LS", 0.03) is None       # 远景脸小，正常
    # 中景/暧昧档不判
    assert ssc.scale_ratio_contradiction("MS", 0.50) is None
    assert ssc.scale_ratio_contradiction("MCU", 0.01) is None
    # 没检到脸（ratio None）→ 不臆造（无脸特写合法）
    assert ssc.scale_ratio_contradiction("CU", None) is None
    assert ssc.scale_ratio_contradiction(None, 0.5) is None


# ── 端到端（注入假人脸检测器 + 受控脸占比） ───────────────────────────────────

def _setup_project(tmp_path):
    root = tmp_path / "剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_01", "shots": [{"lens": "CU 特写"}]},      # 特写
        {"id": "Clip_02", "shots": [{"lens": "LS 远景"}]},      # 远景
        {"id": "Clip_03", "shots": [{"lens": "CU 铜镜"}]},      # 特写但无脸（道具）→ ratio None
        {"id": "Clip_04", "shots": [{"lens": "MS 中景"}]},      # 中景不判
    ]}, ensure_ascii=False), encoding="utf-8")
    img = root / "出图" / "第1集" / "图片"
    img.mkdir(parents=True)
    for n in ("Clip_01.png", "Clip_02.png", "Clip_03.png", "Clip_04.png"):
        (img / n).write_bytes(b"x")
    return root


def test_analyze_end_to_end_with_injected_detector(tmp_path, monkeypatch):
    import image_qc
    root = _setup_project(tmp_path)
    # 假人脸检测器（只需有 cv2_face_boxes 属性通过可用性闸）
    monkeypatch.setattr(image_qc, "_load_review_module",
                        lambda name: types.SimpleNamespace(cv2_face_boxes=lambda *a, **k: []))
    # 受控脸占比：Clip_01(特写)给极小脸=矛盾；Clip_02(远景)给大脸=矛盾；Clip_03 无脸=None；Clip_04 中景不判
    ratios = {"Clip_01.png": 0.02, "Clip_02.png": 0.45, "Clip_03.png": None, "Clip_04.png": 0.5}
    monkeypatch.setattr(image_qc, "_png_face_ratio_and_size",
                        lambda fm, ap: (ratios.get(os.path.basename(ap)), 1024))
    res = ssc.analyze(root, "第1集")
    assert res["available"] is True
    codes = {(f["code"]) for f in res["findings"]}
    assert codes == {"shot_scale_closeup_tiny_face", "shot_scale_wide_big_face"}
    # Clip_03(无脸特写)和 Clip_04(中景)不产 finding
    assert all("镜3" not in f["msg"] and "镜4" not in f["msg"] for f in res["findings"])


def test_analyze_skips_without_detector(tmp_path, monkeypatch):
    import image_qc
    root = _setup_project(tmp_path)
    # 检测器无 cv2_face_boxes → available False，整段跳过
    monkeypatch.setattr(image_qc, "_load_review_module", lambda name: types.SimpleNamespace())
    res = ssc.analyze(root, "第1集")
    assert res["available"] is False and res["findings"] == []


def test_analyze_available_true_when_no_storyboard_scales(tmp_path, monkeypatch):
    import image_qc
    root = tmp_path / "剧"
    sb_dir = root / "脚本" / "第1集"
    sb_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({"clips": [
        {"id": "Clip_01", "shots": [{"lens": "无景别"}]}]}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(image_qc, "_load_review_module",
                        lambda name: types.SimpleNamespace(cv2_face_boxes=lambda *a, **k: []))
    res = ssc.analyze(root, "第1集")
    assert res["available"] is True and res["checked"] == 0 and res["findings"] == []
