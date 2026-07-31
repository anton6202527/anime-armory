#!/usr/bin/env python3
"""gates/consistency.py — 语义谱系/状态百科/多模态一致性(3 locked)+一致性审计闸簇族

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座，避免与 gate.py 循环导入；
gate.py `from gates.consistency import *` 回灌，run()/按名自省助手照常解析；成员经校验 call-graph-closed。
"""
from gate_core import *  # noqa: F401,F403
from gate_core import (
    _add_continuity_rows,
    _advisory_row_signed_off,
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

IMAGE_QC_AUTHORITATIVE_DIMS = {"脸(G1)", "发型(H1)", "服装配色(N1)", "风格(S1)", "场景(O2)", "多模态(P2)", "手部/解剖(N5)"}
HUMAN_REVIEW_SIGNOFF_DIMS = {"发型(H1)"}


def _image_qc_clears_pixel_blocks(root: str, ep: str) -> bool:
    """True when the current image_qc report is fresh/full and has no hard blocks.

    image_qc is the image-stage pixel gate because it can carry audited manual
    confirmations (face/prop) and the strict-pixel policy.  consistency_audit is
    still valuable as an omnibus report, but it must not re-hard-block the same
    image pixel rows after image_qc has already produced a fresh hard=0 verdict.
    """
    path = os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")
    data = load_json(path)
    if not isinstance(data, dict):
        return False
    if fingerprint_is_fresh is None:
        return False
    try:
        if not fingerprint_is_fresh(data.get("inputs_fingerprint"), root):
            return False
    except Exception:
        return False
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    env = data.get("qc_environment") if isinstance(data.get("qc_environment"), dict) else {}
    coverage = data.get("face_reference_coverage") if isinstance(data.get("face_reference_coverage"), dict) else {}
    return (
        int(float(summary.get("hard_blocks") or 0)) == 0
        and str(env.get("precision_level") or coverage.get("precision_level") or "") == "full"
        and str(coverage.get("verdict") or "ok") == "ok"
    )


def _image_stage_should_ignore_video_finding(row: Mapping[str, Any]) -> bool:
    dim = str(row.get("dimension") or row.get("dim") or "")
    return_to = str(row.get("return_to_stage") or "")
    artifacts = row.get("affected_artifacts") if isinstance(row.get("affected_artifacts"), list) else []
    joined = " ".join(str(x) for x in artifacts)
    return return_to.startswith("video") or dim.startswith("视频") or "出视频/" in joined or "video_" in joined


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
        allow_degraded = degraded_qc_active(root)
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
                f"{boundary}不放行——请在 full 环境复跑，或显式 N2D_ALLOW_DEGRADED_QC=1 / 项目 internal_only demo 放行并自负其责。",
                return_to_stage="review",
            )
        else:
            if allow_degraded and strict_stage:
                note_degraded_qc_waiver("一致性总审", ep, loc, f"审计精度 {precision}·像素一致性降级放行")
            note = f"（已通过{degraded_qc_waiver_label(root)}放行）" if allow_degraded else ""
            add(
                WARN,
                "一致性总审",
                loc,
                f"一致性审计精度为 {precision}；机检通过不等于脸部/像素一致性已完整验证，正式定稿前应在 full 环境复跑。{note}",
                return_to_stage="review",
            )

    # 证据等级账本（#3）：advanced tier（torch/syncnet 进阶依赖缺位的跨帧主体一致/口型词级）此前完全
    # 不可见也不阻断；这里在交付边界把"本可验到 embedding/pixel 却只到结构级"的维度判 PENDING→BLOCK。
    eg_allow_waiver = degraded_qc_active(root)
    eg_under = (summary.get("evidence_grade") or {}).get("under_proven") or [] if isinstance(summary.get("evidence_grade"), Mapping) else []
    if eg_allow_waiver and stage in {"compose", "review"} and eg_under:
        note_degraded_qc_waiver("证据等级", ep, loc, f"advanced tier 未达标降级放行：{('、').join(str(d) for d in eg_under)}")
    for eg_sev, eg_msg in evidence_grade_findings(summary, stage, eg_allow_waiver):
        add(eg_sev, "证据等级", loc, eg_msg, return_to_stage="review")

    block_count = 0
    mapped_warns = 0
    skipped_warns = 0
    intentional_downgrades = 0
    qc_downgrades = 0
    advisory_downgrades = 0
    ignored_video_findings = 0
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
    # A fresh/full image-stage pixel verdict remains authoritative downstream.
    # Video/compose/review must not resurrect the same hair/outfit/face heuristic
    # rows after image_qc has already cleared the current pixels.
    image_qc_pixel_clear = stage in {"image", "video", "compose", "review"} and _image_qc_clears_pixel_blocks(root, ep)
    for row in sorted_rows:
        if not isinstance(row, dict):
            continue
        sev = str(row.get("severity") or row.get("verdict") or "").lower()
        if sev not in {BLOCK, WARN}:
            continue
        if stage == "image" and _image_stage_should_ignore_video_finding(row):
            ignored_video_findings += 1
            continue
        dim = str(row.get("dimension") or row.get("dim") or "一致性总审")
        qc_downgraded = False
        if sev == BLOCK and image_qc_pixel_clear and dim in IMAGE_QC_AUTHORITATIVE_DIMS:
            sev = WARN
            qc_downgraded = True
            qc_downgrades += 1
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
        advisory_note = ""
        advisory_signed = False
        if (
            sev == BLOCK
            and stage in {"video", "compose", "review"}
            and dim in REQUIRED_VIDEO_EVIDENCE_DIMENSIONS
            and _advisory_row_signed_off(root, ep, row)
        ):
            sev = WARN
            advisory_signed = True
            advisory_downgrades += 1
            advisory_note = "[consistency_advisory_signoff 已签收·视频后验证据] "
        if (
            sev == BLOCK
            and stage in {"video", "compose", "review"}
            and dim in HUMAN_REVIEW_SIGNOFF_DIMS
            and _advisory_row_signed_off(root, ep, row)
        ):
            sev = WARN
            advisory_signed = True
            advisory_downgrades += 1
            advisory_note = "[consistency_advisory_signoff 已人工复核签收·像素误报] "
        strict_block, strict_reason = _strict_advisory_should_block(root, ep, stage, row, summary)
        if sev == WARN and strict_block and not intentional_signed and not qc_downgraded and not advisory_signed:
            sev = BLOCK
        if sev == WARN:
            if mapped_warns >= 12:
                skipped_warns += 1  # 不静默丢——循环后出一条 rollup，避免"12 条已处理"的错觉
                continue
            mapped_warns += 1
        else:
            block_count += 1
        msg = str(row.get("message") or row.get("msg") or row.get("reason") or "一致性审计发现问题")
        if intentional_note:
            msg = intentional_note + msg
        if advisory_note:
            msg = advisory_note + msg
        if qc_downgraded:
            msg = "[fresh image_qc hard=0 已覆盖同类像素硬闸] " + msg
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
    # 例外：本轮把 native block 作为「已签收的有意不连续 / 视频后验证据 signoff / QC 覆盖」降级成 WARN 时，
    # 非 0 退出码已被这些降级解释，gate 也已把它们以 WARN 留痕——不再误补 generic block。
    if (
        proc.returncode != 0
        and not block_count
        and not intentional_downgrades
        and not advisory_downgrades
        and not qc_downgrades
        and not ignored_video_findings
    ):
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
            f"现实验证器覆盖 {summ['ran_fresh']}/{summ['applicable']} 真跑（场景 DINOv2/OWLv2 + 道具在场 O3V + "
            f"外观判官 VAP + 服装 CLIP-I）；休眠 {summ['dormant']}（适用但后端/裁决没真出活）。stage={stage}")
    if not deliverable:
        return
    allow_degraded = degraded_qc_active(root)
    for r in rows:
        if not r["dormant"]:
            continue
        loc = r["sidecar"]
        run_hint = f"跑 python3 skills/n2d/n2d-review/scripts/{r['producer']} \"{root}\" {ep} --write（需对应重型后端 env）"
        if r.get("hint"):
            run_hint += f"；或：{r['hint']}"
        if allow_degraded:
            note_degraded_qc_waiver("现实覆盖", ep, loc, f"{r['label']} 后端休眠·交付降级放行")
            add(WARN, "现实覆盖", loc,
                f"{r['label']} 适用但休眠（后端没真验证），已通过{degraded_qc_waiver_label(root)}放行（自负其责·已计债）；"
                f"本次交付未真验该轴一致性。{run_hint}",
                risk_score=0.75)
        else:
            add(BLOCK, "现实覆盖", loc,
                f"{r['label']} 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——"
                f"「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 / 项目 internal_only demo 计债放行。{run_hint}",
                risk_score=0.85, return_to_stage="image",
                rerun_scope=f"对当前产物跑 {r['producer']} --write（真后端）", affected_artifacts=[loc])

