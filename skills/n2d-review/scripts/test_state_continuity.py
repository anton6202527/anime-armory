"""state_continuity 单测。
cd skills/n2d-review/scripts && python -m pytest test_state_continuity.py
"""
import json

import state_continuity as st


def test_shot_and_episode_parsing():
    assert st.shot_num("镜3 起左颊新伤") == 3
    assert st.shot_num("shot 12") == 12
    assert st.episode_num("第２集") == 2


def test_shot_num_matches_real_clip_numbering():
    # 真实 producer 用 Clip 编号；若 shot_num 不认 Clip，整个状态哨兵会静默失效。
    assert st.shot_num("Clip14") == 14
    assert st.shot_num("## Clip 14") == 14
    assert st.shot_num("Clip_18") == 18
    assert st.shot_num("片段7") == 7
    assert st.shot_num("至集尾") is None  # 无编号 = 直到集尾


def test_state_sentry_flags_premature_and_missing(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    sb_dir = root / "脚本" / ep
    prompt_dir = root / "出图" / ep / "prompt"
    sb_dir.mkdir(parents=True)
    prompt_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({
        "visual_contract": {
            "角色状态演进": {
                "沈念": [{"自": "镜3", "状态": "左颊新伤", "保持": "至集尾"}]
            }
        },
        "clips": [],
    }, ensure_ascii=False), encoding="utf-8")
    (prompt_dir / "01_分镜出图.md").write_text(
        "## 镜头 1\n**参考图**：`定妆_沈念.png`\n沈念左颊新伤，站在门口。\n"
        "## 镜头 3\n**参考图**：`定妆_沈念.png`\n沈念站在冷宫，衣服干净。\n",
        encoding="utf-8",
    )

    res = st.analyze(str(root), ep)
    kinds = {a["kind"] for a in res["alerts"]}
    assert "premature_state_leak" in kinds
    assert "state_missing_after_start" in kinds
    assert "block" in res["verdicts"]
    assert "warn" in res["verdicts"]


def test_state_sentry_with_clip_numbering(tmp_path):
    # 同 test_state_sentry_flags... 但用真实 Clip 编号（producer 实际写法）。
    # 若 shot_num 退回只认 镜N，所有 start_shot 塌成 1、出图块 shot=None → 0 镜被评估、报绿。
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    sb_dir = root / "脚本" / ep
    prompt_dir = root / "出图" / ep / "prompt"
    sb_dir.mkdir(parents=True)
    prompt_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({
        "visual_contract": {
            "角色状态演进": {
                "沈念": [{"自": "Clip3", "状态": "左颊新伤", "保持": "至集尾"}]
            }
        },
        "clips": [],
    }, ensure_ascii=False), encoding="utf-8")
    (prompt_dir / "01_分镜出图.md").write_text(
        "## Clip 1\n**参考图**：`定妆_沈念.png`\n沈念左颊新伤，站在门口。\n"   # 提前泄露（Clip1 < Clip3）
        "## Clip 3\n**参考图**：`定妆_沈念.png`\n沈念站在冷宫，衣服干净。\n",  # 漏继承（Clip3 起应有伤）
        encoding="utf-8",
    )
    res = st.analyze(str(root), ep)
    kinds = {a["kind"] for a in res["alerts"]}
    assert "premature_state_leak" in kinds
    assert "state_missing_after_start" in kinds


