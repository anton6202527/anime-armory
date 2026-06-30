"""从本目录跑：cd skills/n2d-image/scripts && python -m pytest test_asset_impact.py"""
from asset_impact import (normalize, core, ref_tokens, parse_shots,
                          shot_references, shot_key)


def test_normalize_strips_dir_ext_prefix():
    assert normalize("出图/共享/图片/定妆_沈念_侧.png") == "沈念_侧"
    assert normalize("定妆_沈念") == "沈念"
    assert normalize("沈念") == "沈念"


def test_core_drops_view_suffix_keeps_state():
    assert core("定妆_沈念_侧.png") == "沈念"
    assert core("沈念_半身") == "沈念"
    assert core("沈念_觉醒_半身") == "沈念_觉醒"   # 状态保留，仅去视图后缀
    assert core("冷宫寝殿") == "冷宫寝殿"


def test_ref_tokens_splits_fullwidth():
    assert ref_tokens("参考图：沈念、柳娘子、冷宫寝殿") == ["沈念", "柳娘子", "冷宫寝殿"]


SAMPLE = """## 镜头 1（冷开场）🔑关键镜
目标：`出图/第1集/图片/镜头1_赐死冷开场.png`
参考图：沈念、柳娘子、冷宫寝殿、赐死托盘
- [ ] 脸未漂移（对照 定妆_沈念.png）

## 镜头 2（沈念惊醒）
目标：`出图/第1集/图片/镜头2_沈念惊醒.png`
参考图：沈念、冷宫寝殿
"""


def test_parse_shots_extracts_target_and_refline():
    shots = parse_shots(SAMPLE)
    assert len(shots) == 2
    assert shots[0]["target"] == "出图/第1集/图片/镜头1_赐死冷开场.png"
    assert "柳娘子" in ref_tokens(shots[0]["refline"])


def test_shot_references_matches_via_refline():
    shots = parse_shots(SAMPLE)
    assert shot_references(shots[0], {"柳娘子"}) is True       # 镜头1 引用柳娘子
    assert shot_references(shots[1], {"柳娘子"}) is False      # 镜头2 不引用
    assert shot_references(shots[1], {"沈念"}) is True


def test_shot_references_view_suffix_normalized():
    shots = parse_shots(SAMPLE)
    # 用户传 定妆_沈念_侧 → 核心键沈念 → 仍命中（参考图里只写"沈念"）
    assert shot_references(shots[0], {core("定妆_沈念_侧.png")}) is True


# ② 看花胖子式 schema：## Clip N · 镜N，**参考图**：`定妆_x.png`，无目标行
SAMPLE2 = """## Clip 1 · 镜1（ECU / 3.872s）系统主观·冷开场 🔑
**正向 prompt**
```text
极特写主观镜头…
```
**参考图**：`定妆_淡青系统符纹光幕.png`（VFX锚，强度 ~0.8）。**清空人物参考。**

## Clip 11 · 镜9A（LS / 5.0s）回忆·卑微开局
**参考图**：`定妆_王敦.png`、`定妆_山洞.png`
"""


def test_shot_key_derives_clip_and_shot():
    assert shot_key("Clip 1 · 镜1（ECU）") == "Clip_01"
    assert shot_key("Clip 11 · 镜9A") == "Clip_11"
    assert shot_key("镜头 3（铜镜）") == "镜头3"
    assert shot_key("统一参数与锚点句速查") is None


def test_kanhua_schema_prefixed_refs_match():
    shots = parse_shots(SAMPLE2)
    assert shot_references(shots[0], {"淡青系统符纹光幕"}) is True   # 带前缀写法命中
    assert shot_references(shots[1], {"王敦"}) is True
    assert shot_references(shots[0], {"王敦"}) is False             # 不串台


# M8：`定妆_<键>` 前缀匹配必须有边界，短键不得误伤长名
def test_prefixed_match_requires_boundary_no_false_positive():
    shots = parse_shots(SAMPLE)   # 含 `定妆_沈念.png`
    # `沈` 是 `沈念` 的前缀，但 `定妆_沈` 不该命中 `定妆_沈念.png`
    assert shot_references(shots[0], {"沈"}) is False
    # 完整核心键仍命中
    assert shot_references(shots[0], {"沈念"}) is True


def test_prefixed_match_scene_prefix_no_false_positive():
    s = parse_shots("## Clip 2 · 镜2\n**参考图**：`定妆_冷宫寝殿.png`\n")
    assert shot_references(s[0], {"冷宫"}) is False        # 不误伤 冷宫寝殿
    assert shot_references(s[0], {"冷宫寝殿"}) is True


def test_prefixed_match_view_suffix_still_matches():
    s = parse_shots("## Clip 3 · 镜3\n正文出现 定妆_沈念_侧.png 引用\n")
    assert shot_references(s[0], {"沈念"}) is True         # 视图后缀仍算同一资产


