"""marks_consistency 单测——辨识标记归一/搜索词/Clip 段映射/判定 + 端到端 analyze。

cd skills/n2d-review/scripts && python3 -m pytest test_marks_consistency.py
"""
from __future__ import annotations

import json
from pathlib import Path

import marks_consistency as mk


# ── 纯函数 ──────────────────────────────────────────────────────────────────

def test_episode_num():
    assert mk.episode_num("第12集") == 12
    assert mk.episode_num("序章") is None


def test_normalize_mark_permanent_and_acquired():
    perm = mk.normalize_mark({"mark_id": "MARK_左腕旧疤", "type": "疤痕", "region": "左腕",
                              "persistence": "permanent", "keywords": ["左腕旧疤"]})
    assert perm["persistence"] == "permanent" and perm["acquired_ep"] is None
    acq = mk.normalize_mark({"mark_id": "MARK_金瞳", "type": "瞳色", "region": "双眼",
                             "persistence": {"acquired_at": "第3集"}, "keywords": ["金瞳"]})
    assert acq["persistence"] == "acquired" and acq["acquired_ep"] == 3
    acq_num = mk.normalize_mark({"type": "瞳色", "region": "双眼", "persistence": {"acquired_at": 5},
                                 "keywords": ["金瞳"]})
    assert acq_num["acquired_ep"] == 5


def test_normalize_mark_without_any_token_is_none():
    # 无 type/region/keywords/mark_id → 无法机检
    assert mk.normalize_mark({"side": "left"}) is None
    assert mk.normalize_mark("not a dict") is None


def test_mark_tokens_derive_and_filter_single_char():
    toks = mk.mark_tokens({"mark_id": "MARK_左腕旧疤", "type": "疤痕", "region": "左腕",
                           "color": "淡", "keywords": ["左腕旧疤", "x"]})
    assert "左腕旧疤" in toks            # 显式 keyword
    assert "左腕疤痕" in toks            # region+type 组合
    assert "疤痕" in toks and "左腕" in toks
    assert "淡" not in toks              # 单字剔除
    assert "x" not in toks              # 单字剔除


def test_text_has_mark():
    mark = mk.normalize_mark({"type": "疤痕", "region": "左腕", "keywords": ["左腕旧疤"]})
    assert mk.text_has_mark("沈念按住左腕旧疤", mark)
    assert not mk.text_has_mark("沈念怔住", mark)


def test_split_prompt_sections_and_section_for_clip():
    md = ("# 第1集分镜出图\n前言\n"
          "## Clip 1 — 铜镜\n**目标落档**：`出图/第1集/图片/EP01_CLIP01.png` 锁左腕淡疤\n"
          "## Clip 2 — 对峙\n出图/第1集/图片/EP01_CLIP02.png 无标记\n")
    secs = mk.split_prompt_sections(md)
    assert [s[0] for s in secs] == ["EP01_CLIP01", "EP01_CLIP02"]
    assert "左腕淡疤" in mk.section_for_clip("EP01_CLIP01", 0, secs)
    # id 对不上 → 按序号兜底
    assert "对峙" in mk.section_for_clip("", 1, secs)
    assert mk.split_prompt_sections("") == []


def test_evaluate_permanent_missing_warn_present_ok():
    char = {"char_name": "沈念", "marks": [mk.normalize_mark(
        {"type": "疤痕", "region": "左腕", "persistence": "permanent", "plot_load": True,
         "keywords": ["左腕旧疤"]})]}
    miss = mk.evaluate_clip_marks("沈念怒视", [char], 1, "EP01_CLIP02")
    assert miss[0]["verdict"] == "warn" and "载剧情" in miss[0]["message"]
    ok = mk.evaluate_clip_marks("沈念按住左腕旧疤", [char], 1, "EP01_CLIP01")
    assert ok[0]["verdict"] == "ok"


def test_evaluate_acquired_anachronism_block_and_post_ok():
    char = {"char_name": "沈念", "marks": [mk.normalize_mark(
        {"type": "瞳色", "region": "双眼", "persistence": {"acquired_at": "第3集"},
         "keywords": ["金瞳"]})]}
    # 第1集（获得集前）出现金瞳 → block 穿帮
    early = mk.evaluate_clip_marks("沈念睁开金瞳", [char], 1, "EP01_CLIP01")
    assert early[0]["verdict"] == "block" and "第3集之前" in early[0]["message"]
    # 第1集未出现 → ok（还没获得，本就不该有）
    assert mk.evaluate_clip_marks("沈念怔住", [char], 1, "EP01_CLIP01")[0]["verdict"] == "ok"
    # 第4集（获得后）缺失 → warn
    late = mk.evaluate_clip_marks("沈念怔住", [char], 4, "EP04_CLIP01")
    assert late[0]["verdict"] == "warn"


def test_collect_character_marks_only_forms_with_marks():
    reg = {"characters": [
        {"id": "CHAR_01", "name": "沈念", "forms": [
            {"form": "常态", "asset_key": "沈念_常态",
             "identity_marks": [{"type": "疤痕", "region": "左腕", "keywords": ["左腕旧疤"]}]},
            {"form": "无标记态", "asset_key": "沈念_无标记"},  # 无 marks → 不收
        ]},
        {"id": "CHAR_02", "name": "配角", "forms": [{"form": "常态"}]},  # 全无 marks
    ]}
    got = mk.collect_character_marks(reg)
    assert len(got) == 1
    assert got[0]["char_name"] == "沈念" and "CHAR_01" in got[0]["aliases"]


# ── 端到端 ──────────────────────────────────────────────────────────────────

