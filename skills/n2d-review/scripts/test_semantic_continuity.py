"""semantic_continuity 单测。
cd skills/n2d-review/scripts && python -m pytest test_semantic_continuity.py
"""
import json

import semantic_continuity as sc


def test_salient_terms_and_coverage():
    terms = sc.salient_terms({"状态": "镜3起左颊新伤", "mode": "match_cut"})
    assert "左颊新伤" in terms or "镜3起左颊新伤" in terms
    assert "match_cut" in terms
    cov, missing = sc.coverage(["左颊新伤", "match_cut"], "本镜保持左颊新伤，转场 match_cut")
    assert cov == 1.0 and missing == []
    cov, missing = sc.coverage(["左颊新伤"], "沈念左脸新伤，视线压低")
    assert cov == 1.0 and missing == []


def test_analyze_flags_missing_downstream_contract_terms(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    sb_dir = root / "脚本" / ep
    img_dir = root / "出图" / ep / "prompt"
    vid_dir = root / "出视频" / ep / "prompt"
    sb_dir.mkdir(parents=True)
    img_dir.mkdir(parents=True)
    vid_dir.mkdir(parents=True)
    (sb_dir / "voiceover.txt").write_text("[镜头1·沈念·冷冽] 谁敢动我。 💥爽点\n", encoding="utf-8")
    (sb_dir / "storyboard.json").write_text(json.dumps({
        "visual_contract": {
            "色调基线": "冷青压暗红",
            "角色状态演进": {"沈念": [{"自": "镜3", "状态": "左颊新伤", "保持": "至集尾"}]},
            "景别阶梯": "MS→CU",
        },
        "style_contract": {"风格名": "国漫写实", "风格禁忌": ["欧美脸漂移", "页游塑料盔甲"]},
        "clips": [{
            "id": "EP01_CLIP01",
            "scene": "冷宫寝殿/夜/内",
            "rhythm": "爽点·CU硬切",
            "continuity": {
                "start_state": "沈念左颊新伤，画左起身",
                "end_state": "沈念金瞳亮起，视线画右",
                "transition": "match_cut",
            },
        }],
    }, ensure_ascii=False), encoding="utf-8")
    # 下游故意只写泛化文案，缺关键契约词。
    (img_dir / "00_总览.md").write_text("## 本集视觉一致性契约\n- 色调：统一\n", encoding="utf-8")
    (img_dir / "01_分镜出图.md").write_text("## Clip 1\n**参考图**：`定妆_沈念.png`\n普通出图。\n", encoding="utf-8")
    (vid_dir / "00_总览.md").write_text("## 本集导演一致性契约\n统一风格。\n", encoding="utf-8")
    (vid_dir / "01_clips.md").write_text("## Clip 1\n普通运动。\n", encoding="utf-8")

    res = sc.analyze(str(root), ep)
    assert res["available"] is True
    assert any("视觉契约" in f["message"] for f in res["findings"])
    assert any(f["source"].endswith("continuity") for f in res["findings"])
    assert "warn" in res["verdicts"]
