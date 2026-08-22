import type { CanvasProductionState, LineKey } from "./types";
import { canvasCandidateTargetRel } from "../../shared/canvasTargets";

const LINE_ENTRY: Record<LineKey, string> = {
  n2d: "n2d-supervisor",
  comic: "comic-batch",
  ad: "ad",
  mv: "mv",
  song: "song",
  novel: "novel",
};

/** Build the one-click production handoff. The agent remains the executor, but
 *  the canvas state/hash/definition-of-done are the machine contract; terminal
 *  prose is no longer treated as a completion receipt. */
export function buildCanvasProductionPrompt(
  line: LineKey,
  rootPath: string,
  episode: string,
  state: CanvasProductionState,
  runId: string,
): string {
  const task = state.tasks.find((item) => item.job_id === runId);
  const dirtyNodes = Object.values(state.node_fingerprints)
    .filter((node) => node.lifecycle !== "accepted")
    .map((node) => node.id);
  const dirtyTargets = state.authoring.clips
    .filter((clip) => dirtyNodes.includes(clip.id))
    .map((clip) => {
      const target = clip.final_target ?? { slot: state.authoring.final_stage, output_path: "（旧状态未声明）" };
      return `${clip.id} → ${target.slot} → candidate=${canvasCandidateTargetRel(target.output_path, runId)} → stable=${target.output_path}`;
    });
  const finalTarget = task?.target_output_path ?? "";
  const finalCandidate = task?.candidate_output_path ??
    (finalTarget ? canvasCandidateTargetRel(finalTarget, runId) : "");
  return [
    `请使用 ${LINE_ENTRY[line]}，从当前画布制作状态继续，一键推进到可验收最终成品。`,
    `作品目录：${rootPath}`,
    `集/话：${episode}`,
    `画布 run_id：${runId}`,
    `唯一内容哈希（SHA-256）：${state.content_hash}`,
    `权威创作源：${state.authoring.source_rel}`,
    `制作状态文件：生产数据/canvas_state_${episode}.json`,
    `最终成片 candidate：${finalCandidate || "当前作品线未声明"}`,
    `最终成片 stable target（只读，禁止 agent 直写）：${finalTarget || "当前作品线未声明"}`,
    "",
    `当前需要处理的节点：${dirtyNodes.length ? dirtyNodes.join("、") : "节点已齐，继续最终合成/导出与 QC"}`,
    `最终目标映射：${dirtyTargets.length ? dirtyTargets.join("；") : "沿用已验收节点的 final_target"}`,
    "",
    "执行约束：",
    "- 先重新读取权威创作源、_设置.md、_进度.md、当前制作状态和本线 gate；只处理当前哈希对应的工作。",
    "- 普通创作与技术选择采用证据最强的推荐方案自动继续；局部失败按本线策略限次重试、降级或返工，不逐镜等待用户确认。",
    "- 只在真人/版权/合规授权缺失、超出已授权预算包、不可逆覆盖/删除、公开发布，或两个核心方向无证据可优选时暂停。",
    `- 仅重做 input_hash 失效或尚未 accepted 的节点；保留 input_hash 未变的已验收节点。最终节点槽固定为：漫画 target_slot=panel、其它视觉线 target_slot=video；target_output_path 必须是权威脚本/任务包声明且实际采用的作品内相对输出路径。`,
    `- 禁止写任何 stable target。每个节点只能写 job-scoped candidate：按上方映射的 candidate 路径；candidate 必须与 stable target 同父目录下 .canvas-candidates/${runId}/...。桌面主进程才有权在复核当前 task/content/input/node_input/target、候选字节 SHA、probe/QC 后原子晋升。`,
    `- 每个新候选用真实字节算 SHA-256、实际媒体 probe，并原子写 生产数据/canvas_node_candidate_qc_${runId}_<node_id安全名>.json：kind=anime_armory_canvas_node_candidate_qc，version=1，episode=${episode}，job_id=${runId}，node_id，generation_kind=${state.authoring.final_stage}，target_slot/target_output_path/candidate_output_path，content_hash=${state.content_hash}，input_hash=该节点 canvas_state.node_fingerprints[node_id].input_hash，task_input_hash=${state.content_hash}，candidate_sha256/qa_blocks=0/verdict=pass/probe_passed=true。`,
    `- 再分别原子写 生产数据/canvas_node_candidate_receipt_${runId}_<node_id安全名>.json：kind=anime_armory_canvas_node_candidate_receipt，version=1，根对象绑定同一组字段，并带 qa_receipt_path/qa_receipt_sha256/qa_blocks=0/verdict=pass/probe_passed=true。技术执行者不得填写 reviewer_kind=human、不得伪造 accepted。`,
    `- B14 硬闸：每张图片 candidate 必须展示当前像素并取得用户对该 SHA-256 的显式签收；签收证据 kind=anime_armory_canvas_candidate_human_acceptance，必须绑定本 job/node/target/candidate/content/input/task_input/candidate_sha256、具名 reviewer、带时区 accepted_at 与 confirmation={kind:"explicit_current_pixels_acceptance",accepted_current_pixels:true}。把该文件路径/SHA 写进 candidate receipt 的 human_acceptance_path/human_acceptance_sha256 后，主进程才可晋升图片。没有真实签收就停在 candidate，禁止继续下一张。视频可自动晋升为 machine_complete，但没有 human 节点签收不得 accepted。`,
    `- 节点齐备后读取桌面端生成的 生产数据/canvas_inputs_manifest_${episode}.json，并核对 content_hash=${state.content_hash}。inputs_sha256 的唯一算法是：按 authoring.clips 顺序取数组 [{id,input_hash,output_sha256}]，每个对象键按字典序，UTF-8、紧凑 JSON，整体 SHA-256；不要对 output_path、时间戳或整个 manifest 文件求哈希。`,
    `- 完成正式合成/导出时也只写最终成片 candidate=${finalCandidate}，绝不直写 stable=${finalTarget}。原子写 生产数据/canvas_final_candidate_qc_${runId}.json：kind=anime_armory_canvas_final_candidate_qc，version=1，episode=${episode}，job_id=${runId}，content_hash=${state.content_hash}，task_input_hash=${state.content_hash}，inputs_sha256，target_output_path/candidate_output_path/candidate_sha256，qa_blocks=0/verdict=pass/probe_passed=true；再写 canvas_final_candidate_receipt_${runId}.json（kind=anime_armory_canvas_final_candidate_receipt）并带 QA 路径/哈希。主进程只登记 machine_complete；最终成品必须由用户在桌面端显式验收，技术执行者不得代签。`,
    "- 任何阶段若发现权威内容哈希已不是上述 SHA-256，立即把本 run 标 stale，按新状态重新规划，禁止旧任务覆盖新修订。",
    "- 完成后刷新本线进度与证据。桌面端会自动复算 machine_complete，但逐图当前像素和最终成品验收是硬停点；不要手填 accepted/complete，也不要代替用户确认。",
  ].join("\n");
}