def test_state_sentry_honors_until_end_shot(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    sb_dir = root / "脚本" / ep
    prompt_dir = root / "出图" / ep / "prompt"
    sb_dir.mkdir(parents=True)
    prompt_dir.mkdir(parents=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({
        "visual_contract": {
            "角色状态演进": {
                "沈念": [{"自": "Clip2", "状态": "左颊新伤", "保持": "至 Clip3"}]
            }
        },
        "clips": [],
    }, ensure_ascii=False), encoding="utf-8")
    (prompt_dir / "01_分镜出图.md").write_text(
        "## Clip 2\n**参考图**：`定妆_沈念.png`\n沈念左颊新伤。\n"
        "## Clip 3\n**参考图**：`定妆_沈念.png`\n沈念左颊新伤。\n"
        "## Clip 4\n**参考图**：`定妆_沈念.png`\n沈念衣服干净。\n",
        encoding="utf-8",
    )
    res = st.analyze(str(root), ep)
    assert not any(a["kind"] == "state_missing_after_start" and a["shot"] == 4 for a in res["alerts"])

    (prompt_dir / "01_分镜出图.md").write_text(
        "## Clip 2\n**参考图**：`定妆_沈念.png`\n沈念左颊新伤。\n"
        "## Clip 3\n**参考图**：`定妆_沈念.png`\n沈念左颊新伤。\n"
        "## Clip 4\n**参考图**：`定妆_沈念.png`\n沈念左颊新伤仍在。\n",
        encoding="utf-8",
    )
    res = st.analyze(str(root), ep)
    assert any(a["kind"] == "state_leak_after_end" and a["shot"] == 4 for a in res["alerts"])


def test_single_shot_keep_ends_at_start_shot():
    sb = {
        "visual_contract": {
            "角色状态演进": {
                "沈念": [{"自": "Clip4", "状态": "右手发光", "保持": "本镜"}]
            }
        }
    }
    states = st.states_from_storyboard(sb)
    assert states[0]["start_shot"] == 4
    assert states[0]["end_shot"] == 4


def test_visual_state_ledger_is_consumed(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第2集"
    (root / "脚本" / ep).mkdir(parents=True)
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "出图" / ep / "prompt").mkdir(parents=True)
    (root / "脚本" / ep / "storyboard.json").write_text(json.dumps({"visual_contract": {}, "clips": []}), encoding="utf-8")
    (root / "出图" / "共享" / "visual_state_ledger.json").write_text(json.dumps({
        "kind": "n2d_visual_state_ledger",
        "characters": {"沈念": {"modifiers": [{
            "id": "bandage",
            "description": "左臂带血绷带",
            "added_in": "第1集",
            "active": True,
        }]}}
    }, ensure_ascii=False), encoding="utf-8")
    (root / "出图" / ep / "prompt" / "01_分镜出图.md").write_text(
        "## 镜头 1\n**参考图**：`定妆_沈念.png`\n沈念站着。\n", encoding="utf-8"
    )
    res = st.analyze(str(root), ep)
    assert any(s["source"] == "visual_state_ledger" for s in res["states"])
    assert any(a["kind"] == "state_missing_after_start" for a in res["alerts"])


def _write_prop_ledger(root, props):
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "visual_state_ledger.json").write_text(
        json.dumps({"kind": "n2d_visual_state_ledger", "characters": {}, "props": props},
                   ensure_ascii=False), encoding="utf-8")


def _minimal_storyboard(root, ep):
    sb_dir = root / "脚本" / ep
    sb_dir.mkdir(parents=True, exist_ok=True)
    (sb_dir / "storyboard.json").write_text(json.dumps({"visual_contract": {}, "clips": []},
                                                       ensure_ascii=False), encoding="utf-8")


def test_prop_lifecycle_issue_surfaced_as_alert(tmp_path):
    # 道具 registry 数据质量问题（之前只建账不机检）现在进 alert → gate 会消费
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    _minimal_storyboard(root, ep)
    _write_prop_ledger(root, {
        "PROP_07": {"name": "信物玉佩", "states": ["clean"], "timeline": [],
                    "expected_state": "clean", "stateful_freetext": True,
                    "issues": ["lifecycle 为自由文本但含状态演进语义（默认应结构化）——升级为 {states,transitions} 才能机检"]},
    })
    res = st.analyze(str(root), ep)
    kinds = {a["kind"] for a in res["alerts"]}
    assert "prop_lifecycle_issue" in kinds
    assert "warn" in res["verdicts"]


def test_prop_state_premature_leak_flagged(tmp_path):
    # 结构化 timeline：染血发生在 Clip14；镜10 已画染血 → 提前泄露（warn）
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    _minimal_storyboard(root, ep)
    prompt_dir = root / "出图" / ep / "prompt"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "01_分镜出图.md").write_text(
        "## Clip 10\n信物玉佩 摆在案上，玉佩染血斑斑。\n"
        "## Clip 16\n信物玉佩 染血，握在手心。\n",
        encoding="utf-8")
    _write_prop_ledger(root, {
        "PROP_07": {"name": "信物玉佩", "states": ["clean", "染血"],
                    "timeline": [{"from": "clean", "to": "染血", "trigger": "Clip14", "clip": 14}],
                    "expected_state": "染血", "issues": []},
    })
    res = st.analyze(str(root), ep)
    leaks = [a for a in res["alerts"] if a["kind"] == "prop_state_premature_leak"]
    assert any(a["shot"] == 10 for a in leaks)        # 镜10 提前泄露
    assert not any(a["shot"] == 16 for a in leaks)    # 镜16 在转换镜后，正常
