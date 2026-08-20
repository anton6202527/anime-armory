#!/usr/bin/env python3
import importlib.util
import json
import os
import tempfile
import unittest
from unittest import mock


HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "compose_prompts.py")
SPEC = importlib.util.spec_from_file_location("mv_compose_prompts", PATH)
composer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(composer)


def semantic_row(clip_id="Clip_001"):
    return {
        "clip_id": clip_id,
        "start_state": "起",
        "action_family": "performance_vocal",
        "energy_level": "Level 6",
        "action": "演唱",
        "vocal_lyrics": "当前一句",
        "action_peak_relative": 0.8,
        "end_state": "止",
        "camera": "推进",
        "lighting": "蓝光",
        "visual_motif": "花",
        "transition_motif": "切",
        "screen_direction": "left_to_right",
        "eyeline": "镜头",
        "prop_state": "无",
        "scene_topology": "舞台",
        "motion_vector": "向前",
    }


class SemanticPromptContractTest(unittest.TestCase):
    def setUp(self):
        self.plan = {"clips": [{
            "clip_id": "Clip_001", "start": 0, "end": 2, "duration": 2,
            "action_peak_anchor": 0.8, "vocal_lyrics": "当前一句",
        }]}

    def test_requires_concrete_generator_and_exact_aligned_lyrics(self):
        payload = {"clips": [semantic_row()]}
        errors = composer.validate_semantic_data(self.plan, payload)
        self.assertTrue(any("generator" in error for error in errors))
        payload["generator"] = {"model": "Test Model", "version": "1"}
        payload["clips"][0]["vocal_lyrics"] = "模型改写"
        errors = composer.validate_semantic_data(self.plan, payload)
        self.assertTrue(any("逐字继承" in error for error in errors))

    def test_complete_receipt_binds_assessment_and_prompt_outputs(self):
        with tempfile.TemporaryDirectory() as root:
            for rel in ("分镜", "词", "字幕", "出图/段落/prompt", "出视频/prompt"):
                os.makedirs(os.path.join(root, rel), exist_ok=True)
            plan = {"clips": [{
                **self.plan["clips"][0],
                "continuity": {}, "shot_design": {},
                "image_prompt_path": "出图/段落/prompt/Clip_001.md",
                "video_prompt_path": "出视频/prompt/Clip_001.md",
            }]}
            plan_path = os.path.join(root, "分镜", "clip_plan.json")
            with open(plan_path, "w", encoding="utf-8") as handle:
                json.dump(plan, handle)
            with open(os.path.join(root, "分镜", "timeline_manifest.json"), "w", encoding="utf-8") as handle:
                json.dump({"clips": []}, handle)
            for rel, text in (
                ("词/lyrics.md", "当前一句"),
                ("字幕/alignment_report.json", "{}"),
                ("视觉蓝图.md", "蓝图"),
                ("出图/段落/prompt/Clip_001.md", "画面必须服务：旧\n- 景别：旧\n- 机位：旧\n- 运镜：旧\n- 光影：旧\n"),
                ("出视频/prompt/Clip_001.md", "- start_state：旧\n- action：旧\n- end_state：旧\n- 动作家族：旧\n- 力量等级：旧\n- 转场母题：旧\n- 景别：旧\n- 运镜：旧\n- 光影：旧\n人物运动：旧；声音约束：无\n"),
            ):
                path = os.path.join(root, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
            assessment = os.path.join(root, "assessment.json")
            payload = {"generator": {"model": "Test Model", "version": "1"}, "clips": [semantic_row()]}
            with open(assessment, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)

            with mock.patch.object(composer.completion, "mark_stage_complete") as complete:
                count = composer.apply_prompts(root, plan, payload, assessment_path=assessment)
            complete.assert_called_once_with(root, "semantic_plan")
            self.assertEqual(count, 1)
            receipt = composer.load_json(os.path.join(root, "分镜", "semantic_prompts.json"))
            self.assertTrue(receipt["complete"])
            self.assertEqual(receipt["schema_version"], 3)
            self.assertEqual(len(receipt["inputs_sha256"]["assessment"]), 64)
            self.assertEqual(len(receipt["prompt_outputs_sha256"]["Clip_001"]["image"]), 64)


if __name__ == "__main__":
    unittest.main()
