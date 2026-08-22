import assert from "node:assert/strict";
import test from "node:test";

import {
  SCRIPT_WORKBENCH_SCHEMA,
  computeScriptWorkbenchContentSha256,
  createStableScriptWorkbenchId,
  normalizeScriptWorkbench,
  prepareScriptWorkbenchVideoJobs,
  scriptWorkbenchSha256Bytes,
  serializeScriptWorkbench,
  setScriptWorkbenchGlobalStyle,
  updateScriptWorkbenchShot,
  updateScriptWorkbenchJobStatus,
  validateScriptWorkbench,
  type ScriptWorkbenchByteVerification,
} from "../src/features/canvas/scriptWorkbenchModel";

const shot = {
  id: "shot-1",
  duration: 8,
  visual: "姜大人走入雨夜长街",
  scale: "中景",
  lighting: "冷色路灯",
  dialogue: "",
  sound: "雨声",
  camera: "缓慢跟拍",
  final_prompt: "雨夜长街，中景跟拍姜大人",
  color: "",
};

function readyDocument() {
  return normalizeScriptWorkbench({
    title: "那妖魔是姜大人",
    global_style: "东方奇幻电影感",
    shots: [shot],
    assets: [],
  });
}

function verifiedBytes(
  sha256: string,
  durableRef = `backend:sha256:${sha256}`,
): ScriptWorkbenchByteVerification {
  return {
    status: "verified",
    verifier_kind: "trusted_backend",
    method: "sha256",
    durable_ref: durableRef,
    sha256,
    verified_at: "2026-08-21T00:00:00.000Z",
  };
}

function humanReceipt(contentSha: string, outputSha: string) {
  return {
    reviewer_kind: "human",
    reviewer_name: "王小明",
    verdict: "accepted",
    content_sha256: contentSha,
    output_sha256: outputSha,
    criteria: ["当前母版完整", "符合交付规格"],
    blocks: [],
    reviewed_at: "2026-08-21T12:00:00+08:00",
    confirmation: {
      kind: "current_artifact_bytes",
      artifact_sha256: outputSha,
      current_pixels_reviewed: true,
      decision: "accept",
      statement: "我已查看当前制品并接受这些确切字节。",
    },
  };
}

test("SHA-256 implementation and canonical authoring hash are deterministic", () => {
  assert.equal(
    scriptWorkbenchSha256Bytes(new TextEncoder().encode("abc")),
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  );
  const document = readyDocument();
  assert.equal(document.content_sha256, computeScriptWorkbenchContentSha256(document));
  assert.equal(document.content_sha256, "961b1ab5500e3c330cec52f4d2a5a03e20f870c3e04f83880afce7f55920882e");
  assert.match(document.content_sha256, /^[0-9a-f]{64}$/);
});

test("legacy v1 migrates without persisting steps or style lock", () => {
  const migrated = normalizeScriptWorkbench({
    schema: "app-script-workbench/v1",
    skill: "app-script-workbench",
    title: "旧脚本",
    global_style: "旧风格",
    style_locked: true,
    steps: { shots: "done", assets: "done", prompts: "done" },
    shots: [{ ...shot, final_prompt: "" }],
    assets: [],
  });
  const serialized = JSON.parse(serializeScriptWorkbench(migrated)) as Record<string, unknown>;
  assert.equal(migrated.schema, SCRIPT_WORKBENCH_SCHEMA);
  assert.notEqual(migrated.state, "complete");
  assert.equal("steps" in serialized, false);
  assert.equal("style_locked" in serialized, false);
});

test("legacy fallback ids match the Python skill SHA-256 algorithm", () => {
  assert.equal(createStableScriptWorkbenchId("shot", 1, "v"), "shot-d53d2528f0");
  assert.equal(createStableScriptWorkbenchId("asset", 1, "character:a"), "asset-e643d04a60");
  const migrated = normalizeScriptWorkbench({
    schema: "app-script-workbench/v1",
    title: "旧脚本",
    global_style: "旧风格",
    shots: [{ ...shot, id: undefined, visual: "v" }],
    assets: [{ id: undefined, kind: "character", name: "a", description: "", prompt: "", status: "pending", source: "none" }],
  });
  assert.equal(migrated.shots[0]?.id, "shot-d53d2528f0");
  assert.equal(migrated.assets[0]?.id, "asset-e643d04a60");
});