def check_series_ledger_gate(root: str, ep: str) -> None:
    """剧级总账闸（2026-07-26 落地）：series_ledger 的季级铁律——集 ledger 缺签收、任一集 blocked、
    跨集脸漂 block、多集季缺身份实测报告——此前**从未被流水线调用**（只能手动 --strict），季级一致性
    enforcement 悬空。本闸在 review 阶段真跑它并把 delivery_surface 落成 finding；逃生口同走
    N2D_ALLOW_DEGRADED_QC 单一 chokepoint。

    集范围只取**已生产**的集（有出图 PNG 或已有 consistency_ledger），不把只写了脚本、尚未进产线的
    未来集当缺签收（否则首集 review 会被计划中的第3-10集永久卡死）。"""
    try:
        import series_ledger as sl
    except Exception:
        return
    produced: List[str] = []
    for cand in sl.discover_episodes(root):
        has_png = os.path.isdir(os.path.join(root, "出图", cand, "图片"))
        has_ledger = os.path.isfile(os.path.join(root, "生产数据", f"consistency_ledger_{cand}.json"))
        if has_png or has_ledger:
            produced.append(cand)
    if len(produced) < 2:
        return  # 单集/首集无跨集语义，季级总账不设闸
    try:
        ledger = sl.run(root, episodes=produced)
    except Exception as exc:
        add(WARN, "剧级总账", "series_ledger", f"剧级总账构建失败：{exc}——季级一致性 enforcement 此刻无数据。")
        return
    surface = ledger.get("delivery_surface") or {}
    if str(surface.get("status")) != "blocked":
        add(INFO, "剧级总账", "生产数据/series_ledger.json",
            f"剧级总账 pass：{ledger.get('ledgers_present')}/{ledger.get('episode_count')} 集已签收，"
            "跨集身份无 block。")
        return
    blocking = surface.get("blocking") or {}
    reasons = []
    if blocking.get("episodes_missing_ledger"):
        reasons.append(f"缺集签收 {blocking['episodes_missing_ledger']}")
    if blocking.get("episodes_blocked"):
        reasons.append(f"集内 block 未清 {blocking['episodes_blocked']}")
    if blocking.get("identity_block_characters"):
        reasons.append(f"跨集脸漂 block {[c.get('character') for c in blocking['identity_block_characters'] if isinstance(c, Mapping)]}")
    if blocking.get("identity_report_missing"):
        reasons.append("多集季缺身份实测报告（跨集崩脸未核验）")
    msg = ("剧级总账 blocked：" + "；".join(reasons) +
           "。按 series_ledger.md 的最薄弱集次序回源修复/签收后复跑 review。")
    if degraded_qc_active(root):
        note_degraded_qc_waiver("剧级总账", ep, "生产数据/series_ledger.json", "季级总账 blocked·交付降级放行")
        add(WARN, "剧级总账", "生产数据/series_ledger.json",
            msg + f"（已通过{degraded_qc_waiver_label(root)}放行·自负其责·已计债）", risk_score=0.8)
    else:
        add(BLOCK, "剧级总账", "生产数据/series_ledger.json", msg,
            risk_score=0.9, return_to_stage="review",
            affected_artifacts=["生产数据/series_ledger.json"])


__all__ = [
    'check_semantic_lineage',
    'check_state_continuity',
    'check_multimodal_continuity',
    'check_consistency_audit_gate',
    'check_consistency_ledger_gate',
    'check_consistency_reality_coverage',
    'check_series_ledger_gate',
]
