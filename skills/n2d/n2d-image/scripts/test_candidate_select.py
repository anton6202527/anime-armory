"""candidate_select 纯排序/选片/纠偏/可用率单测。
cd skills/n2d/n2d-image/scripts && python -m pytest test_candidate_select.py
"""
import json
import os

import candidate_select as cs


def _c(name, **kw):
    return dict(path=f"/x/{name}.png", candidate=name, **kw)


def test_hard_fail_disqualified_and_sinks():
    cands = [_c("a", face_consistency=0.9, qc_hard_fail=True),
             _c("b", face_consistency=0.6)]
    r = cs.select_best(cands)
    assert r["picked"]["candidate"] == "b"          # 崩脸的 a 即便 face 高也淘汰
    assert r["disqualified"] == 1 and r["survivors"] == 1


def test_all_hard_fail_triggers_reroll():
    cands = [_c("a", qc_hard_fail=True), _c("b", qc_hard_fail=True)]
    r = cs.select_best(cands)
    assert r["picked"] is None and r["reroll_needed"] and "硬伤" in r["reason"]


def test_best_below_identity_floor_triggers_reroll():
    cands = [_c("a", face_consistency=0.40), _c("b", face_consistency=0.38)]
    r = cs.select_best(cands, identity_floor=0.45)
    assert r["picked"]["candidate"] == "a" and r["reroll_needed"]  # 最好的也崩脸


def test_deterministic_rank_by_face_then_quality():
    cands = [_c("a", face_consistency=0.7, sharpness=0.2),
             _c("b", face_consistency=0.8, sharpness=0.1),
             _c("c", face_consistency=0.7, sharpness=0.9)]
    r = cs.select_best(cands)
    assert r["picked"]["candidate"] == "b"          # face 余弦主信号
    assert [x["candidate"] for x in r["ranked"]][0] == "b"


def test_vlm_ranker_is_pairwise_not_absolute():
    # VLM 偏好 c（即便 c 确定性分不是最高）——验证 VLM 当 ranker 用、能覆盖确定性次序
    cands = [_c("a", face_consistency=0.7), _c("b", face_consistency=0.72), _c("c", face_consistency=0.71)]
    def compare(x, y):
        # c 永远赢；其余看 face
        if x["candidate"] == "c":
            return "a"
        if y["candidate"] == "c":
            return "b"
        return "a" if x["face_consistency"] >= y["face_consistency"] else "b"
    r = cs.select_best(cands, vlm_compare=compare)
    assert r["method"] == "vlm_ranker" and r["picked"]["candidate"] == "c"


def test_vlm_tie_falls_back_to_deterministic():
    cands = [_c("a", face_consistency=0.6, composition=0.1), _c("b", face_consistency=0.6, composition=0.9)]
    r = cs.select_best(cands, vlm_compare=lambda x, y: "tie")
    assert r["picked"]["candidate"] == "b"          # 平局→确定性分高者（b 构图分高）


def test_empty_candidates_reroll():
    r = cs.select_best([])
    assert r["picked"] is None and r["reroll_needed"]


def test_champion_is_n_minus_1_comparisons():
    calls = []
    cands = [_c(n, face_consistency=0.6) for n in "abcd"]
    def compare(x, y):
        calls.append((x["candidate"], y["candidate"]))
        return "a"
    cs.select_best(cands, vlm_compare=compare)
    assert len(calls) == 3                           # 单淘汰 = N-1 次


# ── Genflow 式纠偏处方 ─────────────────────────────────────────────────────────

def test_corrective_none_when_all_pass():
    cands = [_c("a", face_consistency=0.8), _c("b", face_consistency=0.7)]
    assert cs.corrective_prescription(cands, identity_floor=0.45) is None


def test_corrective_face_drift_from_low_cosine():
    # 全部低于地板 → 失败分布以崩脸为主 → 处方含换脸 negatives + 提脸锚/强制 image2image
    cands = [_c("a", face_consistency=0.30), _c("b", face_consistency=0.28)]
    corr = cs.corrective_prescription(cands, identity_floor=0.45)
    assert corr and corr["dominant"][0] == "face_drift"
    assert any("换脸" in n for n in corr["negatives"])
    assert corr["raise_face_anchor"] and corr["force_image2image"]


def test_corrective_parses_reason_text_codes():
    # 硬伤原因文本/码可解析出对应失败模式（接缝断 + 多指）
    cands = [_c("a", qc_hard_fail=True, qc_fail_reason="接缝断·姿态跳"),
             _c("b", qc_hard_fail=True, fail_codes=["hands", "seam"])]
    corr = cs.corrective_prescription(cands)
    assert "seam_break" in corr["failure_counts"]
    assert "hands" in corr["failure_counts"]