test("v2 delegated evidence migrates to machine_complete until explicit human final acceptance", () => {
  const base = readyDocument();
  const mediaSha = "b".repeat(64);
  const migratedMachine = normalizeScriptWorkbench({
    ...base,
    schema: "app-script-workbench/v2",
    jobs: [{
      id: "job-1",
      kind: "shot_video",
      shot_id: "shot-1",
      input_sha256: base.content_sha256,
      status: "succeeded",
      provider_task_id: "provider-42",
    }],
    results: [{
      id: "result-1",
      kind: "shot_video",
      shot_id: "shot-1",
      input_sha256: base.content_sha256,
      path: "media/shot-1.mp4",
      sha256: mediaSha,
      review: "accepted",
      attachmentId: "video-attachment",
      provider_payload: { task: "video-task-42" },
      byte_verification: verifiedBytes(mediaSha, "backend:video-attachment"),
      acceptance_receipt: {
        reviewer_kind: "delegated_agent",
        verdict: "accepted",
        content_sha256: base.content_sha256,
        output_sha256: mediaSha,
        criteria: ["画面与声音通过"],
        blocks: [],
      },
    }],
    master: {
      status: "ready",
      input_sha256: base.content_sha256,
      path: "media/master.mp4",
      sha256: mediaSha,
      mime_type: "video/mp4",
      duration: 8,
      byte_verification: verifiedBytes(mediaSha, "backend:master-attachment"),
    },
    qc_receipt: {
      verdict: "pass",
      reviewer_kind: "delegated_agent",
      content_sha256: base.content_sha256,
      master_sha256: mediaSha,
      checks: ["时长", "画面", "声音"],
      blocks: [],
      receipt_path: "receipts/final.json",
      receipt_sha256: "d".repeat(64),
      byte_verification: verifiedBytes("d".repeat(64), "backend:qc-receipt"),
    },
  });
  assert.equal(migratedMachine.state, "machine_complete");
  assert.equal(migratedMachine.results[0]?.review, "machine_complete");
  assert.equal(migratedMachine.jobs[0]?.provider_task_id, "provider-42");
  assert.equal(migratedMachine.results[0]?.attachmentId, "video-attachment");
  assert.deepEqual(migratedMachine.results[0]?.provider_payload, { task: "video-task-42" });

  const withEvidence = normalizeScriptWorkbench({
    ...migratedMachine,
    final_acceptance_receipt: humanReceipt(migratedMachine.content_sha256, mediaSha),
  });
  assert.equal(withEvidence.state, "complete");
  assert.equal(withEvidence.jobs[0]?.provider_task_id, "provider-42");
  assert.equal(withEvidence.results[0]?.attachmentId, "video-attachment");
  assert.deepEqual(withEvidence.results[0]?.provider_payload, { task: "video-task-42" });
  assert.equal(withEvidence.qc_receipt.receipt_path, "receipts/final.json");

  const roundTripped = normalizeScriptWorkbench(JSON.parse(serializeScriptWorkbench(withEvidence)));
  assert.equal(roundTripped.jobs[0]?.provider_task_id, "provider-42");
  assert.deepEqual(roundTripped.results[0]?.provider_payload, { task: "video-task-42" });
  assert.equal(roundTripped.state, "complete");

  const recolored = updateScriptWorkbenchShot(withEvidence, "shot-1", { color: "blue" });
  assert.equal(recolored.content_sha256, withEvidence.content_sha256);
  assert.equal(recolored.state, "complete");
});