def _impact_project(tmp_path):
    import os
    root = tmp_path / "制漫剧" / "剧"
    pd = root / "出图" / "第1集" / "prompt"
    pd.mkdir(parents=True)
    (root / "出图" / "第1集" / "图片").mkdir(parents=True)
    (pd / "01_分镜出图.md").write_text(
        "## 镜头 1（冷开场）\n目标：出图/第1集/图片/镜头1.png\n参考图：沈念、冷宫寝殿\n正文\n"
        "## 镜头 2（反打）\n目标：出图/第1集/图片/镜头2.png\n参考图：沈念\n正文\n",
        encoding="utf-8",
    )
    (root / "出图" / "第1集" / "图片" / "镜头1.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # 镜头1 已出图
    return root


def test_build_rerun_plan_chains_and_minimal_scope(tmp_path):
    from asset_impact import scan, build_rerun_plan
    root = _impact_project(tmp_path)
    keys, hits = scan(str(root), ["沈念"])
    plan = build_rerun_plan(str(root), keys, hits)

    assert plan["kind"] == "n2d_asset_rerun_plan"
    assert plan["affected_episodes"] == ["第1集"]
    assert plan["rerun_count"] == 1 and plan["pending_count"] == 1
    skills = [s["skill"] for s in plan["steps"]]
    assert skills == ["n2d-image", "n2d-identity", "n2d-video", "n2d-compose", "n2d-batch"]
    batch_cmd = plan["steps"][-1]["commands"][0]
    assert "--rerun-from image" in batch_cmd
    assert "镜头1.png" in batch_cmd          # 只含已出图镜头（最小范围）
    assert "镜头2" not in batch_cmd          # 未出图镜头不进重跑


def test_rerun_plan_empty_when_nothing_generated(tmp_path):
    import os
    from asset_impact import scan, build_rerun_plan
    root = tmp_path / "制漫剧" / "剧"
    pd = root / "出图" / "第1集" / "prompt"
    pd.mkdir(parents=True)
    (pd / "01_分镜出图.md").write_text(
        "## 镜头 1\n目标：出图/第1集/图片/镜头1.png\n参考图：沈念\n", encoding="utf-8")
    keys, hits = scan(str(root), ["沈念"])  # 无 PNG → 全 pending
    plan = build_rerun_plan(str(root), keys, hits)
    assert plan["rerun_count"] == 0
    assert plan["steps"] == []
    assert plan["warnings"]


# ── B 部分新增：registry 结构化绑定 / 已出视频 / 后端身份提醒 / batch 任务 JSON ──

def _registry_project(tmp_path):
    """带 identity_registry + asset_registry 的项目：镜头 prompt 只写 ID 绑定，不写参考图行。"""
    import json
    root = tmp_path / "制漫剧" / "剧"
    pd = root / "出图" / "第1集" / "prompt"
    pd.mkdir(parents=True)
    (root / "出图" / "第1集" / "图片").mkdir(parents=True)
    shared = root / "出图" / "共享"
    shared.mkdir(parents=True)
    (shared / "identity_registry.json").write_text(json.dumps({
        "kind": "n2d_asset_identity_registry", "version": 1,
        "characters": [{
            "id": "CHAR_01", "name": "沈念 / 林婉儿", "scope": "全篇",
            "forms": [{
                "form": "常态", "asset_key": "沈念_常态",
                "reference_group": {"front": "出图/共享/图片/定妆_沈念_常态.png", "expressions": []},
                "identity_adapters": {
                    "image": {"kling": {"mode": "subject_library", "status": "registered", "id": "subj_123"},
                              "codex": {"mode": "reference_group", "status": "fallback_reference_group"}},
                    "video": {"seedance": {"mode": "face_lock", "status": "unregistered", "reference": ""}},
                    "lora": {"status": "ready", "base_model": "flux", "model_path": "x.safetensors", "trigger": "t"},
                },
            }],
        }],
    }, ensure_ascii=False), encoding="utf-8")
    (shared / "asset_registry.json").write_text(json.dumps({
        "kind": "n2d_asset_reference_registry", "version": 1,
        "assets": [{"id": "LOC_01", "type": "scene", "name": "冷宫寝殿",
                    "reference_group": {"primary": "出图/共享/图片/定妆_冷宫寝殿.png"}}],
    }, ensure_ascii=False), encoding="utf-8")
    # Clip 1：只有 ID 绑定行（无参考图文本）→ 旧逻辑漏报、新逻辑必须命中
    (pd / "01_分镜出图.md").write_text(
        "## Clip 1 · 镜1（MS）\n目标：出图/第1集/图片/Clip_01.png\n"
        "**资产身份注册层**：`CHAR_01/常态`；从 registry 自动取 reference_group\n"
        "**资产引用注册层**：`LOC_01`\n"
        "## Clip 2 · 镜2（LS 空镜）\n目标：出图/第1集/图片/Clip_02.png\n"
        "纯空镜，无任何资产引用\n",
        encoding="utf-8")
    (root / "出图" / "第1集" / "图片" / "Clip_01.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return root


def test_registry_binding_matches_id_only_shot(tmp_path):
    """盲区①：镜头没写「参考图：」、只写 CHAR_xx/LOC_xx 绑定，靠 registry 也要命中。"""
    from asset_impact import scan
    root = _registry_project(tmp_path)
    keys, hits = scan(str(root), ["沈念_常态"])
    assert len(hits) == 1 and hits[0]["镜头"].startswith("Clip 1")
    # 按角色名（registry name 按 / 拆分）也能定位
    keys, hits = scan(str(root), ["林婉儿"])
    assert len(hits) == 1
    # 场景资产按名字 → LOC_01 命中（prompt 里只有 ID，没有名字）
    keys, hits = scan(str(root), ["冷宫寝殿"])
    assert len(hits) == 1 and hits[0]["镜头"].startswith("Clip 1")
    # 不相干资产不串台
    keys, hits = scan(str(root), ["王敦"])
    assert hits == []


def test_registry_binding_id_boundary_no_false_positive():
    from asset_impact import parse_shots, shot_references_bindings
    shots = parse_shots("## Clip 1\n**资产身份注册层**：`CHAR_011/常态`\n")
    b = [{"id": "CHAR_01", "kind": "character", "names": set(), "keys": set(), "forms": []}]
    assert shot_references_bindings(shots[0], b) is False   # CHAR_01 不命中 CHAR_011
    b2 = [{"id": "CHAR_011", "kind": "character", "names": set(), "keys": set(), "forms": []}]
    assert shot_references_bindings(shots[0], b2) is True


def test_include_video_lists_existing_clips_and_prompt_refs(tmp_path):
    """盲区②：受影响镜头已出 clip / 出视频 prompt 引用了受影响 PNG → 需重生清单。"""
    import os
    from asset_impact import scan, scan_video_impact
    root = _registry_project(tmp_path)
    vdir = root / "出视频" / "第1集" / "视频"
    vdir.mkdir(parents=True)
    (vdir / "Clip_01.mp4").write_bytes(b"\x00")
    (vdir / "Clip_011.mp4").write_bytes(b"\x00")   # 键后接数字，不得误伤
    pdir = root / "出视频" / "第1集" / "prompt"
    pdir.mkdir(parents=True)
    (pdir / "01_clips.md").write_text("首帧：出图/第1集/图片/Clip_01.png", encoding="utf-8")
    keys, hits = scan(str(root), ["沈念_常态"])
    impacts = scan_video_impact(str(root), hits)
    assert len(impacts) == 1
    assert impacts[0]["clips"] == [os.path.join("出视频", "第1集", "视频", "Clip_01.mp4")]
    assert impacts[0]["prompt引用"] == [os.path.join("出视频", "第1集", "prompt", "01_clips.md")]


def test_video_key_boundary_shot_1_vs_10():
    from asset_impact import _key_in_name
    assert _key_in_name("镜头1_开场.mp4", "镜头1") is True
    assert _key_in_name("镜头10_反打.mp4", "镜头1") is False


def test_check_native_adapters_reports_registered_with_handle(tmp_path):
    """盲区③：registered/ready + 句柄 → 「身份注册基于旧定妆」提醒；unregistered 不报。"""
    from asset_impact import load_registry_bindings, match_bindings, native_adapter_notices
    root = _registry_project(tmp_path)
    bindings = match_bindings(load_registry_bindings(str(root)), ["沈念_常态"])
    notices = native_adapter_notices(bindings)
    by_backend = {(n["区域"], n["后端"]) for n in notices}
    assert ("image", "kling") in by_backend          # registered + id
    assert ("lora", "lora") in by_backend            # ready + model_path
    assert ("video", "seedance") not in by_backend   # unregistered 不报
    assert ("image", "codex") not in by_backend      # fallback 无句柄不报
    assert all("重新注册" in n["提醒"] for n in notices)


def test_output_batch_tasks_json_aligns_queue_fields(tmp_path):
    """盲区④：--output-batch-tasks 产物 = queue.py plan --from-asset-impact 可直接消费。"""
    import json
    import os
    from asset_impact import scan, scan_video_impact, build_batch_tasks, main
    root = _registry_project(tmp_path)
    vdir = root / "出视频" / "第1集" / "视频"
    vdir.mkdir(parents=True)
    (vdir / "Clip_01.mp4").write_bytes(b"\x00")
    keys, hits = scan(str(root), ["沈念_常态"])
    plan = build_batch_tasks(str(root), keys, hits, video_impacts=scan_video_impact(str(root), hits))
    assert plan["kind"] == "n2d_asset_rerun_plan"
    by_stage = {t["rerun_from"]: t for t in plan["rerun_tasks"]}
    assert by_stage["image"]["episode"] == "第1集"
    assert by_stage["image"]["affected_shots"] == ["Clip_01"]
    assert by_stage["image"]["affected_artifacts"] == ["出图/第1集/图片/Clip_01.png"]
    assert by_stage["video"]["affected_artifacts"] == [os.path.join("出视频", "第1集", "视频", "Clip_01.mp4")]
    # CLI 端到端：写出文件
    out = tmp_path / "计划.json"
    rc = main([str(root), "沈念_常态", "--include-video", "--output-batch-tasks", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["kind"] == "n2d_asset_rerun_plan"
    assert {t["rerun_from"] for t in data["rerun_tasks"]} == {"image", "video"}
