#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile

import observe


def test_select_can_write_chapter_observation_packet():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "素材"), exist_ok=True)
        args = type("Args", (), {
            "project_root": root,
            "source": "observation",
            "domain": "县城医院",
            "text": "候诊区叫号屏坏了一半，护士靠喊名字维持秩序。",
            "sensory": "消毒水味、塑料椅发黏",
            "behavior": "家属手一直捏缴费单",
            "dramatic_use": "pressure,setting",
            "tags": "医院,等待",
            "scene": "",
            "privacy": "anonymized",
            "consent_note": "",
            "transfer_rule": "借等待压力，不照搬真人。",
        })()
        observe.add_record(args)

        records = observe.select_records(root, tag="医院", dramatic_use="pressure", limit=5)
        path = observe.write_selection_packet(
            root,
            records,
            tag="医院",
            dramatic_use="pressure",
            chapter=3,
        )
        assert os.path.exists(path)
        assert path.endswith("写作任务/观察素材_第03章.md")
        text = open(path, encoding="utf-8").read()
        assert "候诊区叫号屏坏了一半" in text
        assert "借等待压力" in text