test("every legacy v1 spelling preserves runtime evidence and fail-closed downgrades acceptance", () => {
  for (const [schema, skill] of [
    ["app-script-workbench/v1", "app-script-workbench"],
    ["n2d-script-workbench/v1", "n2d-script-workbench"],
    ["app-n2d-script-workbench/v1", "app-n2d-script-workbench"],
  ] as const) {
    const mediaSha = "b".repeat(64);
    const assetSha = "c".repeat(64);
    const qcSha = "d".repeat(64);
    const base = normalizeScriptWorkbench({
      title: "旧版有运行证据的脚本",
      global_style: "东方奇幻电影感",
      shots: [shot],
      assets: [{
        id: "asset-1",
        kind: "character",
        name: "姜大人",
        description: "黑色长袍",
        prompt: "角色设定图",
        status: "pending",
        source: "upload",
        path: "media/character.png",
        sha256: assetSha,
        byte_verification: verifiedBytes(assetSha, "backend:character-attachment"),
      }],
    });
    const migrated = normalizeScriptWorkbench({
      ...base,
      schema,
      skill,
      state: "complete",
      assets: [{
        ...base.assets[0],
        status: "accepted",
        acceptance_receipt: humanReceipt(base.content_sha256, assetSha),
      }],
      jobs: [{
        id: "legacy-job-1",
        kind: "shot_video",
        shot_id: "shot-1",
        input_sha256: base.content_sha256,
        status: "succeeded",
        provider_task_id: "provider-legacy-42",
      }],
      results: [{
        id: "legacy-result-1",
        kind: "shot_video",
        shot_id: "shot-1",
        input_sha256: base.content_sha256,
        path: "media/shot-1.mp4",
        sha256: mediaSha,
        review: "accepted",
        byte_verification: verifiedBytes(mediaSha, "backend:legacy-video"),
        acceptance_receipt: humanReceipt(base.content_sha256, mediaSha),
      }],
      master: {
        status: "ready",
        input_sha256: base.content_sha256,
        path: "media/master.mp4",
        sha256: mediaSha,
        mime_type: "video/mp4",
        duration: 8,
        byte_verification: verifiedBytes(mediaSha, "backend:legacy-master"),
      },
      qc_receipt: {
        verdict: "pass",
        reviewer_kind: "delegated_agent",
        content_sha256: base.content_sha256,
        master_sha256: mediaSha,
        checks: ["时长", "画面", "声音"],
        blocks: [],
        receipt_path: "receipts/legacy-qc.json",
        receipt_sha256: qcSha,
        byte_verification: verifiedBytes(qcSha, "backend:legacy-qc"),
      },
      final_acceptance_receipt: humanReceipt(base.content_sha256, mediaSha),
    });

    assert.equal(migrated.schema, SCRIPT_WORKBENCH_SCHEMA, schema);
    assert.notEqual(migrated.state, "complete", schema);
    assert.equal(migrated.assets[0]?.status, "machine_complete", schema);
    assert.equal(migrated.assets[0]?.path, "media/character.png", schema);
    assert.equal(migrated.assets[0]?.sha256, assetSha, schema);
    assert.equal(migrated.assets[0]?.legacy_acceptance_receipt?.verdict, "accepted", schema);
    assert.equal(migrated.assets[0]?.acceptance_receipt?.verdict, "pending", schema);
    assert.equal(migrated.jobs[0]?.provider_task_id, "provider-legacy-42", schema);
    assert.equal(migrated.results[0]?.review, "machine_complete", schema);
    assert.equal(migrated.results[0]?.path, "media/shot-1.mp4", schema);
    assert.equal(migrated.results[0]?.sha256, mediaSha, schema);
    assert.equal(migrated.results[0]?.legacy_acceptance_receipt?.verdict, "accepted", schema);
    assert.equal(migrated.results[0]?.acceptance_receipt.verdict, "pending", schema);
    assert.equal(migrated.master.path, "media/master.mp4", schema);
    assert.equal(migrated.qc_receipt.receipt_path, "receipts/legacy-qc.json", schema);
    assert.equal(migrated.final_acceptance_receipt.verdict, "pending", schema);
    assert.equal(migrated.migration?.source_schema, schema, schema);

    const roundTripped = normalizeScriptWorkbench(JSON.parse(serializeScriptWorkbench(migrated)));
    assert.equal(roundTripped.assets[0]?.status, "machine_complete", schema);
    assert.equal(roundTripped.assets[0]?.path, "media/character.png", schema);
    assert.equal(roundTripped.assets[0]?.legacy_acceptance_receipt?.verdict, "accepted", schema);
    assert.equal(roundTripped.jobs[0]?.provider_task_id, "provider-legacy-42", schema);
    assert.equal(roundTripped.results[0]?.legacy_acceptance_receipt?.verdict, "accepted", schema);
  }
});

