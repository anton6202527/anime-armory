from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("queue.py")
spec = importlib.util.spec_from_file_location("n2d_batch_queue", SCRIPT)
queue = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(queue)


def write_progress(root: Path) -> None:
    (root / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
                "| 第2集 | 820 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 1/3 | ⬜ | ⬜ | ⬜ |",
                "| 第3集 | 830 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | 1/2 | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )


def test_route_plan_and_budget_cap(tmp_path: Path) -> None:
    write_progress(tmp_path)
    estimates = queue.load_cost_estimates(str(tmp_path))
    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=None,
        stage_filters=None,
        cost_estimates=estimates,
        max_retries=2,
    )
    budget = queue.apply_budget(tasks, 4.0, "work_units")
    planned = queue.make_queue(str(tmp_path), tasks, max_concurrency=2, max_retries=2, budget=budget)

    assert [task["stage_key"] for task in planned["tasks"]] == ["voice", "image", "video"]
    assert [task["status"] for task in planned["tasks"]] == ["queued", "queued", "blocked_budget"]
    assert planned["budget"]["accepted_total"] == 4.0
    assert planned["batches"] == [[planned["tasks"][0]["id"], planned["tasks"][1]["id"]]]


def test_stage_filter_and_episode_selector(tmp_path: Path) -> None:
    write_progress(tmp_path)
    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("2-3"),
        stage_filters={"video"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )

    assert len(tasks) == 1
    assert tasks[0]["episode"] == "第3集"
    assert tasks[0]["owner"] == "n2d-video"


def test_episode_selector_accepts_chinese_and_fullwidth_numbers(tmp_path: Path) -> None:
    assert queue.parse_episode_selector("一-三") == {"第1集", "第2集", "第3集"}
    assert queue.parse_episode_selector("第２集,第三集") == {"第2集", "第3集"}
    assert queue.episode_num("第三集") == 3
    assert queue.task_id("第三集", "image", "progress").startswith("003-")


def test_route_filter_matches_chinese_episode_row(tmp_path: Path) -> None:
    write_progress(tmp_path)
    text = (tmp_path / "_进度.md").read_text(encoding="utf-8").replace("第3集", "第三集")
    (tmp_path / "_进度.md").write_text(text, encoding="utf-8")

    tasks = queue.route_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("3"),
        stage_filters={"video"},
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
    )

    assert len(tasks) == 1
    assert tasks[0]["episode"] == "第三集"


def test_targeted_rerun_and_claim_retry(tmp_path: Path) -> None:
    write_progress(tmp_path)
    tasks = queue.rerun_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("2") or set(),
        rerun_from="image",
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
        rerun_scope="只重跑 Clip_03 首帧",
        affected_artifacts=["出图/第2集/图片/Clip_03.png"],
        affected_shots=["Clip_03"],
    )
    budget = queue.apply_budget(tasks, None, None)
    ledger = queue.make_queue(str(tmp_path), tasks, max_concurrency=1, max_retries=1, budget=budget)
    queue.save_queue(str(tmp_path), ledger)

    loaded = queue.load_queue(str(tmp_path))
    claimed = queue.claim_tasks(loaded, limit=1)
    assert len(claimed) == 1
    assert claimed[0]["status"] == "running"
    assert claimed[0]["attempts"] == 1

    failed = queue.mark_task(loaded, claimed[0]["id"], "fail", "脸漂移")
    assert failed["status"] == "retry_queued"

    claimed_again = queue.claim_tasks(loaded, limit=1)
    assert claimed_again[0]["attempts"] == 2
    failed_again = queue.mark_task(loaded, claimed[0]["id"], "fail", "仍脸漂移")
    assert failed_again["status"] == "failed"
    assert failed_again["affected_shots"] == ["Clip_03"]


def _saved_queue(tmp_path: Path, max_concurrency: int = 2):
    write_progress(tmp_path)
    tasks = queue.route_tasks(str(tmp_path), episodes=None, stage_filters=None,
                              cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=2)
    ledger = queue.make_queue(str(tmp_path), tasks, max_concurrency=max_concurrency, max_retries=2,
                              budget=queue.apply_budget(tasks, None, None))
    queue.save_queue(str(tmp_path), ledger)
    return ledger