def _make(root: Path, *, marks, clips, prompt_md=None, ep="第1集"):
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "出图" / "共享" / "identity_registry.json").write_text(json.dumps({
        "characters": [{"id": "CHAR_01", "name": "沈念", "forms": [
            {"form": "常态", "asset_key": "沈念_常态", "identity_marks": marks}]}]
    }, ensure_ascii=False), encoding="utf-8")
    (root / "脚本" / ep).mkdir(parents=True)
    (root / "脚本" / ep / "storyboard.json").write_text(json.dumps({"clips": clips},
                                                                   ensure_ascii=False), encoding="utf-8")
    if prompt_md is not None:
        (root / "出图" / ep / "prompt").mkdir(parents=True)
        (root / "出图" / ep / "prompt" / "01_分镜出图.md").write_text(prompt_md, encoding="utf-8")


def test_analyze_warns_on_dropped_permanent_mark(tmp_path: Path):
    root = tmp_path / "剧"
    _make(root,
          marks=[{"mark_id": "MARK_左腕旧疤", "type": "疤痕", "region": "左腕",
                  "persistence": "permanent", "plot_load": True, "keywords": ["左腕旧疤"]}],
          clips=[
              {"id": "EP01_CLIP01", "label": "镜中脸", "shots": [{"desc": "沈念按住左腕旧疤"}]},
              {"id": "EP01_CLIP02", "label": "对峙", "shots": [{"desc": "沈念怒视柳娘子"}]},
          ])
    rep = mk.analyze(str(root), "第1集")
    assert rep["available"] is True
    by = {s["shot"]: s for s in rep["shots"]}
    assert by["EP01_CLIP01"]["verdict"] == "ok"
    assert by["EP01_CLIP02"]["verdict"] == "warn"   # 左腕旧疤在 CLIP02 缺失


def test_analyze_blocks_acquired_mark_anachronism(tmp_path: Path):
    root = tmp_path / "剧"
    _make(root,
          marks=[{"mark_id": "MARK_金瞳", "type": "瞳色", "region": "双眼",
                  "persistence": {"acquired_at": "第3集"}, "keywords": ["金瞳"]}],
          clips=[{"id": "EP01_CLIP01", "label": "睁眼", "shots": [{"desc": "沈念睁开金瞳"}]}])
    rep = mk.analyze(str(root), "第1集")   # 第1集 < 获得集第3集
    blk = [s for s in rep["shots"] if s["verdict"] == "block"]
    assert len(blk) == 1 and "第3集之前" in blk[0]["message"]


def test_analyze_skips_when_no_marks_registered(tmp_path: Path):
    root = tmp_path / "剧"
    _make(root, marks=[], clips=[{"id": "EP01_CLIP01", "label": "x", "shots": [{"desc": "沈念"}]}])
    rep = mk.analyze(str(root), "第1集")
    assert rep["available"] is False and rep["shots"] == []
    assert any("无角色登记 identity_marks" in n for n in rep["notes"])


def test_presence_sidecar_shots_maps_absent_to_warn():
    sidecar = {"findings": [
        {"shot": "EP01_CLIP02", "asset": "MARK_左腕旧疤", "present": False, "confidence": 0.04, "char": "沈念"},
        {"shot": "EP01_CLIP03", "asset": "MARK_金瞳", "present": True, "confidence": 0.9},  # 检出→不报
    ]}
    rows = mk.presence_sidecar_shots(sidecar)
    assert len(rows) == 1
    assert rows[0]["verdict"] == "warn" and rows[0]["shot"] == "EP01_CLIP02"
    assert "像素在场检测未在该帧检出" in rows[0]["message"]
    assert mk.presence_sidecar_shots(None) == []


def test_analyze_merges_presence_sidecar(tmp_path: Path):
    root = tmp_path / "剧"
    _make(root,
          marks=[{"mark_id": "MARK_左腕旧疤", "type": "疤痕", "region": "左腕",
                  "persistence": "permanent", "keywords": ["左腕旧疤"]}],
          clips=[{"id": "EP01_CLIP01", "label": "x", "shots": [{"desc": "沈念按住左腕旧疤"}]}])
    (root / "生产数据").mkdir(parents=True)
    (root / "生产数据" / "marks_presence_第1集.json").write_text(json.dumps({
        "findings": [{"shot": "EP01_CLIP01", "asset": "MARK_左腕旧疤", "present": False, "confidence": 0.03}]
    }, ensure_ascii=False), encoding="utf-8")
    rep = mk.analyze(str(root), "第1集")
    # 文本档 CLIP01 ok（prompt 写了），但像素 sidecar 报缺席 warn → 合并后存在 warn
    assert any(s["verdict"] == "warn" and "像素" in s.get("message", "") for s in rep["shots"])


def test_analyze_uses_prompt_section_corpus(tmp_path: Path):
    # storyboard 镜头文本不含标记，但出图 prompt 段写了 → 应判 ok（语料含 prompt 段）
    root = tmp_path / "剧"
    _make(root,
          marks=[{"mark_id": "MARK_左腕旧疤", "type": "疤痕", "region": "左腕",
                  "persistence": "permanent", "keywords": ["左腕旧疤"]}],
          clips=[{"id": "EP01_CLIP01", "label": "起身", "shots": [{"desc": "沈念起身"}]}],
          prompt_md=("# 第1集\n## Clip 1 — 起身\n"
                     "**资产身份注册层**：`出图/第1集/图片/EP01_CLIP01.png` 锁凤眼薄唇、左腕旧疤。\n"))
    rep = mk.analyze(str(root), "第1集")
    assert {s["shot"]: s for s in rep["shots"]}["EP01_CLIP01"]["verdict"] == "ok"