test("paths and SHA-shaped strings without durable byte verification never complete", () => {
  const base = readyDocument();
  const mediaSha = "b".repeat(64);
  const unverified = normalizeScriptWorkbench({
    ...base,
    results: [{
      id: "result-1",
      kind: "shot_video",
      shot_id: "shot-1",
      input_sha256: base.content_sha256,
      path: "/definitely/not/a/real/video.mp4",
      sha256: mediaSha,
      review: "accepted",
      acceptance_receipt: {
        reviewer_kind: "delegated_agent",
        verdict: "accepted",
        content_sha256: base.content_sha256,
        output_sha256: mediaSha,
        criteria: ["画面与声音通过"],
        blocks: [],
      },
    }],
    master: {
      status: "ready",
      input_sha256: base.content_sha256,
      path: "/definitely/not/a/real/master.mp4",
      sha256: mediaSha,
      mime_type: "video/mp4",
      duration: 8,
    },
    qc_receipt: {
      verdict: "pass",
      reviewer_kind: "delegated_agent",
      content_sha256: base.content_sha256,
      master_sha256: mediaSha,
      checks: ["时长", "画面", "声音"],
      blocks: [],
      receipt_path: "/definitely/not/a/real/qc.json",
      receipt_sha256: "d".repeat(64),
    },
  });
  assert.equal(unverified.state, "needs_revision");
  assert.notEqual(unverified.state, "complete");
  assert.equal(validateScriptWorkbench(unverified).some((issue) => issue.path === "master"), true);
  assert.equal(validateScriptWorkbench(unverified).some((issue) => issue.path === "qc_receipt"), true);
});

test("delegated or malformed final receipts cannot promote machine_complete", () => {
  const base = readyDocument();
  const mediaSha = "b".repeat(64);
  const machine = normalizeScriptWorkbench({
    ...base,
    results: [{
      id: "result-1", kind: "shot_video", shot_id: "shot-1", input_sha256: base.content_sha256,
      path: "media/shot-1.mp4", sha256: mediaSha, review: "machine_complete",
      byte_verification: verifiedBytes(mediaSha),
      machine_receipt: { reviewer_kind: "delegated_agent", verdict: "pass", content_sha256: base.content_sha256, output_sha256: mediaSha, checks: ["视频可用"], blocks: [] },
    }],
    master: { status: "machine_complete", input_sha256: base.content_sha256, path: "media/master.mp4", sha256: mediaSha, mime_type: "video/mp4", duration: 8, byte_verification: verifiedBytes(mediaSha) },
    qc_receipt: { verdict: "pass", reviewer_kind: "delegated_agent", content_sha256: base.content_sha256, master_sha256: mediaSha, checks: ["母版可用"], blocks: [], receipt_path: "qc.json", receipt_sha256: "d".repeat(64), byte_verification: verifiedBytes("d".repeat(64)) },
  });
  assert.equal(machine.state, "machine_complete");
  const delegated = normalizeScriptWorkbench({
    ...machine,
    final_acceptance_receipt: { ...humanReceipt(machine.content_sha256, mediaSha), reviewer_kind: "delegated_agent" },
  });
  assert.notEqual(delegated.state, "complete");
  const naiveTime = normalizeScriptWorkbench({
    ...machine,
    final_acceptance_receipt: { ...humanReceipt(machine.content_sha256, mediaSha), reviewed_at: "2026-08-21T12:00:00" },
  });
  assert.notEqual(naiveTime.state, "complete");
});