def test_claim_sets_worker_and_lease_then_mark_clears(tmp_path: Path) -> None:
    _saved_queue(tmp_path)
    claimed = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=60)
    assert claimed and claimed[0]["worker"] == "w1"
    assert claimed[0]["lease_until"] > queue.now_ts()
    marked = queue.mark(str(tmp_path), claimed[0]["id"], "pass")
    assert marked["status"] == "done"
    assert "lease_until" not in marked and "worker" not in marked


def test_concurrent_claims_do_not_double_claim(tmp_path: Path) -> None:
    # 同一锁内重读：两次连续 claim 各拿不同任务，不重复（capacity=2）。
    _saved_queue(tmp_path, max_concurrency=2)
    a = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=60)
    b = queue.claim(str(tmp_path), limit=1, worker="w2", lease_seconds=60)
    ids_a = {t["id"] for t in a}
    ids_b = {t["id"] for t in b}
    assert ids_a and ids_b
    assert ids_a.isdisjoint(ids_b)  # 绝不双认领
    # 并发上限到顶：第三次拿不到
    assert queue.claim(str(tmp_path), limit=1, worker="w3", lease_seconds=60) == []


def test_reclaim_expired_lease_returns_task_to_queue(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="dead", lease_seconds=60)
    tid = claimed[0]["id"]
    # 手动把租约设到过去，模拟 worker 崩溃
    loaded = queue.load_queue(str(tmp_path))
    for t in loaded["tasks"]:
        if t["id"] == tid:
            t["lease_until"] = queue.now_ts() - 1
    queue.save_queue(str(tmp_path), loaded)
    reclaimed = queue.reclaim(str(tmp_path))
    assert [t["id"] for t in reclaimed] == [tid]
    after = queue.load_queue(str(tmp_path))
    task = next(t for t in after["tasks"] if t["id"] == tid)
    assert task["status"] == "retry_queued"   # attempts=1 <= max_retries=2
    assert "lease_until" not in task
    # 回收后可被新 worker 再认领
    again = queue.claim(str(tmp_path), limit=1, worker="alive", lease_seconds=60)
    assert again[0]["id"] == tid and again[0]["worker"] == "alive"


def test_force_worker_reclaim_for_resume(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=9999)  # 租约没过期
    tid = claimed[0]["id"]
    # 不强制：租约未过期 → 不回收
    assert queue.reclaim(str(tmp_path), worker="w1", force_worker=False) == []
    # 强制本 worker（--resume 语义）→ 回收自己的残留 running
    reclaimed = queue.reclaim(str(tmp_path), worker="w1", force_worker=True)
    assert [t["id"] for t in reclaimed] == [tid]


def test_renew_extends_lease(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    claimed = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=10)
    tid = claimed[0]["id"]
    before = queue.load_queue(str(tmp_path))
    old = next(t for t in before["tasks"] if t["id"] == tid)["lease_until"]
    assert queue.renew(str(tmp_path), [tid], 600, "w1") == 1
    after = queue.load_queue(str(tmp_path))
    assert next(t for t in after["tasks"] if t["id"] == tid)["lease_until"] > old


