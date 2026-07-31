"""SP1-V 角色状态演进像素契约单测。
cd skills/n2d/n2d-review/scripts && python -m pytest test_state_pixel_contract.py
"""
import json
import os
import sys

import state_pixel_contract as sp


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


def _img(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n")


# ── 纯函数：状态→检测词桥接 ──────────────────────────────────────────────────
_MARKS = [{
    "char_name": "沈念", "aliases": {"沈念", "CHAR_01", "shen"}, "char_id": "CHAR_01", "form": "常态",
    "marks": [{"mark_id": "MARK_金瞳", "type": "瞳色", "region": "双眼", "keywords": ["金瞳"],
               "detect_phrase": "golden glowing eyes", "persistence": "permanent", "acquired_ep": None}],
}]


def test_resolve_state_probe_bridges_to_registry_detect_phrase():
    state = {"description": "金瞳觉醒态", "terms": ["金瞳", "觉醒态"]}
    asset, phrase = sp.resolve_state_probe(state, "沈念", _MARKS)
    assert asset == "MARK_金瞳" and phrase == "golden glowing eyes"


def test_resolve_state_probe_falls_back_to_chinese_when_no_mark():
    # 无注册 mark 命中（左颊新伤无对应 identity_mark）→ 退化用中文状态描述作弱检测词
    state = {"description": "左颊新伤", "terms": ["左颊", "新伤"]}
    asset, phrase = sp.resolve_state_probe(state, "沈念", _MARKS)
    assert phrase == "左颊新伤"


def test_char_in_corpus_matches_name_or_id():
    assert sp.char_in_corpus("沈念", "沈念立于殿前", _MARKS) is True
    assert sp.char_in_corpus("沈念", json.dumps(["CHAR_01"]), _MARKS) is True
    assert sp.char_in_corpus("沈念", "柳娘子独坐", _MARKS) is False


def test_clip_presence_blob_includes_structured_fields():
    blob = sp.clip_presence_blob({"id": "Clip_03", "character_ids": ["CHAR_01"],
                                  "shots": [{"desc": "沈念立"}]})
    assert "CHAR_01" in blob and "沈念" in blob


# ── 纯函数：逐 probe 双向判定 ────────────────────────────────────────────────
def test_state_finding_premature_leak():
    ea = {"asset": "MARK_金瞳", "phrase": "golden eyes", "expect": "absent", "char": "沈念", "state": "金瞳觉醒态"}
    f = sp.state_finding("Clip_03", ea, present=True, confidence=0.9)
    assert f and f["kind"] == "state_pixel_premature_leak" and f["present"] is True


def test_state_finding_missing_in_range():
    ea = {"asset": "MARK_金瞳", "phrase": "golden eyes", "expect": "present", "char": "沈念", "state": "金瞳觉醒态"}
    f = sp.state_finding("Clip_08", ea, present=False, confidence=0.02)
    assert f and f["kind"] == "state_pixel_missing" and f["expected"] is True


def test_state_finding_consistent_cases_are_none():
    # 区间内·在场 → None；区间前·不在场 → None
    assert sp.state_finding("c", {"expect": "present"}, present=True, confidence=0.9) is None
    assert sp.state_finding("c", {"expect": "absent"}, present=False, confidence=0.0) is None


# ── manifest 构建：逐镜区间 → present/absent 探针 ─────────────────────────────
def _project(root):
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"), {
        "visual_contract": {"角色状态演进": {"沈念": [{"自": "Clip7", "状态": "金瞳觉醒态", "保持": "至集尾"}]}},
        "clips": [
            {"id": "Clip_03", "character_ids": ["CHAR_01"], "shots": [{"desc": "沈念立于殿前"}]},
            {"id": "Clip_08", "character_ids": ["CHAR_01"], "shots": [{"desc": "沈念回眸，金瞳大盛"}]},
        ]})
    _w(os.path.join(root, "出图", "共享", "identity_registry.json"), {"characters": [
        {"id": "CHAR_01", "name": "沈念", "forms": [{"form": "常态", "asset_key": "shen", "identity_marks": [
            {"mark_id": "MARK_金瞳", "type": "瞳色", "region": "双眼", "keywords": ["金瞳"],
             "detect_phrase": "golden glowing eyes", "plot_load": True}]}]}]})
    for c in ("Clip_03", "Clip_08"):
        _img(os.path.join(root, "出图", "第1集", "图片", f"{c}.png"))


def test_build_manifest_marks_prestart_absent_and_inrange_present(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_MARKS_PRESENCE_CMD", raising=False)
    root = str(tmp_path)
    _project(root)
    man = sp.build_manifest(root, "第1集")
    assert man["kind"] == "n2d_state_pixel"
    by_shot = {p["shot"]: p["expected_assets"][0] for p in man["probes"]}
    assert by_shot["Clip_03"]["expect"] == "absent"   # 镜在金瞳起点(7)之前 → 查提前泄露
    assert by_shot["Clip_08"]["expect"] == "present"  # 镜在区间内 → 查应有
    assert by_shot["Clip_08"]["phrase"] == "golden glowing eyes"
    assert man["findings"] == []  # 无检测器命令 → 不臆造在场结论


def test_build_manifest_skips_clip_without_state_character(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_MARKS_PRESENCE_CMD", raising=False)
    root = str(tmp_path)
    _project(root)
    # 加一镜不含沈念 → 不产探针（避免对未在场角色误报）
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"), {
        "visual_contract": {"角色状态演进": {"沈念": [{"自": "Clip7", "状态": "金瞳觉醒态", "保持": "至集尾"}]}},
        "clips": [{"id": "Clip_05", "character_ids": ["CHAR_99"], "shots": [{"desc": "柳娘子独坐"}]}]})
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_05.png"))
    man = sp.build_manifest(root, "第1集")
    assert man["probes"] == []


def test_fill_findings_bidirectional_with_injected_detector(tmp_path):
    root = str(tmp_path)
    _project(root)
    fake = os.path.join(root, "fake.py")
    with open(fake, "w") as fh:
        fh.write("import json; print(json.dumps({'present': True, 'confidence': 0.9}))\n")
    os.environ["N2D_MARKS_PRESENCE_CMD"] = f"{sys.executable} {fake}"
    try:
        man = sp.fill_findings(root, sp.build_manifest(root, "第1集"))
    finally:
        del os.environ["N2D_MARKS_PRESENCE_CMD"]
    kinds = {f["shot"]: f["kind"] for f in man["findings"]}
    # 金瞳在两帧都"检出"：Clip_03(起点前)=提前泄露；Clip_08(区间内·在场)=无 finding
    assert kinds.get("Clip_03") == "state_pixel_premature_leak"
    assert "Clip_08" not in kinds