test("invalid accepted or machine runtime evidence derives needs_revision", () => {
  const base = readyDocument();
  const mediaSha = "b".repeat(64);
  const brokenAccepted = normalizeScriptWorkbench({
    ...base,
    results: [{
      id: "result-1",
      kind: "shot_video",
      shot_id: "shot-1",
      input_sha256: base.content_sha256,
      path: "media/shot-1.mp4",
      sha256: mediaSha,
      review: "accepted",
      byte_verification: verifiedBytes(mediaSha),
      acceptance_receipt: {
        reviewer_kind: "delegated_agent",
        verdict: "accepted",
        content_sha256: base.content_sha256,
        output_sha256: "c".repeat(64),
        criteria: ["画面通过"],
        blocks: [],
      },
    }],
  });
  assert.equal(brokenAccepted.state, "needs_revision");

  const brokenMaster = normalizeScriptWorkbench({
    ...base,
    master: {
      status: "ready",
      input_sha256: base.content_sha256,
      path: "media/master.mp4",
      sha256: mediaSha,
      mime_type: "video/mp4",
      duration: 8,
    },
  });
  assert.equal(brokenMaster.state, "needs_revision");
});

test("authoring edits create a new hash and stale every old production receipt", () => {
  const base = readyDocument();
  const prepared = prepareScriptWorkbenchVideoJobs(base);
  const changed = setScriptWorkbenchGlobalStyle(prepared, "水墨东方奇幻");
  assert.notEqual(changed.content_sha256, prepared.content_sha256);
  assert.equal(changed.jobs.every((job) => job.status === "stale"), true);
  assert.equal(changed.state, "draft");
});

test("machine-complete assets require durable byte evidence; blob URLs never qualify", () => {
  const sha256 = "c".repeat(64);
  const blobOnly = normalizeScriptWorkbench({
    ...readyDocument(),
    assets: [{
      id: "asset-1", kind: "character", name: "姜大人", description: "", prompt: "", status: "ready", source: "ai", sha256, imageUrl: "blob:temporary",
      byte_verification: verifiedBytes(sha256, "blob:temporary"),
    }],
  });
  assert.equal(blobOnly.assets[0]?.status, "pending");

  const durable = normalizeScriptWorkbench({
    ...readyDocument(),
    assets: [{
      id: "asset-1", kind: "character", name: "姜大人", description: "", prompt: "", status: "ready", source: "upload", sha256, attachmentId: "attachment-1",
      byte_verification: {
        ...verifiedBytes(sha256, "attachment:attachment-1"),
        verifier_kind: "web_attachment",
      },
    }],
  });
  assert.equal(durable.assets[0]?.status, "machine_complete");
  assert.equal(durable.state, "ready");

  const accepted = normalizeScriptWorkbench({
    ...durable,
    assets: [{
      ...durable.assets[0],
      status: "accepted",
      acceptance_receipt: humanReceipt(durable.content_sha256, sha256),
    }],
  });
  assert.equal(validateScriptWorkbench(accepted).some((issue) => issue.path === "assets[0]"), false);
  const fakeHuman = normalizeScriptWorkbench({
    ...accepted,
    assets: [{ ...accepted.assets[0], acceptance_receipt: { ...accepted.assets[0]?.acceptance_receipt, reviewer_kind: "delegated_agent" } }],
  });
  assert.equal(validateScriptWorkbench(fakeHuman).some((issue) => issue.path === "assets[0]"), true);
});

test("batch video preparation creates stable jobs bound to the one content hash", () => {
  const base = readyDocument();
  const first = prepareScriptWorkbenchVideoJobs(base);
  const second = prepareScriptWorkbenchVideoJobs(first);
  assert.equal(first.jobs.length, 1);
  assert.equal(second.jobs.length, 1);
  assert.equal(first.jobs[0]?.id, second.jobs[0]?.id);
  assert.equal(first.jobs[0]?.input_sha256, first.content_sha256);
  assert.equal(first.jobs[0]?.status, "ready");
  const failed = updateScriptWorkbenchJobStatus(first, first.jobs[0]?.id ?? "", "failed", "backend unavailable");
  assert.equal(failed.state, "needs_revision");
});