def test_stale_worker_mark_is_rejected_after_reclaim(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    old_claim = queue.claim(str(tmp_path), limit=1, worker="dead", lease_seconds=60)
    tid = old_claim[0]["id"]
    loaded = queue.load_queue(str(tmp_path))
    for t in loaded["tasks"]:
        if t["id"] == tid:
            t["lease_until"] = queue.now_ts() - 1
    queue.save_queue(str(tmp_path), loaded)
    queue.reclaim(str(tmp_path))
    new_claim = queue.claim(str(tmp_path), limit=1, worker="alive", lease_seconds=60)
    assert new_claim[0]["id"] == tid

    try:
        queue.mark(str(tmp_path), tid, "pass", expected_worker="dead", expected_attempt=old_claim[0]["attempts"])
        assert False, "stale worker mark should have been rejected"
    except ValueError:
        pass
    after = queue.load_queue(str(tmp_path))
    task = next(t for t in after["tasks"] if t["id"] == tid)
    assert task["status"] == "running"
    assert task["worker"] == "alive"


def test_save_queue_is_atomic_no_leftover_tmp(tmp_path: Path) -> None:
    _saved_queue(tmp_path)
    pdir = tmp_path / "生产数据"
    leftovers = [p for p in pdir.iterdir() if ".tmp." in p.name]
    assert leftovers == []
    assert (pdir / "batch_queue.json").is_file()


def test_plan_merge_preserves_running_task(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    running = queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=600)
    assert running

    # A later plan for a narrower stage must not overwrite the running ledger.
    tasks = queue.rerun_tasks(
        str(tmp_path),
        episodes=queue.parse_episode_selector("2") or set(),
        rerun_from="image",
        cost_estimates=queue.load_cost_estimates(str(tmp_path)),
        max_retries=1,
        rerun_scope="新返工",
        affected_artifacts=[],
        affected_shots=[],
    )
    planned = queue.make_queue(
        str(tmp_path),
        tasks,
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget(tasks, None, None),
    )

    merged = queue.write_planned_queue(str(tmp_path), planned)

    assert any(t["id"] == running[0]["id"] and t["status"] == "running" for t in merged["tasks"])
    assert any(t["reason"] == "rerun" for t in merged["tasks"])


def test_plan_merge_reapplies_budget_to_full_ledger(tmp_path: Path) -> None:
    estimates = queue.load_cost_estimates(str(tmp_path))
    image = queue.task_from_spec(
        str(tmp_path),
        "第1集",
        queue.find_stage("image"),
        reason="progress",
        priority=1,
        cost_estimates=estimates,
        max_retries=1,
    )
    existing = queue.make_queue(
        str(tmp_path),
        [image],
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget([image], 3.0, "work_units"),
    )
    queue.save_queue(str(tmp_path), existing)

    voice = queue.task_from_spec(
        str(tmp_path),
        "第2集",
        queue.find_stage("voice"),
        reason="progress",
        priority=2,
        cost_estimates=estimates,
        max_retries=1,
    )
    planned = queue.make_queue(
        str(tmp_path),
        [voice],
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget([voice], 3.0, "work_units"),
    )

    merged = queue.write_planned_queue(str(tmp_path), planned)

    by_stage = {(task["episode"], task["stage_key"]): task for task in merged["tasks"]}
    assert by_stage[("第1集", "image")]["status"] == "queued"
    assert by_stage[("第2集", "voice")]["status"] == "blocked_budget"
    assert merged["budget"]["scope"] == "ledger"
    assert merged["budget"]["accepted_total"] == 3.0
    assert merged["budget"]["estimated_total"] == 4.0
    assert merged["budget"]["blocked_tasks"] == 1


def _impact_plan(root: Path) -> dict:
    return {
        "kind": "n2d_asset_rerun_plan",
        "version": 1,
        "root": str(root),
        "assets": ["沈念"],
        "rerun_tasks": [
            {"episode": "第1集", "rerun_from": "image", "scope": "定妆沈念变更连锁·重出受影响镜头",
             "affected_artifacts": ["出图/第1集/图片/Clip_01.png"], "affected_shots": ["Clip_01"]},
            {"episode": "第1集", "rerun_from": "video", "scope": "定妆沈念变更连锁·重生已出视频 clip",
             "affected_artifacts": ["出视频/第1集/视频/Clip_01.mp4"], "affected_shots": ["Clip_01"]},
            {"episode": "第2集", "rerun_from": "image", "scope": "定妆沈念变更连锁·重出受影响镜头",
             "affected_artifacts": ["出图/第2集/图片/Clip_05.png"], "affected_shots": ["Clip_05"]},
        ],
    }


def test_tasks_from_asset_impact_builds_rerun_tasks(tmp_path: Path) -> None:
    """asset_impact --output-batch-tasks 的 JSON → 队列任务（字段透传、kind 校验、集过滤）。"""
    plan = _impact_plan(tmp_path)
    tasks = queue.tasks_from_asset_impact(
        str(tmp_path), plan,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=1,
    )
    assert [(t["episode"], t["stage_key"]) for t in tasks] == [
        ("第1集", "image"), ("第1集", "video"), ("第2集", "image")]
    assert all(t["reason"] == "rerun" for t in tasks)
    assert tasks[0]["affected_shots"] == ["Clip_01"]
    assert tasks[0]["rerun_scope"].startswith("定妆沈念变更连锁")
    # 集过滤
    only2 = queue.tasks_from_asset_impact(
        str(tmp_path), plan,
        cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=1,
        episodes=queue.parse_episode_selector("2"),
    )
    assert [(t["episode"], t["stage_key"]) for t in only2] == [("第2集", "image")]
    # kind 校验
    try:
        queue.tasks_from_asset_impact(
            str(tmp_path), {"kind": "x"},
            cost_estimates=queue.load_cost_estimates(str(tmp_path)), max_retries=1)
        assert False, "kind mismatch should raise"
    except ValueError:
        pass


def test_plan_from_asset_impact_cli_writes_queue(tmp_path: Path) -> None:
    import json
    write_progress(tmp_path)
    plan_path = tmp_path / "impact_plan.json"
    plan_path.write_text(json.dumps(_impact_plan(tmp_path), ensure_ascii=False), encoding="utf-8")
    rc = queue.main(["plan", str(tmp_path), "--from-asset-impact", str(plan_path)])
    assert rc == 0
    loaded = queue.load_queue(str(tmp_path))
    by_id = {(t["episode"], t["stage_key"]): t for t in loaded["tasks"]}
    assert ("第1集", "image") in by_id and ("第1集", "video") in by_id and ("第2集", "image") in by_id
    task = by_id[("第1集", "video")]
    assert task["reason"] == "rerun"
    assert task["affected_artifacts"] == ["出视频/第1集/视频/Clip_01.mp4"]


def test_replace_refuses_running_without_force(tmp_path: Path) -> None:
    _saved_queue(tmp_path, max_concurrency=1)
    queue.claim(str(tmp_path), limit=1, worker="w1", lease_seconds=600)
    planned = queue.make_queue(
        str(tmp_path),
        [],
        max_concurrency=1,
        max_retries=1,
        budget=queue.apply_budget([], None, None),
    )

    try:
        queue.write_planned_queue(str(tmp_path), planned, replace=True)
        assert False, "replace should refuse to clobber running work"
    except RuntimeError:
        pass

    replaced = queue.write_planned_queue(str(tmp_path), planned, replace=True, force=True)
    assert replaced["tasks"] == []


# ── T4: 回流闭环后半环（指纹 + resolved 回写 + 复检）──────────────────────────
import queue as q
from n2d_contract import finding_fingerprint


def _findings_report(ep="第1集"):
    return {
        "kind": q.CONSISTENCY_FINDINGS_KIND, "episode": ep,
        "findings": [
            {"severity": "block", "dimension": "character_consistency",
             "return_to_stage": "image", "affected_shots": ["Clip_03"], "msg": "崩脸"},
        ],
    }


def test_consistency_tasks_carry_matching_fingerprint(tmp_path):
    rep = _findings_report()
    tasks = q.tasks_from_consistency_findings(str(tmp_path), rep, cost_estimates={}, max_retries=1)
    assert len(tasks) == 1
    fp = finding_fingerprint("第1集", "image", "character_consistency", "Clip_03")
    assert tasks[0]["finding_fingerprints"] == [fp]
    # task 端指纹 == audit 端重算的现存指纹（可对账）
    assert fp in q.report_active_fingerprints(rep)


def test_merge_reopens_recurring_done_task_no_stack(tmp_path):
    fp = finding_fingerprint("第1集", "image", "character_consistency")
    existing = {"tasks": [{"id": "001-image-rerun", "status": "done", "attempts": 1,
                           "finding_fingerprints": [fp], "history": []}]}
    planned = {"tasks": [{"id": "001-image-rerun", "status": "queued", "attempts": 0,
                          "finding_fingerprints": [fp], "rerun_scope": "重出崩脸", "history": []}]}
    merged = q.merge_queues(existing, planned)
    assert len(merged["tasks"]) == 1                      # 不堆叠
    t = merged["tasks"][0]
    assert t["status"] == "queued" and t["resolved"] is False
    assert any(h["action"] == "plan:reopen_recurring" for h in t["history"])


def test_merge_skips_in_flight_duplicate(tmp_path):
    fp = finding_fingerprint("第1集", "image", "character_consistency")
    existing = {"tasks": [{"id": "001-image-rerun", "status": "running", "attempts": 1,
                           "finding_fingerprints": [fp], "history": []}]}
    planned = {"tasks": [{"id": "001-image-rerun-x", "status": "queued", "attempts": 0,
                          "finding_fingerprints": [fp], "history": []}]}
    merged = q.merge_queues(existing, planned)
    assert len(merged["tasks"]) == 1                      # 在途同问题不重复入队
    assert merged["tasks"][0]["status"] == "running"


def test_reconcile_resolved_marks_and_reopens():
    fp_gone = finding_fingerprint("第1集", "image", "character_consistency")
    fp_still = finding_fingerprint("第2集", "image", "scene_consistency")
    queue = {"tasks": [
        {"id": "a", "status": "done", "finding_fingerprints": [fp_gone], "history": []},
        {"id": "b", "status": "done", "finding_fingerprints": [fp_still], "history": []},
        {"id": "c", "status": "queued", "finding_fingerprints": [fp_still], "history": []},  # 非 done 不碰
    ]}
    q.reconcile_resolved(queue, active_fingerprints={fp_still})
    a, b, c = queue["tasks"]
    assert a["resolved"] is True and a["status"] == "done"          # 问题消失 → resolved
    assert b["status"] == "queued" and b["resolved"] is False        # 仍在 → reopen
    assert c["status"] == "queued"                                   # queued 不动
    assert queue["recheck"] == {"resolved": 1, "reopened": 1, "reopened_coarse": 0, "at": queue["recheck"]["at"]}


def test_fingerprint_stable_across_shot_locator_granularity():
    """#2 根因修复：同一镜头换写法/帧位/产物路径 → 同一精确指纹，复检不再误判 resolved。"""
    base = finding_fingerprint("第1集", "image", "character_consistency", "Clip_03")
    for variant in ("Clip 3", "clip_03", "Clip_03_首帧", "Clip_03_尾帧", "镜头3",
                    "出图/第1集/图片/Clip_03.png"):
        assert finding_fingerprint("第1集", "image", "character_consistency", variant) == base
    # 不同镜头仍区分
    assert finding_fingerprint("第1集", "image", "character_consistency", "Clip_04") != base


def test_recheck_granularity_drift_no_false_resolved():
    """返工前 finding 定位 Clip_03、返工后审查写成 Clip_03_首帧：精确指纹归一后仍判 reopen。"""
    task_fp = finding_fingerprint("第2集", "image", "character_consistency", "Clip_03")
    active = {finding_fingerprint("第2集", "image", "character_consistency", "Clip_03_首帧")}
    queue = {"tasks": [{"id": "a", "status": "done", "finding_fingerprints": [task_fp], "history": []}]}
    q.reconcile_resolved(queue, active)
    assert queue["tasks"][0]["status"] == "queued"  # 没被误判 resolved


def test_recheck_coarse_fallback_reopens_when_bucket_still_dirty():
    """#2 安全网：精确指纹对不上，但 (集×阶段×维度) 桶仍有问题 → --coarse 下 reopen，不漏放。"""
    task_fp = finding_fingerprint("第3集", "image", "outfit_consistency", "无镜头号自由文本A")
    coarse_fp = finding_fingerprint("第3集", "image", "outfit_consistency")
    # 桶里现在是另一条无法归一到同精确指纹的描述，但同 (集,阶段,维度)
    active_fine = {finding_fingerprint("第3集", "image", "outfit_consistency", "另一段自由文本B")}
    active_coarse = {coarse_fp}
    queue = {"tasks": [{"id": "a", "status": "done",
                        "finding_fingerprints": [task_fp],
                        "coarse_fingerprints": [coarse_fp], "history": []}]}
    # 不开 coarse：精确对不上 → 误判 resolved（说明回退的必要性）
    q.reconcile_resolved({"tasks": [dict(queue["tasks"][0])]}, active_fine)
    # 开 coarse：桶仍脏 → reopen
    q.reconcile_resolved(queue, active_fine, coarse_active=active_coarse)
    assert queue["tasks"][0]["status"] == "queued"
    assert queue["recheck"]["reopened_coarse"] == 1
    assert queue["recheck"]["reopened"] == 0


def test_recheck_coarse_fallback_resolves_when_bucket_clean():
    """精确指纹消失且桶也干净 → 即便开 coarse 也判 resolved，能收敛。"""
    task_fp = finding_fingerprint("第3集", "image", "outfit_consistency", "Clip_07")
    coarse_fp = finding_fingerprint("第3集", "image", "outfit_consistency")
    queue = {"tasks": [{"id": "a", "status": "done",
                        "finding_fingerprints": [task_fp],
                        "coarse_fingerprints": [coarse_fp], "history": []}]}
    q.reconcile_resolved(queue, set(), coarse_active=set())
    assert queue["tasks"][0]["resolved"] is True
    assert queue["recheck"]["reopened_coarse"] == 0


def test_consistency_task_carries_coarse_fingerprints(tmp_path):
    rep = {"kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
           "auto_return_tasks": [{
               "return_to_stage": "image",
               "dimensions": ["character_consistency"],
               "affected_shots": ["Clip_03"],
           }]}
    tasks = q.tasks_from_consistency_findings(str(tmp_path), rep, cost_estimates={}, max_retries=1)
    assert tasks[0]["coarse_fingerprints"] == [
        finding_fingerprint("第1集", "image", "character_consistency")
    ]


def test_collect_active_fingerprints_from_disk(tmp_path):
    pdir = tmp_path / "生产数据"
    pdir.mkdir()
    (pdir / "consistency_findings_第1集.json").write_text(
        json.dumps(_findings_report()), encoding="utf-8")
    fps = q.collect_active_fingerprints(str(tmp_path))
    assert finding_fingerprint("第1集", "image", "character_consistency", "Clip_03") in fps


def test_consistency_fingerprints_are_scoped_per_affected_shot(tmp_path):
    rep = {"kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
           "auto_return_tasks": [{
               "return_to_stage": "image",
               "dimensions": ["character_consistency"],
               "affected_shots": ["Clip_03", "Clip_05"],
               "scope": "两镜崩脸",
           }]}
    tasks = q.tasks_from_consistency_findings(str(tmp_path), rep, cost_estimates={}, max_retries=1)
    assert sorted(tasks[0]["finding_fingerprints"]) == sorted([
        finding_fingerprint("第1集", "image", "character_consistency", "Clip_03"),
        finding_fingerprint("第1集", "image", "character_consistency", "Clip_05"),
    ])

    active = q.report_active_fingerprints({
        "kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
        "auto_return_tasks": [{
            "return_to_stage": "image",
            "dimensions": ["character_consistency"],
            "affected_shots": ["Clip_05"],
        }],
    })
    queue_obj = {"tasks": [{"id": "a", "status": "done",
                            "finding_fingerprints": tasks[0]["finding_fingerprints"], "history": []}]}
    q.reconcile_resolved(queue_obj, active)
    assert queue_obj["tasks"][0]["status"] == "queued"


# ── T11: 最小范围返工命令注入 --shots ────────────────────────────────────────
def test_task_command_injects_affected_shots():
    rep = {"kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
           "findings": [{"severity": "block", "dimension": "character_consistency",
                         "return_to_stage": "image", "affected_shots": ["Clip_03", "Clip_05"], "msg": "崩脸"}]}
    tasks = q.tasks_from_consistency_findings(str("/x"), rep, cost_estimates={}, max_retries=1)
    assert tasks and "--shots Clip_03,Clip_05" in tasks[0]["command"]


def test_task_command_no_shots_suffix_when_none():
    rep = {"kind": q.CONSISTENCY_FINDINGS_KIND, "episode": "第1集",
           "findings": [{"severity": "block", "dimension": "style_consistency",
                         "return_to_stage": "image", "msg": "风格漂"}]}
    tasks = q.tasks_from_consistency_findings(str("/x"), rep, cost_estimates={}, max_retries=1)
    assert tasks and "--shots" not in tasks[0]["command"]
