import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_prompts as pp  # noqa: E402


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "广告项目"
    (root / "脚本").mkdir(parents=True)
    (root / "设定库").mkdir()
    (root / "脚本" / "storyboard.json").write_text(json.dumps({
        "aspect": "9:16",
        "clips": [
            {
                "id": "C01",
                "duration": 3,
                "scene": "App 界面",
                "shot": "手机特写",
                "prompt": "Starbox app UI",
                "assets": {"PROD_APP": True, "BRAND_APP": True},
                "product_lock": "同一品牌色",
                "safe_area": {"core_in_center_4x4": True},
                "continuity": {"need_end_frame": True, "transition": "screen glow"},
            }
        ],
    }, ensure_ascii=False), encoding="utf-8")
    (root / "设定库" / "asset_registry.json").write_text(json.dumps({
        "brand": {"id": "BRAND_APP", "name": "星盒", "text_logo": "星盒", "primary_hex": "#2E9E97", "accent_hex": "#F6C85F"},
        "products": [{"id": "PROD_APP", "name": "星盒 App", "brand_id": "BRAND_APP", "type": "mobile_app"}],
    }, ensure_ascii=False), encoding="utf-8")
    return root


def test_run_writes_prompt_pack_and_jobs(tmp_path):
    root = _project(tmp_path)
    payload = pp.run(root)

    assert payload["summary"] == {"first_frames": 1, "end_frames": 1, "planned": 2}
    assert (root / "出图" / "共享" / "asset_registry.json").is_file()
    assert (root / "出图" / "共享" / "prompt" / "品牌_BRAND_APP.md").is_file()
    assert (root / "出图" / "共享" / "prompt" / "产品_PROD_APP.md").is_file()
    assert (root / "出图" / "分镜" / "prompt" / "00_总览.md").is_file()
    assert (root / "出图" / "分镜" / "prompt" / "镜头01.md").is_file()
    assert (root / "出图" / "分镜" / "prompt" / "镜头01_end.md").is_file()
    assert payload["image_route"] == {"model": "GPT Image 2", "channel": "Codex CLI"}
    assert payload["jobs"][0]["planned_model"] == "GPT Image 2"
    assert payload["jobs"][0]["planned_channel"] == "Codex CLI"


def test_shot_prompt_contains_product_qc_lint_markers(tmp_path):
    root = _project(tmp_path)
    pp.run(root)
    text = (root / "出图" / "分镜" / "prompt" / "镜头01.md").read_text(encoding="utf-8")

    assert "参考图/资产引用" in text
    assert "PROD_APP" in text
    assert "身份锁定句" in text
    assert "同一 logo" in text
    assert "不要改包装文字" in text
    assert "不要变形 logo" in text


def test_manifest_is_not_fake_generation(tmp_path):
    root = _project(tmp_path)
    payload = pp.run(root)

    assert "not faked" in payload["note"]
    assert payload["jobs"][0]["status"] == "planned"
    assert payload["jobs"][0]["expected_output"].endswith("镜头01.png")


