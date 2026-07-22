"""multishot_plan 纯逻辑单测（原生多镜执行计划 + seam 消费 helper）。
cd skills/n2d-video/scripts && python3 -m pytest test_multishot_plan.py
"""
import multishot_plan as mp


ROUTES = {
    "routes": [
        {"clip_id": "Clip_01", "primary_backend": "seedance"},
        {"clip_id": "Clip_02", "primary_backend": "seedance"},
        {"clip_id": "Clip_03", "primary_backend": "seedance"},
        {"clip_id": "Clip_07", "primary_backend": "seedance"},
        {"clip_id": "Clip_08", "primary_backend": "seedance"},
    ],
    "multishot_groups": [
        {"group_id": "MSG_01", "members": ["Clip_01", "Clip_02", "Clip_03"],
         "backend": "seedance", "approx_seconds": 9.0},
        {"group_id": "MSG_02", "members": ["Clip_07", "Clip_08"],
         "backend": "seedance", "approx_seconds": 6.0},
    ],
}


def test_setting_parse():
    assert mp.setting_is_on("开启") and mp.setting_is_on("on") and mp.setting_is_on("1")
    assert not mp.setting_is_on("关闭") and not mp.setting_is_on("") and not mp.setting_is_on(None)


def test_inactive_is_zero_behavior_change():
    plan = mp.resolve_plan(ROUTES, active=False)
    assert plan["groups"] == [] and plan["model_handled_seams"] == []
    assert mp.seam_is_model_handled("Clip_02", plan) is False


def test_active_marks_intra_group_non_first_members():
    plan = mp.resolve_plan(ROUTES, active=True)
    assert {g["group_id"] for g in plan["groups"]} == {"MSG_01", "MSG_02"}
    # 组内非首成员的接缝由模型消除；组首成员入点接缝仍逐镜
    assert plan["model_handled_seams"] == ["Clip_02", "Clip_03", "Clip_08"]
    assert mp.seam_is_model_handled("Clip_02", plan) is True
    assert mp.seam_is_model_handled("Clip_03", plan) is True
    assert mp.seam_is_model_handled("Clip_08", plan) is True
    # 组首与非成员仍逐镜（不放松）
    assert mp.seam_is_model_handled("Clip_01", plan) is False
    assert mp.seam_is_model_handled("Clip_07", plan) is False
    assert mp.seam_is_model_handled("Clip_99", plan) is False


def test_singleton_group_ignored():
    routes = {"multishot_groups": [{"group_id": "MSG_X", "members": ["Clip_01"], "backend": "seedance"}]}
    plan = mp.resolve_plan(routes, active=True)
    assert plan["groups"] == []


def test_no_groups_safe():
    plan = mp.resolve_plan({}, active=True)
    assert plan["groups"] == [] and plan["model_handled_seams"] == []
    assert mp.summarize(plan)["group_count"] == 0


def test_build_inactive_when_setting_off(tmp_path):
    import os
    root = str(tmp_path)
    pdir = os.path.join(root, "出视频", "第1集", "prompt")
    os.makedirs(pdir, exist_ok=True)
    import json
    with open(os.path.join(pdir, "video_model_routes.json"), "w", encoding="utf-8") as f:
        json.dump(ROUTES, f, ensure_ascii=False)
    # 无 _设置.md → 选择点默认关闭 → 不激活（即便后端支持、有候选组）
    plan = mp.build(root, "第1集")
    assert plan["active"] is False
    assert plan["summary"]["group_count"] == 0


if __name__ == "__main__":
    import tempfile
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
            except TypeError:
                fn(tempfile.mkdtemp())
            print("ok", name)


def test_primary_is_multishot_reads_capability_table_without_groups():
    # 修复前 import 不存在的 is_multishot_native_backend 会静默 fallback 到「有没有 groups」
    assert mp._primary_is_multishot({"routes": [{"primary_backend": "seedance"}]}) is True
    assert mp._primary_is_multishot({"routes": [{"primary_backend": "即梦"}]}) is False  # dreamina 非 multishot_native
    assert mp._primary_is_multishot({"routes": [{"primary_backend": "luma"}]}) is False


def test_build_inactive_recommends_savings_when_backend_supports(tmp_path):
    import json as _json
    root = tmp_path / "作品"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "video_model_routes.json").write_text(
        _json.dumps(ROUTES, ensure_ascii=False), encoding="utf-8")
    plan = mp.build(str(root), "第1集")
    assert plan["active"] is False
    # 3+2 成员的两组 → 省 (3-1)+(2-1)=3 次
    assert any("省额度推荐" in n and "3 次" in n for n in plan["notes"])
