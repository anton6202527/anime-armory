import json

import state_ledger_build as build


def test_build_visual_state_ledger_from_storyboards(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    ep1 = root / "脚本" / "第1集"
    ep2 = root / "脚本" / "第2集"
    ep1.mkdir(parents=True)
    ep2.mkdir(parents=True)
    (ep1 / "storyboard.json").write_text(json.dumps({
        "visual_contract": {
            "角色状态演进": {
                "沈念": [
                    {"自": "Clip2", "状态": "左颊新伤", "保持": "至集尾"},
                    {"自": "Clip5", "状态": "金瞳觉醒", "保持": "跨集持续"},
                ]
            }
        }
    }, ensure_ascii=False), encoding="utf-8")
    (ep2 / "storyboard.json").write_text(json.dumps({
        "visual_contract": {
            "角色状态演进": {
                "沈念": [{"自": "Clip1", "状态": "金瞳觉醒解除", "保持": "本镜"}]
            }
        }
    }, ensure_ascii=False), encoding="utf-8")

    data = build.build(str(root))
    assert data["kind"] == build.KIND
    info = data["characters"]["沈念"]
    assert len(info["timeline"]) == 3
    # 至集尾状态只进 timeline，不成为跨集 active modifier。
    assert all("左颊新伤" not in m["description"] for m in info["modifiers"])
    assert any(m["description"] == "金瞳觉醒" and m["active"] is False and m["removed_in"] == "第2集"
               for m in info["modifiers"])