def _two_shot_project(tmp_path: Path, name: str = "广告项目") -> Path:
    """同一产品出现在两镜的最小项目（seed 跨镜一致性夹具）。"""
    root = tmp_path / name
    (root / "脚本").mkdir(parents=True)
    (root / "设定库").mkdir()
    (root / "脚本" / "storyboard.json").write_text(json.dumps({
        "aspect": "9:16",
        "shots": [
            {"shot_id": "S1", "scene": "产品 hero", "assets": {"PROD_APP": True},
             "continuity": {"need_end_frame": True}},
            {"shot_id": "S2", "scene": "山谷晨雾空镜"},
            {"shot_id": "S3", "scene": "产品再登场", "assets": {"PROD_APP": True}},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    (root / "设定库" / "asset_registry.json").write_text(json.dumps({
        "brand": {"id": "BRAND_APP", "name": "品牌", "primary_hex": "#224466"},
        "products": [{"id": "PROD_APP", "name": "产品", "brand_id": "BRAND_APP"}],
    }, ensure_ascii=False), encoding="utf-8")
    return root


# ── 稳定 seed 规划：确定性派生 · 同资产跨镜同 seed · 跨项目不同 ───────────────────

def test_planned_seed_is_deterministic_and_project_scoped():
    a = pp.planned_seed_for("项目甲", "PROD_APP")
    assert a == pp.planned_seed_for("项目甲", "PROD_APP")  # 纯确定性：无 random/时间
    assert 0 <= a < pp.SEED_SPACE
    assert a != pp.planned_seed_for("项目乙", "PROD_APP")   # 跨项目不同
    assert a != pp.planned_seed_for("项目甲", "PROD_OTHER")  # 不同资产不同


def test_same_asset_across_shots_shares_one_seed(tmp_path):
    root = _two_shot_project(tmp_path)
    payload = pp.run(root)
    by_id = {j["job_id"]: j for j in payload["jobs"]}

    expected = pp.planned_seed_for(root.name, "PROD_APP")
    # 同一产品的首帧/尾帧/复现镜共享同一 seed（重抽跨镜复用同一随机起点）。
    assert by_id["镜头01_first"]["planned_seed"] == expected
    assert by_id["镜头01_end"]["planned_seed"] == expected
    assert by_id["镜头03_first"]["planned_seed"] == expected
    # 空镜无主资产 → 按镜头标签派生（自身可复现即可），不与产品镜混用。
    assert by_id["镜头02_first"]["planned_seed"] == pp.planned_seed_for(root.name, "镜头02")
    assert by_id["镜头02_first"]["planned_seed"] != expected
    # seed_basis 落 provenance：项目名 + 派生键 + 派生式。
    assert by_id["镜头01_first"]["seed_basis"] == {
        "project": root.name, "seed_key": "PROD_APP",
        "derivation": "zlib.crc32(project|seed_key) % 2^31"}


def test_same_asset_in_different_projects_gets_different_seed(tmp_path):
    seed_a = {j["job_id"]: j["planned_seed"] for j in pp.run(_two_shot_project(tmp_path, "项目甲"))["jobs"]}
    seed_b = {j["job_id"]: j["planned_seed"] for j in pp.run(_two_shot_project(tmp_path, "项目乙"))["jobs"]}
    assert seed_a["镜头01_first"] != seed_b["镜头01_first"]


def test_rerun_produces_identical_seeds(tmp_path):
    root = _two_shot_project(tmp_path)
    first = {j["job_id"]: j["planned_seed"] for j in pp.run(root)["jobs"]}
    second = {j["job_id"]: j["planned_seed"] for j in pp.run(root)["jobs"]}
    assert first == second


def test_seed_capability_recorded_from_adapter_tri_state(tmp_path):
    # 默认路线 GPT Image 2 via Codex：seed 控制明确 unavailable → 如实标注，不假装生效。
    payload = pp.run(_project(tmp_path))
    for job in payload["jobs"]:
        assert job["seed_capability"] == "unavailable"
        assert isinstance(job["planned_seed"], int)  # 不支持也照记 planned_seed（provenance）
    assert payload["seed_policy"]["seed_capability"] == "unavailable"
    assert "不得宣称 seed 生效" in payload["seed_policy"]["note"]


def test_job_seed_info_tolerates_legacy_manifest_jobs():
    # 向后兼容：旧 manifest 的 job 没有 seed 字段——不许炸，如实降级为「未知」。
    legacy = {"job_id": "镜头01_first", "status": "done"}
    info = pp.job_seed_info(legacy)
    assert info == {"planned_seed": None, "seed_capability": "unknown", "seed_basis": {}}
    # 新 manifest 正常读出。
    fresh = {"planned_seed": 42, "seed_capability": "unavailable", "seed_basis": {"seed_key": "PROD_X"}}
    assert pp.job_seed_info(fresh) == {"planned_seed": 42, "seed_capability": "unavailable",
                                       "seed_basis": {"seed_key": "PROD_X"}}


def test_asset_regex_does_not_match_plain_product_or_brand_words():
    shot = {"prompt": "product shot with brand color but no structured ids"}

    assert pp.asset_ids(shot, pp.PROD_RE) == []
    assert pp.asset_ids(shot, pp.BRAND_RE) == []


@pytest.mark.parametrize("brand,product,pid,bid,scene", [
    ("清露", "气泡水", "PROD_QINGLU_BOTTLE", "BRAND_QINGLU", "瓶装饮料 hero"),
    ("岚途", "电动汽车", "PROD_LANTU_CAR", "BRAND_LANTU", "汽车外观 hero"),
    ("安家", "家政服务", "PROD_ANJIA_SERVICE", "BRAND_ANJIA", "服务流程演示"),
    ("云账", "财务软件", "PROD_YUNZHANG_APP", "BRAND_YUNZHANG", "App 界面 demo"),
])
def test_prompt_templates_are_industry_neutral(tmp_path, brand, product, pid, bid, scene):
    root = tmp_path / pid
    (root / "脚本").mkdir(parents=True)
    (root / "设定库").mkdir()
    (root / "脚本" / "storyboard.json").write_text(json.dumps({
        "aspect": "9:16", "shots": [{"shot_id": "S1", "duration": 3, "scene": scene,
        "assets": {pid: True, bid: True}, "safe_area": {"core_in_center_4x4": True}}],
    }, ensure_ascii=False), encoding="utf-8")
    (root / "设定库" / "asset_registry.json").write_text(json.dumps({
        "brand": {"id": bid, "name": brand, "text_logo": brand, "primary_hex": "#224466"},
        "products": [{"id": pid, "name": product, "brand_id": bid,
                      "reference_images": [f"设定库/{pid}.png"]}],
    }, ensure_ascii=False), encoding="utf-8")

    pp.run(root)
    rendered = "\n".join(p.read_text(encoding="utf-8") for p in (root / "出图").rglob("*.md"))
    assert brand in rendered and pid in rendered and bid in rendered
    assert "STARBOX" not in rendered and "Starbox" not in rendered and "星盒" not in rendered
