#!/usr/bin/env python3
import json
from pathlib import Path

import pytest

import apply_split_mapping as ASM
import split_novel as SN


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "作品"
    paras = [item for i in range(1, 7) for item in (f"第{i}章", f"第{i}章正文，危机后反击！")]
    source = root / "小说" / "测试.txt"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(paras) + "\n", encoding="utf-8")
    episodes = ["\n".join(paras[i:i + 2]) for i in range(0, len(paras), 2)]
    for ep in range(1, 3):
        raw = root / "脚本" / f"第{ep}集" / "raw.txt"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(episodes[ep - 1] + "\n", encoding="utf-8")
    SN.write_split_plan(str(root), "测试", str(source), episodes, 2, split_mode="test", genre_note="test", partial=True, source_paras=paras)
    (root / "_进度.md").write_text(
        "# 测试 — 生产进度\n\n| 集 | 字数 | raw | 剧本改编 | bgm |\n|---|---|---|---|---|\n"
        "| 第1集 | 10 | ✅ | ⬜ | ⬜ |\n| 第2集 | 10 | ✅ | ⬜ | — |\n",
        encoding="utf-8",
    )
    mapping = {
        "schema_version": 1,
        "kind": ASM.KIND,
        "approval": {"reviewer": "user:owner", "roles": ["director", "producer"], "approved_at": "2026-07-14T00:00:00+08:00"},
        "window": {"start_episode": 1, "end_episode": 2, "start_source_unit_id": "U000001", "end_source_unit_id": "U000006", "next_source_unit_id": "U000007"},
        "episodes": [
            {"episode": 1, "start_source_unit_id": "U000001", "end_source_unit_id": "U000004", "source_chapters": "1–2"},
            {"episode": 2, "start_source_unit_id": "U000005", "end_source_unit_id": "U000006", "source_chapters": "3"},
        ],
    }
    mapping_path = root / "生产数据" / "拆集映射" / "approved.json"
    mapping_path.parent.mkdir(parents=True)
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    return root, mapping_path


def test_apply_splices_suffix_and_writes_receipt(tmp_path):
    root, mapping = _fixture(tmp_path)
    receipt = ASM.apply_mapping(root, mapping)
    plan = json.loads((root / "脚本" / "split_plan.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "applied"
    assert receipt["splice"] == {
        "old_episode_count": 6,
        "new_episode_count": 5,
        "suffix_old_episode": 4,
        "suffix_new_episode": 3,
        "suffix_start_source_unit_id": "U000007",
    }
    assert plan["episodes"][0]["source_unit_span"]["end_index"] == 4
    assert plan["episodes"][2]["source_unit_span"]["start_index"] == 7
    assert (root / "脚本" / "第1集" / "raw.txt").read_text(encoding="utf-8").startswith("第1章")
    assert (root / receipt["backup"]["path"]).is_file()
    assert list((root / "生产数据" / "边界收据").glob("split_mapping_applied_*.json"))


def test_refuses_downstream_progress(tmp_path):
    root, mapping = _fixture(tmp_path)
    progress = root / "_进度.md"
    progress.write_text(progress.read_text(encoding="utf-8").replace("| 第1集 | 10 | ✅ | ⬜", "| 第1集 | 10 | ✅ | ✅"), encoding="utf-8")
    with pytest.raises(ValueError, match="已有下游进度"):
        ASM.apply_mapping(root, mapping)


def test_refuses_non_contiguous_mapping(tmp_path):
    root, mapping_path = _fixture(tmp_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["episodes"][1]["start_source_unit_id"] = "U000006"
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="连续"):
        ASM.apply_mapping(root, mapping_path)


def test_accepts_crlf_source_when_plan_hash_uses_text_mode_lf(tmp_path):
    root, mapping = _fixture(tmp_path)
    source = root / "小说" / "测试.txt"
    source.write_bytes(source.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    # source-unit semantics stay identical; split_plan's source hash follows
    # Python text-mode universal-newline behavior and therefore also stays LF.
    receipt = ASM.apply_mapping(root, mapping)
    assert receipt["checks"]["source_snapshot_matched"] is True