def test_corrective_unparsed_hardfail_defaults_face_drift():
    cands = [_c("a", qc_hard_fail=True), _c("b", qc_hard_fail=True)]
    corr = cs.corrective_prescription(cands)
    assert corr["failure_counts"].get("face_drift") == 2


def test_select_best_attaches_corrective_only_on_reroll():
    ok = cs.select_best([_c("a", face_consistency=0.8)])
    assert ok["corrective"] is None                  # 选出即可 → 无处方
    bad = cs.select_best([_c("a", qc_hard_fail=True)])
    assert bad["reroll_needed"] and bad["corrective"]  # reroll → 带处方


# ── 可用率账本 ────────────────────────────────────────────────────────────────

def test_shot_and_aggregate_yield():
    rows = [
        {"candidate_count": 4, "survivors": 1, "picked": {"candidate": "x"}, "reroll_needed": False},
        {"candidate_count": 4, "survivors": 0, "picked": None, "reroll_needed": True},
    ]
    sy0 = cs.shot_yield(rows[0])
    assert sy0["shot_yield"] == 0.25 and sy0["usable_pick"] == 1
    agg = cs.aggregate_yield(rows)
    assert agg["total_candidates"] == 8 and agg["total_survivors"] == 1
    assert agg["usable_yield"] == 0.125 and agg["resolved_clips"] == 1 and agg["reroll_clips"] == 1


def test_rolling_yield_from_events():
    events = [
        {"candidate_count": 4, "survivors": 1, "reroll_needed": False},
        {"candidate_count": 4, "survivors": 0, "reroll_needed": True},
    ]
    roll = cs.rolling_yield_from_events(events)
    assert roll["rounds"] == 2 and roll["usable_yield"] == 0.125
    assert roll["reroll_rounds"] == 1 and roll["reroll_rate"] == 0.5


def test_append_yield_ledger_rounds_and_summary(tmp_path):
    root = str(tmp_path)
    rows1 = [{"clip": "镜头1", "candidate_count": 4, "survivors": 0, "picked": None,
              "reroll_needed": True, "corrective": {"dominant": ["face_drift"]}}]
    p = cs.append_yield_ledger(root, "第1集", rows1, now="2026-06-27T00:00:00+00:00")
    assert p and os.path.isfile(p)
    # 第二轮（纠偏后回升）：同镜 round 应 +1，滚动可用率合并两轮
    rows2 = [{"clip": "镜头1", "candidate_count": 4, "survivors": 3,
              "picked": {"candidate": "x"}, "reroll_needed": False, "corrective": None}]
    cs.append_yield_ledger(root, "第1集", rows2, now="2026-06-27T00:01:00+00:00")
    events = cs._read_yield_events(p)
    assert [e["round"] for e in events] == [1, 2]
    summ = json.loads((tmp_path / "生产数据" / "yield_summary.json").read_text(encoding="utf-8"))
    assert summ["rounds"] == 2 and summ["total_survivors"] == 3 and summ["usable_yield"] == 0.375


# ── keyshot 候选落档目标 ──────────────────────────────────────────────────────

def test_apply_pick_uses_source_target_from_sidecar(tmp_path):
    cdir = tmp_path / "出图" / "第1集" / "候选" / "EP01_CLIP01"
    cdir.mkdir(parents=True)
    png = cdir / "candidate_01.png"
    png.write_bytes(b"candidate-image")
    (cdir / "candidate_01.json").write_text(json.dumps({
        "source_target": "出图/第1集/图片/Clip01_first.png",
        "source_prompt_shot": "Clip01 first",
    }), encoding="utf-8")

    cand = cs.gather_candidate(str(png), str(tmp_path))
    assert cand["source_target"] == "出图/第1集/图片/Clip01_first.png"
    assert cand["source_prompt_shot"] == "Clip01 first"

    dst = cs.apply_pick(str(tmp_path), "第1集", "EP01_CLIP01", cand)
    assert dst == os.path.join("出图", "第1集", "图片", "Clip01_first.png")
    assert (tmp_path / dst).read_bytes() == b"candidate-image"


def test_apply_pick_falls_back_to_clip_png_without_target(tmp_path):
    cdir = tmp_path / "出图" / "第1集" / "候选" / "EP01_CLIP01"
    cdir.mkdir(parents=True)
    png = cdir / "candidate_01.png"
    png.write_bytes(b"candidate-image")

    dst = cs.apply_pick(str(tmp_path), "第1集", "EP01_CLIP01", {"path": str(png)})
    assert dst == os.path.join("出图", "第1集", "图片", "EP01_CLIP01.png")
    assert (tmp_path / dst).read_bytes() == b"candidate-image"


