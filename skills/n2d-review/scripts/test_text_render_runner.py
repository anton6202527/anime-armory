"""text_render_runner manifest 构建 + batch 后端单测。
cd skills/n2d-review/scripts && python -m pytest test_text_render_runner.py
"""
import json
import os

import text_render_runner as tr


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


def _img(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(b"\x89PNG\r\n")


def test_manifest_from_storyboard_text_field(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_TEXT_OCR_BATCH_CMD", raising=False)
    root = str(tmp_path)
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_01", "desc": "系统面板浮现", "图中文字": "等级 3 修为 120"},
                  {"id": "Clip_02", "desc": "宫墙下对话"}]})
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_01.png"))
    m = tr.build_manifest(root, "第1集")
    assert m["kind"] == "n2d_text_render"
    assert len(m["probes"]) == 1
    assert m["probes"][0]["expected_text"] == "等级 3 修为 120"
    assert m["findings"] == []


def test_manifest_from_ui_registry_text_template(tmp_path):
    root = str(tmp_path)
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_01", "desc": "召出 UI_panel 系统面板"}]})
    _w(os.path.join(root, "设定库", "ui_asset_registry.json"),
       {"assets": [{"id": "UI_panel", "text_template": "等级 {lv}", "frame": "x", "palette": [], "font": "x", "layout": "x"}]})
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_01.png"))
    m = tr.build_manifest(root, "第1集")
    assert m["probes"] and m["probes"][0]["expected_text"] == "等级 {lv}"


def test_no_probe_without_image_or_expected(tmp_path):
    root = str(tmp_path)
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_01", "desc": "系统面板"}]})  # 文字镜但无预期文字+无图
    assert tr.build_manifest(root, "第1集")["probes"] == []


def test_write_invokes_batch_backend(tmp_path, monkeypatch):
    root = str(tmp_path)
    _w(os.path.join(root, "脚本", "第1集", "storyboard.json"),
       {"clips": [{"id": "Clip_01", "desc": "系统面板", "render_text": "等级 3"}]})
    _img(os.path.join(root, "出图", "第1集", "图片", "Clip_01.png"))
    fake = tmp_path / "ocr_batch.py"
    fake.write_text(
        "#!/usr/bin/env python3\nimport json,sys\np=sys.argv[1]\nd=json.load(open(p,encoding='utf-8'))\n"
        "d['ocr']='fake'\nd['findings']=[{'shot':'Clip_01','verdict':'block','expected':'等级 3','ocr_text':'等级 8'}]\n"
        "json.dump(d,open(p,'w',encoding='utf-8'),ensure_ascii=False)\n", encoding="utf-8")
    monkeypatch.setenv("N2D_TEXT_OCR_BATCH_CMD", f"python3 {fake}")
    path = tr.write(root, "第1集")
    payload = json.load(open(path, encoding="utf-8"))
    assert payload["ocr"] == "fake"
    assert payload["findings"][0]["verdict"] == "block"
