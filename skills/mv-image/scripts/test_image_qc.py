"""mv-image image_qc 单测——纯函数 + 锚点 lint + palette + 汇总。

CI-safe：全部走纯函数 / 降级路径 / fixtures，不依赖 insightface/cv2/onnxruntime 实跑。

从本目录跑：
  cd skills/mv-image/scripts && python3 -m pytest test_image_qc.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("image_qc.py")
spec = importlib.util.spec_from_file_location("mv_image_qc", SCRIPT)
image_qc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(image_qc)


# ── 纯数学：cosine / floor / band ────────────────────────────────────────────

def test_cosine_basic() -> None:
    assert image_qc.cosine([1, 0], [1, 0]) == 1.0
    assert image_qc.cosine([1, 0], [0, 1]) == 0.0
    assert image_qc.cosine([0, 0], [1, 1]) == 0.0   # 零向量


def test_calibrate_floor_takes_min_else_fallback() -> None:
    assert image_qc.calibrate_floor([0.7, 0.6, 0.8]) == 0.6
    assert image_qc.calibrate_floor([]) == 0.50          # 无内部对 → 保守回退
    assert image_qc.floor_calibrated([0.6]) is True
    assert image_qc.floor_calibrated([]) is False


def test_band_severity() -> None:
    assert image_qc.band(0.9, 0.6) == "ok"
    assert image_qc.band(0.58, 0.6, 0.08) == "warn"      # floor-margin ≤ score < floor
    assert image_qc.band(0.3, 0.6, 0.08) == "block"


def test_worst_verdict_and_count() -> None:
    assert image_qc.worst_verdict([]) == "ok"
    assert image_qc.worst_verdict(["ok", "warn", "block"]) == "block"
    assert image_qc.worst_verdict(["ok", "noface"]) == "noface"
    rows = [{"verdict": "block"}, {"verdict": "warn"}, {"verdict": "ok"}, {"no": 1}]
    assert image_qc.count_verdicts(rows) == {"block": 1, "warn": 1, "noface": 0, "ok": 1}


def test_pillow_shot_verdict() -> None:
    assert image_qc.pillow_shot_verdict(False)[0] == "block"          # 图坏 → block
    assert image_qc.pillow_shot_verdict(True, 1024, 1024, 99.0)[0] == "ok"
    v, reasons = image_qc.pillow_shot_verdict(True, 200, 200, 99.0)   # 分辨率不足
    assert v == "warn" and any("分辨率" in r for r in reasons)
    v, reasons = image_qc.pillow_shot_verdict(True, 1024, 1024, 5.0)  # 糊
    assert v == "warn" and any("清晰度" in r for r in reasons)


def test_laplacian_variance_zero_on_flat() -> None:
    assert image_qc.laplacian_variance([100] * 9, 3, 3) == 0.0        # 纯色 → 0
    assert image_qc.laplacian_variance([0] * 4, 2, 2) == 0.0          # 太小 → 0


# ── palette：确定性主色漂移（不需要脸栈） ─────────────────────────────────────

def test_parse_palette_anchor_hex_rgb_and_names() -> None:
    anchors = image_qc.parse_palette_anchor("palette_anchor: #ff0000, rgb(0, 0, 255), 金色霓虹")
    assert (255, 0, 0) in anchors
    assert (0, 0, 255) in anchors
    assert image_qc.COLOR_NAME_RGB["金"] in anchors


def test_rgb_distance_and_nearest() -> None:
    assert image_qc.rgb_distance((0, 0, 0), (0, 0, 0)) == 0.0
    assert round(image_qc.rgb_distance((0, 0, 0), (3, 4, 0)), 4) == 5.0
    assert image_qc.nearest_anchor_distance((10, 10, 10), []) is None
    assert image_qc.nearest_anchor_distance((0, 0, 0), [(255, 0, 0), (5, 5, 5)]) < 10


def test_palette_verdict_flags_far_dominant() -> None:
    anchors = [(200, 40, 40)]   # 红
    # clip 主色全是蓝绿 → 离红很远 → warn
    v, dist = image_qc.palette_verdict([(40, 60, 200), (30, 170, 170)], anchors)
    assert v == "warn" and dist is not None and dist > image_qc.PALETTE_DRIFT_THRESHOLD
    # clip 含一个贴近红的主色 → ok（取最贴近）
    v2, _ = image_qc.palette_verdict([(40, 60, 200), (205, 45, 50)], anchors)
    assert v2 == "ok"
    # 无 anchor → ok（跳过，不臆判）
    assert image_qc.palette_verdict([(1, 2, 3)], [])[0] == "ok"


def test_extract_palette_anchor_reads_blueprint(tmp_path: Path) -> None:
    (tmp_path / "视觉蓝图.md").write_text(
        "# 视觉蓝图\n## 一致性包\npalette_anchor: 深红 #102040 与金色霓虹\n", encoding="utf-8")
    anchors = image_qc.extract_palette_anchor(tmp_path)
    assert (0x10, 0x20, 0x40) in anchors
    assert image_qc.COLOR_NAME_RGB["红"] in anchors
    # 无蓝图 / 无字段 → 空（不臆测）
    assert image_qc.extract_palette_anchor(tmp_path / "nope") == []


# ── 锚点句落地 lint（确定性·便宜） ──────────────────────────────────────────

def _full_anchor_prompt() -> str:
    return (
        "# Clip_003 首帧\n画面：主角嘶吼\n\n"
        "身份锚点：凤眼薄唇·黑色短发·红披风（lead_identity_anchor）\n"
        "视觉锚点：电影颗粒 + palette_anchor 深红霓虹（global_style）\n"
        "母题锚点：红线\n"
        "禁止漂移：换脸/换发色/换主色（forbidden_drift）\n"
    )


def test_anchor_block_presence() -> None:
    p = image_qc.anchor_block_presence(_full_anchor_prompt())
    assert p == {"identity": True, "visual": True, "forbidden": True}
    p2 = image_qc.anchor_block_presence("# Clip_004\n只有画面描述，没有任何锚点块。")
    assert p2 == {"identity": False, "visual": False, "forbidden": False}


def test_lint_clip_prompt_flags_missing_anchor() -> None:
    findings = image_qc.lint_clip_prompt("Clip_004", "# 画面\n主角站在雨中，没有锚点块。")
    codes = {f["code"]: f["level"] for f in findings}
    assert codes.get("missing_anchor_identity") == "warn"
    assert codes.get("missing_anchor_visual") == "warn"
    assert codes.get("missing_anchor_forbidden") == "warn"


def test_lint_clip_prompt_clean_when_all_anchors_present() -> None:
    assert image_qc.lint_clip_prompt("Clip_003", _full_anchor_prompt()) == []


def test_lint_clip_prompt_missing_file_is_warn() -> None:
    findings = image_qc.lint_clip_prompt("Clip_005", None)
    assert findings[0]["code"] == "prompt_missing" and findings[0]["level"] == "warn"


def _make_project(tmp_path: Path, clips: list, prompt_bodies: dict) -> Path:
    (tmp_path / "分镜").mkdir(parents=True, exist_ok=True)
    (tmp_path / "分镜" / "clip_plan.json").write_text(
        json.dumps({"kind": "mv_clip_plan", "clips": clips}, ensure_ascii=False), encoding="utf-8")
    for rel, body in prompt_bodies.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return tmp_path


def test_lint_prompts_over_clip_plan(tmp_path: Path) -> None:
    clips = [
        {"clip_id": "Clip_001", "image_prompt_path": "出图/段落/prompt/Clip_001.md"},
        {"clip_id": "Clip_002", "image_prompt_path": "出图/段落/prompt/Clip_002.md"},
    ]
    root = _make_project(tmp_path, clips, {
        "出图/段落/prompt/Clip_001.md": _full_anchor_prompt(),       # 全锚点 → 干净
        "出图/段落/prompt/Clip_002.md": "# Clip_002\n没有锚点块的裸 prompt。",
    })
    res = image_qc.lint_prompts(root)
    assert res["available"] is True and res["clips_linted"] == 2
    codes = {f["code"] for f in res["findings"]}
    assert "missing_anchor_identity" in codes
    assert all("Clip_002" in f["msg"] for f in res["findings"])     # 干净的 Clip_001 不报


def test_lint_prompts_skips_when_no_plan(tmp_path: Path) -> None:
    res = image_qc.lint_prompts(tmp_path)
    assert res["available"] is False
    assert any("clip_plan" in n for n in res["notes"])


# ── 资产发现：clip 帧（不依赖脸栈） ─────────────────────────────────────────

def test_discover_clip_frames_from_plan(tmp_path: Path) -> None:
    clips = [
        {"clip_id": "Clip_001", "image_path": "出图/段落/图片/Clip_001.png",
         "end_frame_path": "出图/段落/图片/Clip_001_end.png", "need_end_frame": True},
        {"clip_id": "Clip_002", "image_path": "出图/段落/图片/Clip_002.png",
         "end_frame_path": "出图/段落/图片/Clip_002_end.png", "need_end_frame": False},
    ]
    root = _make_project(tmp_path, clips, {})
    frames = image_qc.discover_clip_frames(root)
    cids = {cid for cid, _ in frames}
    assert "Clip_001" in cids and "Clip_001_end" in cids   # need_end_frame=True → 含尾帧
    assert "Clip_002" in cids and "Clip_002_end" not in cids


def test_discover_lead_costume_set_picks_lead(tmp_path: Path) -> None:
    img = tmp_path / "出图" / "共享" / "图片"
    img.mkdir(parents=True)
    for name in ("定妆_主唱.png", "定妆_主唱_侧.png", "定妆_主唱_背.png",
                 "定妆_雨夜街道.png", "定妆_霓虹光效.png", "定妆_主唱_三视图.png"):
        (img / name).write_bytes(b"x")
    lead = image_qc.discover_lead_costume_set(tmp_path)
    assert set(lead.keys()) == {"主", "侧", "背"}    # 场景/光效/三视图被排除
    assert "主唱" in lead["主"]


# ── 汇总 hard vs advisory（与 n2d 同哲学） ──────────────────────────────────

def test_summarize_face_block_is_hard() -> None:
    payload = {"checks": {"face": {"available": True, "mode": "insightface",
                                   "shots": [{"verdict": "block"}, {"verdict": "ok"}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 1
    assert s["verdict"] == "block"


def test_summarize_palette_block_is_only_review() -> None:
    # 主色初筛即便 block 也只算 review（人判），不强制重抽——MV 段落允许加亮/变暗
    payload = {"checks": {"palette": {"available": True, "shots": [{"verdict": "block"}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0
    assert s["verdict"] == "review"


def test_summarize_anchor_lint_is_advisory() -> None:
    payload = {"checks": {}, "lint": {"available": True, "findings": [
        {"level": "warn", "code": "missing_anchor_identity", "msg": "Clip_002：缺身份锚点"}]}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0 and s["advisory"] == 1
    assert s["verdict"] == "review"


def test_summarize_clean_is_ok() -> None:
    payload = {"checks": {"face": {"available": True, "mode": "insightface",
                                   "shots": [{"verdict": "ok"}]},
                          "palette": {"available": True, "shots": [{"verdict": "ok"}]}},
               "lint": {"available": True, "findings": []}}
    assert image_qc.summarize(payload)["verdict"] == "ok"


def test_summarize_pillow_fallback_degrades_to_review() -> None:
    payload = {"checks": {"face": {"available": True, "mode": "pillow_fallback",
                                   "shots": [{"verdict": "ok"}]}},
               "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["hard_blocks"] == 0 and s["degraded"] is True
    assert s["verdict"] == "review"


def test_summarize_unavailable_visual_checks_degrades_to_review() -> None:
    payload = {"checks": {
        "face": {"available": False, "notes": ["未找到主角定妆图"]},
        "palette": {"available": False, "notes": ["未装 Pillow"]}},
        "lint": {"available": True, "findings": []}}
    s = image_qc.summarize(payload)
    assert s["verdict"] == "review" and s["degraded"] is True
    assert set(s["unavailable_visual_checks"]) == {"face", "palette"}


# ── qc_environment 能力 banner ──────────────────────────────────────────────

def test_qc_environment_levels() -> None:
    full = {"checks": {"face": {"available": True, "mode": "insightface", "shots": []},
                       "palette": {"available": True, "shots": []}},
            "summary": {"verdict": "ok"}}
    env = image_qc.qc_environment(full)
    assert env["precision_level"] == "full" and env["jump_to_stage"] == "video"
    assert env["recommended_install"] == ""

    degraded = {"checks": {"face": {"available": True, "mode": "pillow_fallback", "shots": []},
                           "palette": {"available": True, "shots": []}},
                "summary": {"verdict": "ok"}}
    env = image_qc.qc_environment(degraded)
    assert env["precision_level"] == "degraded" and env["jump_to_stage"] == "image"
    assert "insightface" in " ".join(env["missing_or_degraded"])

    none = {"checks": {"face": {"available": False, "notes": ["跳过"]},
                       "palette": {"available": False, "notes": ["跳过"]}},
            "summary": {"verdict": "review"}}
    env = image_qc.qc_environment(none)
    assert env["precision_level"] == "none" and env["jump_to_stage"] == "image_qc_setup"

    env = image_qc.qc_environment(full, with_pixel=False)
    assert env["precision_level"] == "none"


# ── to_findings（与 n2d 同形） ──────────────────────────────────────────────

def test_to_findings_maps_severity_and_dims() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "出图/段落/图片/Clip_03.png", "verdict": "block",
                                "score": 0.2, "floor": 0.6},
                               {"png": "Clip_04.png", "verdict": "ok"}]},
            "palette": {"shots": [{"png": "出图/段落/图片/Clip_05.png", "verdict": "warn",
                                   "nearest_dist": 150}]},
        },
        "lint": {"findings": [{"level": "warn", "code": "missing_anchor_identity",
                               "msg": "Clip_06：缺身份锚点"}]},
    }
    fnds = image_qc.to_findings(payload)
    by = {(f["dim"], f["sev"]) for f in fnds}
    assert ("character_consistency", "block") in by    # 脸崩 hard
    assert ("palette_consistency", "warn") in by        # 主色初筛 warn
    assert ("anchor_prompt_lint", "warn") in by         # 锚点 lint warn
    assert all(f["return_to_stage"] == "image" for f in fnds)
    # face 的 ok 行不进 findings
    assert not any("Clip_04" in str(f.get("loc")) for f in fnds)


def test_to_findings_reports_unavailable() -> None:
    payload = {"checks": {"face": {"available": False, "notes": ["未找到主角定妆图"]},
                          "palette": {"available": False, "notes": ["未装 Pillow"]}},
               "lint": {"findings": []}}
    fnds = image_qc.to_findings(payload)
    assert len(fnds) == 2 and all(f["sev"] == "warn" for f in fnds)
    assert any(f["dim"] == "character_consistency" and "未执行" in f["msg"] for f in fnds)


def test_to_findings_empty_when_clean() -> None:
    payload = {"checks": {"face": {"shots": [{"png": "a.png", "verdict": "ok"}]},
                          "palette": {"shots": [{"png": "a.png", "verdict": "ok"}]}},
               "lint": {"findings": []}}
    assert image_qc.to_findings(payload) == []


# ── 重生成清单 ────────────────────────────────────────────────────────────────

def test_clip_key_extracts_number() -> None:
    assert image_qc._clip_key("出图/段落/图片/Clip_018.png") == "Clip_018"
    assert image_qc._clip_key("Clip_3") == "Clip_003"
    assert image_qc._clip_key(None) is None
    assert image_qc._clip_key("空镜.png") == "空镜.png"


def test_to_regen_list_only_face_block() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "出图/段落/图片/Clip_03.png", "verdict": "block"},
                               {"png": "出图/段落/图片/Clip_04.png", "verdict": "warn"}]},
            "palette": {"shots": [{"png": "出图/段落/图片/Clip_05.png", "verdict": "block"}]},
        },
        "lint": {"findings": [{"level": "warn", "code": "missing_anchor_identity", "msg": "Clip_06"}]},
    }
    regen = image_qc.to_regen_list(payload)
    clips = {r["clip"] for r in regen}
    assert clips == {"Clip_003"}   # 只脸 block 进；脸 warn / 主色 block / 锚点 warn 都不进
    assert "主角脸崩 G1" in regen[0]["reasons"]


def test_to_strict_regen_list_includes_warn_and_palette_and_lint() -> None:
    payload = {
        "checks": {
            "face": {"shots": [{"png": "出图/段落/图片/Clip_03.png", "verdict": "warn"}]},
            "palette": {"shots": [{"png": "出图/段落/图片/Clip_05.png", "verdict": "warn"}]},
        },
        "lint": {"findings": [{"level": "warn", "code": "missing_anchor_forbidden",
                               "msg": "Clip_06：缺禁止漂移锚点"}]},
    }
    regen = image_qc.to_strict_regen_list(payload)
    clips = {r["clip"] for r in regen}
    assert clips == {"Clip_003", "Clip_005", "Clip_006"}


def test_to_regen_list_empty_when_only_advisory() -> None:
    payload = {"checks": {"palette": {"shots": [{"png": "a.png", "verdict": "warn"}]}},
               "lint": {"findings": [{"level": "warn", "code": "missing_anchor_identity", "msg": "Clip_01"}]}}
    assert image_qc.to_regen_list(payload) == []


# ── 端到端：run_qc 在无脸栈环境也产出报告（CI-safe 降级路径） ─────────────────

def test_run_qc_no_pixel_writes_report(tmp_path: Path) -> None:
    clips = [{"clip_id": "Clip_001", "image_prompt_path": "出图/段落/prompt/Clip_001.md"}]
    root = _make_project(tmp_path, clips, {
        "出图/段落/prompt/Clip_001.md": "# Clip_001\n裸 prompt，没有锚点块。"})
    payload = image_qc.run_qc(root, with_pixel=False)
    assert Path(payload["json_path"]).exists()
    assert Path(payload["markdown_path"]).exists()
    # --no-pixel → 像素能力 none，但锚点 lint 仍跑并报缺锚点
    assert payload["qc_environment"]["precision_level"] == "none"
    assert payload["summary"]["verdict"] == "review"   # 锚点缺 → advisory
    on_disk = json.loads(Path(payload["json_path"]).read_text(encoding="utf-8"))
    assert on_disk["kind"] == "mv_image_qc"
