#!/usr/bin/env python3
import json
import os
import tempfile
import unittest
import shutil
import wave

import export_otio
import picture_lock
import render_animatic


class ProductionControlsTest(unittest.TestCase):
    def make_project(self, root):
        for rel in ("分镜", "节拍", "歌", "生产数据/image_qc", "制片", "出图/段落/图片"):
            os.makedirs(os.path.join(root, rel), exist_ok=True)
        clip = {"clip_id": "Clip_001", "duration": 2.0, "start": 0, "end": 2,
                "image_path": "出图/段落/图片/Clip_001.png", "selected_video_path": "出视频/视频/Clip_001.mp4"}
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"is_demo": True}, f)
        with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
            json.dump({"clips": [clip]}, f)
        with open(os.path.join(root, "分镜", "timeline_manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "Test", "clips": [{"clip_id": "Clip_001", "duration": 2.0,
                                                       "video_path": "出视频/视频/Clip_001.mp4"}]}, f)
        for rel in ("节拍/beatgrid.json", "生产数据/image_qc/image_qc.json"):
            with open(os.path.join(root, rel), "w", encoding="utf-8") as f: f.write("{}")
        for rel in ("歌/song.wav", "分镜/animatic.mp4", "出图/段落/图片/Clip_001.png"):
            with open(os.path.join(root, rel), "wb") as f: f.write(b"asset")
        export_otio.write_export(root, rate=24)
        os.makedirs(os.path.join(root, "生产数据", "animatic"), exist_ok=True)
        timeline = json.load(open(os.path.join(root, "分镜", "timeline_manifest.json"), encoding="utf-8"))
        with open(os.path.join(root, "生产数据", "animatic", "animatic.json"), "w", encoding="utf-8") as f:
            json.dump({
                "output_sha256": export_otio.mv_utils.content_hash(os.path.join(root, "分镜", "animatic.mp4")),
                "timeline_edit_sha256": export_otio.mv_utils.timeline_edit_hash(timeline),
            }, f)

    def test_picture_lock_binds_all_inputs(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_project(root)
            payload = picture_lock.build_lock(root, "director", "approved")
            self.assertTrue(payload["accepted"])
            self.assertIn("分镜/animatic.mp4", payload["inputs_sha256"])
            self.assertIn("出图/段落/图片/Clip_001.png", payload["inputs_sha256"])
            self.assertEqual(payload["editorial_timeline_sha256"], payload["otio_timeline_sha256"])

    def test_otio_contains_timed_external_clip(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_project(root)
            payload = export_otio.build(root, rate=24)
            clip = payload["tracks"]["children"][0]["children"][0]
            self.assertEqual(clip["name"], "Clip_001")
            self.assertEqual(clip["source_range"]["duration"]["value"], 48.0)
            self.assertEqual(payload["tracks"]["children"][1]["kind"], "Audio")

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_renders_real_animatic(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "分镜"))
            os.makedirs(os.path.join(root, "歌"))
            os.makedirs(os.path.join(root, "出图", "段落", "图片"))
            image_rel = "出图/段落/图片/Clip_001.ppm"
            with open(os.path.join(root, image_rel), "wb") as f:
                f.write(b"P6\n2 2\n255\n" + bytes([255, 0, 0] * 4))
            with wave.open(os.path.join(root, "歌", "song.wav"), "wb") as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000); wav.writeframes(b"\0\0" * 2000)
            with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": [{"clip_id": "Clip_001", "duration": 0.25, "image_path": image_rel}]}, f)
            output = render_animatic.render(root)
            self.assertTrue(os.path.getsize(output) > 0)
            self.assertTrue(os.path.exists(os.path.join(root, "生产数据", "animatic", "animatic.json")))
            source = open(render_animatic.__file__, encoding="utf-8").read()
            self.assertNotIn('"-shortest"', source)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_animatic_rejects_plan_that_would_cut_song(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "分镜"))
            os.makedirs(os.path.join(root, "歌"))
            os.makedirs(os.path.join(root, "出图", "段落", "图片"))
            image_rel = "出图/段落/图片/Clip_001.ppm"
            with open(os.path.join(root, image_rel), "wb") as f:
                f.write(b"P6\n2 2\n255\n" + bytes([255, 0, 0] * 4))
            with wave.open(os.path.join(root, "歌", "song.wav"), "wb") as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000); wav.writeframes(b"\0\0" * 8000)
            with open(os.path.join(root, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": [{"clip_id": "Clip_001", "duration": 0.25, "image_path": image_rel}]}, f)
            with self.assertRaisesRegex(RuntimeError, "不能用截歌"):
                render_animatic.render(root)


if __name__ == "__main__":
    unittest.main()
