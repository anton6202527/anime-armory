#!/usr/bin/env python3
"""gates/consistency.py — 语义谱系/状态百科/多模态一致性(3 locked)+一致性审计闸簇族

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座，避免与 gate.py 循环导入；
gate.py `from gates.consistency import *` 回灌，run()/按名自省助手照常解析；成员经校验 call-graph-closed。
"""
from gate_core import *  # noqa: F401,F403
from gate_core import (
    _add_continuity_rows,
    _autorun_scene_verifier,
    _check_fidelity_gate_active,
    _consistency_finding_hash,
    _consistency_signoff_path,
    _loads_json_from_noisy_stdout,
    _native_block_intentional_signoff,
    _strict_advisory_should_block,
)

def check_semantic_lineage(root: str, ep: str) -> None:
    res = semc.analyze(root, ep)
    _add_continuity_rows(
        "语义谱系(P0)",
        [r for r in res.get("findings", []) if isinstance(r, dict)],
        ep,
        default_stage="script_stage2",
        default_scope="修 storyboard→出图/出视频 prompt 的语义继承缺口；必要时重跑 n2d-script 阶段2。",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt", f"出视频/{ep}/prompt"),
    )

def check_state_continuity(root: str, ep: str) -> None:
    res = statec.analyze(root, ep)
    _add_continuity_rows(
        "状态百科(P1)",
        [r for r in res.get("alerts", []) if isinstance(r, dict)],
        ep,
        default_stage="image",
        default_scope="修 visual_state_ledger / 出图分镜 prompt 的角色/道具状态锁；道具 lifecycle 未结构化的升级为 {states,transitions}；必要时回 storyboard / asset_registry 修状态演进。",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/visual_state_ledger.json", "出图/共享/asset_registry.json"),
    )

def check_multimodal_continuity(root: str, ep: str) -> None:
    res = mmc.analyze(root, ep)
    _add_continuity_rows(
        "多模态(P2)",
        [r for r in res.get("shots", []) if isinstance(r, dict)],
        ep,
        default_stage="image",
        default_scope="按离群道具/场景/法宝参考组只重出受影响镜头；必要时补资产定妆 taxonomy。",
        default_artifacts=(f"出图/{ep}/prompt/01_分镜出图.md", f"出图/{ep}/图片"),
    )