def test_apply_pick_rejects_unsafe_source_target(tmp_path):
    cdir = tmp_path / "出图" / "第1集" / "候选" / "EP01_CLIP01"
    cdir.mkdir(parents=True)
    png = cdir / "candidate_01.png"
    png.write_bytes(b"candidate-image")

    dst = cs.apply_pick(str(tmp_path), "第1集", "EP01_CLIP01", {
        "path": str(png),
        "source_target": "../outside.png",
    })
    assert dst == os.path.join("出图", "第1集", "图片", "EP01_CLIP01.png")
    assert not (tmp_path.parent / "outside.png").exists()


def test_apply_interlock_is_nonwaivable(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(cs, "_apply_interlock_targets", lambda *args, **kwargs: [object()])
    monkeypatch.setattr(
        cs.cir,
        "enforce_shared_first_interlock",
        lambda root, ep, targets=None: seen.append((root, ep, targets)) or False,
    )
    assert cs.enforce_apply_shared_first(str(tmp_path), "第1集", [{"clip": "EP01_CLIP01"}]) is False
    assert seen and seen[0][1] == "第1集" and len(seen[0][2]) == 1


def test_main_apply_blocked_does_not_copy_candidate(monkeypatch, tmp_path):
    report = {
        "kind": cs.KIND,
        "version": cs.VERSION,
        "episode": "第1集",
        "rows": [{
            "clip": "EP01_CLIP01",
            "picked": {"path": "/tmp/candidate.png", "candidate": "candidate_01"},
            "reroll_needed": False,
        }],
    }
    copied = []
    monkeypatch.setattr(cs, "build_report", lambda *args, **kwargs: report)
    monkeypatch.setattr(cs, "enforce_apply_shared_first", lambda *args, **kwargs: False)
    monkeypatch.setattr(cs, "apply_pick", lambda *args, **kwargs: copied.append(args) or "unexpected.png")

    rc = cs.main([str(tmp_path), "第1集", "--apply", "--no-ledger", "--json"])

    assert rc == 1
    assert copied == []
    saved = json.loads(
        (tmp_path / "生产数据" / "candidate_selection_第1集.json").read_text(encoding="utf-8")
    )
    assert saved["apply_blocked"] is True
    assert saved["applied"] == []


def test_apply_pick_records_promotion_event_from_candidate_event(tmp_path):
    cdir = tmp_path / "出图" / "第1集" / "候选" / "EP01_CLIP01"
    cdir.mkdir(parents=True)
    png = cdir / "candidate_01.png"
    png.write_bytes(b"candidate-image")
    prod = tmp_path / "生产数据"
    prod.mkdir()
    source_event = {
        "kind": "n2d_production_event",
        "episode": "第1集",
        "stage": "image",
        "event": "generation",
        "generation": {
            "asset": "出图/第1集/候选/EP01_CLIP01/candidate_01.png",
            "provider": "Codex",
            "status": "pass",
        },
        "meta": {
            "provider": "Codex",
            "model": "GPT Image 2",
            "channel": "Codex CLI",
            "route_hash": "route",
            "capability_evidence_id": "cap",
            "recipe_hash": "source-recipe",
            "prompt_sha256": "prompt",
            "reference_bundle_sha256": "refs",
            "backend_version": "codex",
            "quality_tier": "project_default",
            "actual_image_inputs": "出图/共享/图片/ref.png",
            "seed_effective": "false",
            "seed_support": "unsupported_no_seed_api",
        },
        "ts": "2026-07-05T00:00:00+00:00",
        "version": 1,
    }
    (prod / "production_events.jsonl").write_text(json.dumps(source_event, ensure_ascii=False) + "\n", encoding="utf-8")

    dst = cs.apply_pick(str(tmp_path), "第1集", "EP01_CLIP01", {
        "path": str(png),
        "rel": "出图/第1集/候选/EP01_CLIP01/candidate_01.png",
        "source_target": "出图/第1集/图片/Clip01_first.png",
    })

    assert dst == os.path.join("出图", "第1集", "图片", "Clip01_first.png")
    events = [
        json.loads(line)
        for line in (prod / "production_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    promoted = events[-1]
    assert promoted["generation"]["asset"] == "出图/第1集/图片/Clip01_first.png"
    assert promoted["generation"]["status"] == "pass"
    assert promoted["meta"]["promoted_from"] == "出图/第1集/候选/EP01_CLIP01/candidate_01.png"
    assert promoted["meta"]["promotion_method"] == "candidate_select_apply"
    assert promoted["meta"]["recipe_hash"] != "source-recipe"
    assert promoted["meta"]["actual_image_inputs"] == "出图/共享/图片/ref.png"