def check_consistency_audit_gate(root: str, ep: str, stage: str = "review") -> None:
    """Final consistency suite gate.

    The detector bundle is useful only if it is on a mandatory path.  Run the
    full audit before image(出图后)/compose/review and mirror active findings into
    gate output; the complete report remains in 生产数据/consistency_findings_<ep>.json.

    `stage` gates how 降级精度 is treated: compose/review are deliverable boundaries,
    so non-full precision (insightface 缺失→脸/像素一致性其实没验证) is a BLOCK there
    unless explicitly waived via `N2D_ALLOW_DEGRADED_QC=1`. At image/video artifact gates,
    demo profile only WARNs, while production profile BLOCKs degraded precision at the
    closest artifact boundary.
    """
    script = os.path.join(SCRIPT_DIR, "consistency_audit.py")
    loc = os.path.join(root, "生产数据", f"consistency_findings_{ep}.json")
    # 铁律 B11（2026-06-27）：一致性总审一律按 production 严格度跑，demo 不降标准。
    # （子进程 --profile 只影响 consistency_audit.py 自己的退出码，本 gate 解析 JSON 不看退出码；
    #  by_dim 严重度不依赖 profile，升级判定由本文件 _strict_advisory_should_block 统一做。）
    try:
        proc = subprocess.run(
            [sys.executable, script, root, ep, "--json", "--profile", "production"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=1200,
        )
    except Exception as exc:
        add(BLOCK, "一致性总审", loc, f"consistency_audit.py 无法运行：{type(exc).__name__}: {exc}", return_to_stage="review")
        return
    try:
        res = _loads_json_from_noisy_stdout(proc.stdout or "{}")
    except Exception as exc:
        add(
            BLOCK,
            "一致性总审",
            loc,
            f"consistency_audit.py --json 输出不可解析：{type(exc).__name__}: {exc}；stderr={proc.stderr[:500]}",
            return_to_stage="review",
        )
        return
    if not isinstance(res, dict):
        add(BLOCK, "一致性总审", loc, "consistency_audit.py --json 未返回对象", return_to_stage="review")
        return

    summary = res.get("summary") if isinstance(res.get("summary"), dict) else {}
    precision = str(summary.get("precision_level") or "full")
    if precision != "full":
        # 铁律 B11（2026-06-27·C4 豁免堵死）：降级精度=脸/像素一致性其实没机检过。此前 demo image/video
        # 只 WARN 静默放行（"不强制装依赖"），现 demo 与 production 同标准——四个阶段都不给绿灯，缺 insightface
        # 不再是默认免单，唯一出口是显式留痕 N2D_ALLOW_DEGRADED_QC=1（把"缺依赖默认放行"改成"显式自负其责"）。
        allow_degraded = os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1"
        strict_stage = stage in {"compose", "review", "image", "video"}
        if strict_stage and not allow_degraded:
            boundary = (
                "交付边界" if stage in {"compose", "review"}
                else "出视频后闸门" if stage == "video"
                else "出图后闸门"
            )
            add(
                BLOCK,
                "一致性总审",
                loc,
                f"一致性审计精度为 {precision}（insightface 等不可用，脸/像素一致性未真正验证）；"
                f"{boundary}不放行——请在 full 环境复跑，或显式 N2D_ALLOW_DEGRADED_QC=1 放行并自负其责。",
                return_to_stage="review",
            )
        else:
            if allow_degraded and strict_stage:
                note_degraded_qc_waiver("一致性总审", ep, loc, f"审计精度 {precision}·像素一致性降级放行")
            note = "（已显式 N2D_ALLOW_DEGRADED_QC 放行）" if allow_degraded else ""
            add(
                WARN,
                "一致性总审",
                loc,
                f"一致性审计精度为 {precision}；机检通过不等于脸部/像素一致性已完整验证，正式定稿前应在 full 环境复跑。{note}",
                return_to_stage="review",
            )

    # 证据等级账本（#3）：advanced tier（torch/syncnet 进阶依赖缺位的跨帧主体一致/口型词级）此前完全
    # 不可见也不阻断；这里在交付边界把"本可验到 embedding/pixel 却只到结构级"的维度判 PENDING→BLOCK。
    eg_allow_waiver = os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1"
    eg_under = (summary.get("evidence_grade") or {}).get("under_proven") or [] if isinstance(summary.get("evidence_grade"), Mapping) else []
    if eg_allow_waiver and stage in {"compose", "review"} and eg_under:
        note_degraded_qc_waiver("证据等级", ep, loc, f"advanced tier 未达标降级放行：{('、').join(str(d) for d in eg_under)}")
    for eg_sev, eg_msg in evidence_grade_findings(summary, stage, eg_allow_waiver):
        add(eg_sev, "证据等级", loc, eg_msg, return_to_stage="review")

    block_count = 0
    mapped_warns = 0
    skipped_warns = 0
    intentional_downgrades = 0
    # Sort WARN findings by risk_score descending so high-priority warns are
    # never skipped in favour of low-priority ones under the 12-warn cap.
    raw_rows = res.get("findings", []) or []
    warn_rows = [
        r for r in raw_rows
        if isinstance(r, dict) and str(r.get("severity") or r.get("verdict") or "").lower() == WARN
    ]
    warn_rows.sort(key=lambda r: -(float(r.get("risk_score", 0.5) or 0.5)))
    non_warn_rows = [r for r in raw_rows if r not in warn_rows or not isinstance(r, dict)]
    sorted_rows = non_warn_rows + warn_rows
    for row in sorted_rows:
        if not isinstance(row, dict):
            continue
        sev = str(row.get("severity") or row.get("verdict") or "").lower()
        if sev not in {BLOCK, WARN}:
            continue
        # C1/C2: a native consistency BLOCK on an eligible continuity axis (昼夜/越轴/
        # 重打光/调色…) that the creator has signed off as an *intended* discontinuity
        # is downgraded to WARN here — so the intentional_discontinuity manifest finally
        # bites at the exit-code gate, not just in the report. Kept as a traceable WARN
        # (never silently dropped). `intentional_signed` also blocks strict-advisory from
        # re-escalating the same row back to BLOCK below.
        intentional_note = ""
        intentional_signed = False
        if sev == BLOCK:
            signed, signoff_src = _native_block_intentional_signoff(root, ep, row)
            if signed:
                sev = WARN
                intentional_signed = True
                intentional_downgrades += 1
                intentional_note = f"[有意不连续已签收·{signoff_src}] "
        strict_block, strict_reason = _strict_advisory_should_block(root, ep, stage, row, summary)
        if sev == WARN and strict_block and not intentional_signed:
            sev = BLOCK
        if sev == WARN:
            if mapped_warns >= 12:
                skipped_warns += 1  # 不静默丢——循环后出一条 rollup，避免"12 条已处理"的错觉
                continue
            mapped_warns += 1
        else:
            block_count += 1
        dim = str(row.get("dimension") or row.get("dim") or "一致性总审")
        msg = str(row.get("message") or row.get("msg") or row.get("reason") or "一致性审计发现问题")
        if intentional_note:
            msg = intentional_note + msg
        if strict_block:
            msg = (
                f"[production一致性升级:{strict_reason}] {msg}。如确认为可接受，写入 "
                f"{os.path.relpath(_consistency_signoff_path(root, ep), root)} 的 accepted 后复跑；"
                f"finding_hash={_consistency_finding_hash(row)}，签收需包含 accepted=true/reviewer/reason/expires_at，"
                "并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。"
            )
        artifacts = row.get("affected_artifacts") if isinstance(row.get("affected_artifacts"), list) else []
        shots = row.get("affected_shots") if isinstance(row.get("affected_shots"), list) else []
        # Pass through risk_score from audit row (consistency_audit.py sets per-dimension
        # risk_score on export rows; carried forward into gate finding for display tiering).
        rs = row.get("risk_score")
        try:
            rs = float(rs) if rs is not None else None
        except (TypeError, ValueError):
            rs = None
        add(
            sev,
            dim,
            str(artifacts[0] if artifacts else loc),
            msg,
            risk_score=rs,
            return_to_stage=row.get("return_to_stage") or ("image" if sev == BLOCK else "review"),
            rerun_scope=row.get("rerun_scope") or "按 consistency_findings 报告回源头修复对应一致性维度。",
            affected_shots=shots,
            affected_artifacts=artifacts or [os.path.relpath(loc, root)],
        )

    # Cross-detector correlation: when >=3 WARN_HI cluster on same clip across
    # >=3 different dimensions, auto-upgrade to BLOCK (likely backend mismatch).
    correlation_upgrades = correlate_findings(findings)
    for upgrade in correlation_upgrades:
        add(
            str(upgrade.get("sev", BLOCK)),
            str(upgrade.get("dim", "一致性总审")),
            str(upgrade.get("loc", loc)),
            str(upgrade.get("msg", "")),
            risk_score=float(upgrade.get("risk_score", 0.9)),
            return_to_stage=str(upgrade.get("return_to_stage", "image")),
            rerun_scope=str(upgrade.get("rerun_scope", "")),
            affected_shots=list(upgrade.get("affected_shots", [])),
            affected_artifacts=list(upgrade.get("affected_artifacts", [loc])),
        )

    # 逐镜仲裁/归并（report 层·INFO·不改 verdict）：把同一镜被多检测器同时报的 finding 按证据族去重，
    # 单点呈现"这一镜有问题"，并暴露原始条数 vs 归并族数（防读者把双计数当独立问题）。
    arbitration = consolidate_findings_by_shot(findings)
    multi_source = [
        a for a in arbitration
        if len(a.get("dims") or []) >= 2 and len(a.get("independent_evidence_families") or []) >= 2
    ]
    if multi_source:
        top = "；".join(
            f"{a['shot']}({len(a['dims'])}维/{a['merged_family_count']}族/{a['raw_finding_count']}条·最坏{a['verdict']})"
            for a in multi_source[:8]
        )
        add(
            INFO,
            "逐镜仲裁",
            loc,
            f"{len(multi_source)} 个镜被多检测器同时报，已按证据族归并（severity 以最坏维度为准，"
            f"勿按条数重复计=双计数）：{top}" + ("…" if len(multi_source) > 8 else ""),
            return_to_stage="review",
        )

    # Fidelity-gate liveness: ensure vlm_verify --write has been run for production
    # compose/review stages (following check_drift_report_freshness pattern).
    _check_fidelity_gate_active(root, ep, stage)

    # 现实覆盖闸：场景现实验证器（DINOv2/OWLv2）适用却休眠 → 交付边界阻断（治「跑了却没执行」）。
    check_consistency_reality_coverage(root, ep, stage)

    if skipped_warns:
        add(
            WARN,
            "一致性总审",
            loc,
            f"另有 {skipped_warns} 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 "
            f"生产数据/consistency_findings_{ep}.json，勿当作已全部处理。",
            return_to_stage="review",
        )

    # 非 0 退出码兜底：若 audit 报了 block(exit≠0) 但 gate 没surface任何 block，补一条以防漏判。
    # 例外：本轮把 native block 作为「已签收的有意不连续」降级成 WARN（intentional_downgrades>0）
    # 时，非 0 退出码已被这些降级解释，gate 也已把它们以 WARN 留痕——不再误补 generic block。
    if proc.returncode != 0 and not block_count and not intentional_downgrades:
        add(
            BLOCK,
            "一致性总审",
            loc,
            f"consistency_audit.py 退出码 {proc.returncode}，但未导出 block finding；stderr={proc.stderr[:500]}",
            return_to_stage="review",
        )

def check_consistency_ledger_gate(root: str, ep: str) -> None:
    """review 阶段消费跨集验收总账，防止验收仍停留在单镜观感。

    ledger 把角色/服装/场景/道具/声音/字幕/合规/生产操作收成一张账；counts.block/high
    是正式验收硬阻断。
    """
    loc = os.path.join(root, "生产数据", f"consistency_ledger_{ep}.json")
    try:
        import consistency_ledger as ledger_mod
        ledger = ledger_mod.run(root, ep)
    except Exception as exc:
        add(BLOCK, "验收总账", loc,
            f"consistency_ledger.py 无法生成：{type(exc).__name__}: {exc}；review 必须从跨集总账验收，不再只看单镜观感。",
            return_to_stage="review")
        return
    if not isinstance(ledger, dict):
        add(BLOCK, "验收总账", loc, "consistency_ledger.py 未返回对象；review fail-closed。", return_to_stage="review")
        return
    counts = ledger.get("counts") if isinstance(ledger.get("counts"), Mapping) else {}
    block = int(counts.get("block") or 0)
    high = int(counts.get("high") or 0)
    medium = int(counts.get("medium") or 0)
    if block or high:
        add(
            BLOCK,
            "验收总账",
            loc,
            f"一致性验收总账未清零：block={block} high={high} medium={medium}。"
            "review 不再按单镜看着像放行；请按 consistency_ledger 的交付域/根因回源头修复后复跑。",
            return_to_stage="review",
            affected_artifacts=[os.path.relpath(loc, root)],
        )
    elif medium:
        add(WARN, "验收总账", loc,
            f"一致性验收总账仍有 medium={medium}；可人工签收，但需逐项看角色/资产/镜头/声音跨集账本。",
            return_to_stage="review")
    else:
        add(INFO, "验收总账", loc, "一致性验收总账 block/high 已清零，角色/资产/镜头/声音等交付域已汇总。")

def check_consistency_reality_coverage(root: str, ep: str, stage: str) -> None:
    """一致性现实覆盖闸（治「跑了数据却没真执行一致性」的结构根因·SonarQube/MLOps fail-closed 范式）。

    场景现实验证器（DINOv2 嵌入 / OWLv2 在场+几何）此前缺后端就**静默降级 advisory**——真实出片机常没装
    重型后端，于是最强检测器全休眠却照样交付。本闸把它们补进交付边界的休眠阻断（脸/声纹/VLM 已各有）：
      · 先自动跑 producer（缺 sidecar 时），把「忘了跑」与「跑了但后端休眠」区分开；
      · **适用 × 休眠** 的验证器：compose/review → BLOCK，逃生口 N2D_ALLOW_DEGRADED_QC=1 → WARN + 计债
        （同 fidelity-gate 单一 chokepoint，不另起逃生口；账本 rollup 在 run() 末统一汇）；
      · 始终出一条覆盖率 INFO 摘要（X/Y 现实验证器真跑过），让「这次交付到底验了几个」一眼可查。
    image/video 阶段不硬拦（产物未全/未到交付），只 INFO 提示。"""
    try:
        import consistency_coverage as cov
    except Exception:
        return
    deliverable = stage in {"compose", "review"}
    rows = cov.scene_coverage_rows(root, ep)
    # item 2：交付边界上，适用但缺 sidecar 的验证器先自动跑一次（区分「没跑」vs「跑了休眠」）。
    if deliverable:
        for r in rows:
            if r["applicable"] and not os.path.isfile(os.path.join(root, r["sidecar"])):
                _autorun_scene_verifier(root, ep, r["producer"])
        rows = cov.scene_coverage_rows(root, ep)  # 重读

    summ = cov.coverage_summary(rows)
    if summ["applicable"]:
        add(INFO, "现实覆盖", ep,
            f"场景现实验证器覆盖 {summ['ran_fresh']}/{summ['applicable']} 真跑（DINOv2/OWLv2）；"
            f"休眠 {summ['dormant']}（适用但后端没真出活）。stage={stage}")
    if not deliverable:
        return
    allow_degraded = degraded_qc_active()
    for r in rows:
        if not r["dormant"]:
            continue
        loc = r["sidecar"]
        run_hint = f"跑 python3 skills/n2d-review/scripts/{r['producer']} \"{root}\" {ep} --write（需对应重型后端 env）"
        if allow_degraded:
            note_degraded_qc_waiver("现实覆盖", ep, loc, f"{r['label']} 后端休眠·交付降级放行")
            add(WARN, "现实覆盖", loc,
                f"{r['label']} 适用但休眠（后端没真验证），N2D_ALLOW_DEGRADED_QC=1 放行（自负其责·已计债）；"
                f"本次交付未真验该轴一致性。{run_hint}",
                risk_score=0.75)
        else:
            add(BLOCK, "现实覆盖", loc,
                f"{r['label']} 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——"
                f"「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。{run_hint}",
                risk_score=0.85, return_to_stage="image",
                rerun_scope=f"对当前产物跑 {r['producer']} --write（真后端）", affected_artifacts=[loc])

__all__ = [
    'check_semantic_lineage',
    'check_state_continuity',
    'check_multimodal_continuity',
    'check_consistency_audit_gate',
    'check_consistency_ledger_gate',
    'check_consistency_reality_coverage',
]
