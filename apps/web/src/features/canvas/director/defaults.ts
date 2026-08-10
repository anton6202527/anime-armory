import type {
  DirectorActor,
  DirectorActorArchetype,
  DirectorCamera,
  DirectorPose,
  DirectorPoseKey,
  DirectorPosePreset,
  DirectorSceneState,
  DirectorVector3,
} from "./types";

export const DIRECTOR_ACTOR_PRESETS: Array<{ id: DirectorActorArchetype; label: string }> = [
  { id: "standard-male", label: "标准男性" },
  { id: "standard-female", label: "标准女性" },
  { id: "strong", label: "健硕" },
  { id: "slim", label: "纤细" },
  { id: "teen", label: "少年" },
  { id: "child", label: "儿童" },
  { id: "broad", label: "宽厚" },
  { id: "chibi", label: "二头身" },
  { id: "crowd", label: "群众 (3x3)" },
  { id: "geometry", label: "几何模型" },
];

export const DIRECTOR_CAMERA_PRESETS = [
  "当前视角",
  "正面中景",
  "正面特写",
  "正面全景",
  "侧面跟拍",
  "侧面近景",
  "背面中景",
  "俯拍全景",
  "45° 俯拍",
  "低角度仰拍",
  "低角度广角",
  "过肩镜头",
  "过肩镜头（右）",
  "鸟瞰",
  "荷兰角",
] as const;

export const DIRECTOR_POSE_PRESETS: Array<{ id: DirectorPosePreset; label: string }> = [
  { id: "stand", label: "站立" },
  { id: "t-pose", label: "T型" },
  { id: "walk", label: "行走" },
  { id: "run", label: "跑步" },
  { id: "sit", label: "坐姿" },
  { id: "squat", label: "蹲下" },
  { id: "kneel-one", label: "单膝跪" },
  { id: "kneel-two", label: "双膝跪" },
  { id: "hands-hips", label: "叉腰" },
  { id: "lean", label: "倚靠" },
  { id: "bow", label: "鞠躬" },
  { id: "think", label: "思考" },
  { id: "fight", label: "格斗" },
  { id: "kick", label: "踢球" },
  { id: "throw", label: "投掷" },
  { id: "push", label: "推进" },
  { id: "wave", label: "招手" },
  { id: "reach", label: "伸手" },
  { id: "arms-crossed", label: "抱臂" },
  { id: "phone", label: "看手机" },
];

export const DIRECTOR_POSE_SECTIONS: Array<{
  title: string;
  controls: Array<{ key: DirectorPoseKey; label: string; min?: number; max?: number }>;
}> = [
  { title: "身体", controls: [{ key: "bodyPitch", label: "前倾" }, { key: "bodyTurn", label: "转身" }, { key: "bodyRoll", label: "侧倾" }] },
  { title: "躯干", controls: [{ key: "torsoPitch", label: "前倾" }, { key: "torsoTwist", label: "扭转" }, { key: "torsoRoll", label: "侧倾" }] },
  { title: "头部", controls: [{ key: "headPitch", label: "点头" }, { key: "headTurn", label: "转头" }, { key: "headRoll", label: "歪头" }] },
  { title: "手臂 — 肩", controls: [
    { key: "leftShoulderPitch", label: "左 · 前举" }, { key: "leftShoulderOut", label: "左 · 外展" }, { key: "leftShoulderTwist", label: "左 · 扭转" },
    { key: "rightShoulderPitch", label: "右 · 前举" }, { key: "rightShoulderOut", label: "右 · 外展" }, { key: "rightShoulderTwist", label: "右 · 扭转" },
  ] },
  { title: "肘部", controls: [{ key: "leftElbow", label: "左 · 弯曲", min: 0, max: 150 }, { key: "rightElbow", label: "右 · 弯曲", min: 0, max: 150 }] },
  { title: "腿部 — 髋", controls: [
    { key: "leftHipPitch", label: "左 · 前抬" }, { key: "leftHipOut", label: "左 · 外展" }, { key: "leftHipTwist", label: "左 · 扭转" },
    { key: "rightHipPitch", label: "右 · 前抬" }, { key: "rightHipOut", label: "右 · 外展" }, { key: "rightHipTwist", label: "右 · 扭转" },
  ] },
  { title: "膝部", controls: [{ key: "leftKnee", label: "左 · 弯曲", min: 0, max: 150 }, { key: "rightKnee", label: "右 · 弯曲", min: 0, max: 150 }] },
];

export function defaultDirectorPose(): DirectorPose {
  return {
    bodyPitch: 0, bodyTurn: 0, bodyRoll: 0,
    torsoPitch: 2, torsoTwist: 0, torsoRoll: 0,
    headPitch: -10, headTurn: 0, headRoll: 0,
    leftShoulderPitch: -5, leftShoulderOut: 7, leftShoulderTwist: 0,
    rightShoulderPitch: -5, rightShoulderOut: 7, rightShoulderTwist: 0,
    leftElbow: 15, rightElbow: 15,
    leftHipPitch: 0, leftHipOut: 0, leftHipTwist: 0,
    rightHipPitch: 0, rightHipOut: 0, rightHipTwist: 0,
    leftKnee: 0, rightKnee: 0,
  };
}

export function createDirectorActor(index: number, archetype: DirectorActorArchetype = "standard-male"): DirectorActor {
  const colors = ["#4F8EF7", "#F75353", "#43C59E", "#C983FF", "#F5B642"];
  return {
    id: `actor-${crypto.randomUUID()}`,
    kind: "actor",
    name: `角色${String.fromCharCode(65 + index)}`,
    archetype,
    position: [index ? (index % 2 ? 1.25 : -1.25) : 0, 0, index ? Math.floor(index / 2) * .7 : 0],
    rotation: [0, 0, 0],
    scale: [1.03, 1.03, 1.03],
    color: colors[index % colors.length],
    visible: true,
    locked: false,
    posePreset: "stand",
    pose: defaultDirectorPose(),
  };
}

function lookAtRotation(position: DirectorVector3, target: DirectorVector3, roll = 0): DirectorVector3 {
  const dx = target[0] - position[0];
  const dy = target[1] - position[1];
  const dz = target[2] - position[2];
  const length = Math.hypot(dx, dy, dz) || 1;
  return [
    Math.asin(dy / length) * 180 / Math.PI,
    Math.atan2(-dx, -dz) * 180 / Math.PI,
    roll,
  ];
}

function cameraPreset(position: DirectorVector3, target: DirectorVector3, fov: number, roll = 0) {
  return { position, rotation: lookAtRotation(position, target, roll), fov };
}

const CAMERA_PRESET_VALUES: Record<string, { position: DirectorVector3; rotation: DirectorVector3; fov: number }> = {
  "正面中景": cameraPreset([0, 1.7, 5], [0, 1.55, 0], 35),
  "正面特写": cameraPreset([0, 1.7, 2], [0, 1.62, 0], 35),
  "正面全景": cameraPreset([0, 2, 8], [0, 1.35, 0], 45),
  "侧面跟拍": cameraPreset([5.2, 1.8, 0], [.4, 1.35, 0], 42),
  "侧面近景": cameraPreset([3.8, 1.7, 0], [.25, 1.5, 0], 35),
  "背面中景": cameraPreset([0, 1.7, -5], [0, 1.5, 0], 35),
  "俯拍全景": cameraPreset([0, 8, 3], [0, .8, 0], 48),
  "45° 俯拍": cameraPreset([4, 5, 5], [0, 1, 0], 40),
  "低角度仰拍": cameraPreset([0, .45, 3], [0, 1.45, 0], 36),
  "低角度广角": cameraPreset([0, .35, 2.6], [0, 1.35, 0], 62),
  "过肩镜头": cameraPreset([-1.4, 1.65, 2.3], [0, 1.45, 0], 42),
  "过肩镜头（右）": cameraPreset([1.4, 1.65, 2.3], [0, 1.45, 0], 42),
  "鸟瞰": cameraPreset([0, 10, .01], [0, 0, 0], 50),
  "荷兰角": cameraPreset([0, 1.7, 4.5], [0, 1.5, 0], 38, 18),
};

export function createDirectorCamera(index: number, preset = "正面中景", current?: { position: DirectorVector3; rotation: DirectorVector3; fov?: number }): DirectorCamera {
  const fallback = CAMERA_PRESET_VALUES[preset] ?? CAMERA_PRESET_VALUES["正面中景"];
  return {
    id: `camera-${crypto.randomUUID()}`,
    kind: "camera",
    name: `机位${index + 1}`,
    position: current?.position ?? fallback.position,
    rotation: current?.rotation ?? fallback.rotation,
    scale: [1, 1, 1],
    color: "#4F8EF7",
    visible: true,
    locked: false,
    fov: current?.fov ?? fallback.fov,
    followTargetId: null,
    followOffset: null,
    lookAtMode: "rotation",
    lookAtTargetId: null,
    lookAt: [0, 1.6, 0],
    shots: [],
  };
}

export function createDefaultDirectorScene(): DirectorSceneState {
  const camera = createDirectorCamera(0);
  const actor = createDirectorActor(0);
  return {
    schema: "labutv-director/v1",
    panel: "scene",
    tool: "translate",
    viewMode: "director",
    aspectRatio: "16:9",
    compositionGuide: false,
    selectedObjectId: actor.id,
    activeCameraId: camera.id,
    objects: [camera, actor],
    timeline: {
      duration: 10,
      head: 0,
      loop: false,
      autoFrame: false,
      tracks: [],
    },
    scene: {
      position: [0, 0, 0],
      rotation: [0, 0, 0],
      scale: 3,
      skyColor: "#060608",
      panoramaAttachmentId: null,
      panoramaRotation: 0,
      panoramaRadius: 60,
      showLabels: true,
      gridSnap: false,
      groundSnap: true,
      showGround: true,
      groundOpacity: .4,
      groundHeight: 0,
    },
  };
}

function vector(value: unknown, fallback: DirectorVector3): DirectorVector3 {
  if (!Array.isArray(value) || value.length !== 3) return fallback;
  const next = value.map(Number);
  return next.every(Number.isFinite) ? next as DirectorVector3 : fallback;
}

function bounded(value: unknown, fallback: number, min: number, max: number) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
}

function text(value: unknown, fallback: string, max = 120) {
  return typeof value === "string" && value.trim() ? value.trim().slice(0, max) : fallback;
}

function color(value: unknown, fallback: string) {
  return typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value) ? value.toUpperCase() : fallback;
}

function boolean(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

const ACTOR_ARCHETYPES = new Set(DIRECTOR_ACTOR_PRESETS.map((preset) => preset.id));
const POSE_PRESETS = new Set(DIRECTOR_POSE_PRESETS.map((preset) => preset.id));
const PANELS = new Set(["scene", "actors", "cameras", "panorama", "ratio"]);
const TOOLS = new Set(["select", "translate", "rotate", "scale"]);
const VIEW_MODES = new Set(["director", "camera"]);
const ASPECTS = new Set(["adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]);

function normalizeObject(item: unknown, index: number): DirectorSceneState["objects"][number] | null {
  if (!item || typeof item !== "object") return null;
  const source = item as Record<string, unknown>;
  if (source.kind === "actor") {
    const archetype = ACTOR_ARCHETYPES.has(source.archetype as DirectorActorArchetype) ? source.archetype as DirectorActorArchetype : "standard-male";
    const fallback = createDirectorActor(index, archetype);
    const poseSource = source.pose && typeof source.pose === "object" ? source.pose as Record<string, unknown> : {};
    const basePose = defaultDirectorPose();
    const pose = Object.fromEntries(Object.entries(basePose).map(([key, fallbackValue]) => [key, bounded(poseSource[key], fallbackValue, -180, 180)])) as DirectorPose;
    return {
      ...fallback,
      id: text(source.id, fallback.id, 160),
      name: text(source.name, fallback.name),
      position: vector(source.position, fallback.position),
      rotation: vector(source.rotation, fallback.rotation),
      scale: vector(source.scale, fallback.scale).map((entry) => bounded(entry, 1, .01, 100)) as DirectorVector3,
      color: color(source.color, fallback.color),
      visible: boolean(source.visible, true),
      locked: boolean(source.locked, false),
      archetype,
      posePreset: POSE_PRESETS.has(source.posePreset as DirectorPosePreset) ? source.posePreset as DirectorPosePreset : "stand",
      pose,
    };
  }
  if (source.kind === "camera") {
    const fallback = createDirectorCamera(index);
    const shots = Array.isArray(source.shots) ? source.shots.slice(0, 100).flatMap((value, shotIndex) => {
      if (!value || typeof value !== "object") return [];
      const shot = value as Record<string, unknown>;
      const attachmentId = text(shot.attachmentId, "", 160);
      if (!attachmentId) return [];
      return [{
        id: text(shot.id, `shot-${index}-${shotIndex}`, 160),
        name: text(shot.name, `截图 ${shotIndex + 1}`),
        attachmentId,
        mimeType: text(shot.mimeType, "image/png", 80),
        width: Math.round(bounded(shot.width, 1920, 1, 8192)),
        height: Math.round(bounded(shot.height, 1080, 1, 8192)),
        createdAt: text(shot.createdAt, new Date(0).toISOString(), 80),
      }];
    }) : [];
    return {
      ...fallback,
      id: text(source.id, fallback.id, 160),
      name: text(source.name, fallback.name),
      position: vector(source.position, fallback.position),
      rotation: vector(source.rotation, fallback.rotation),
      scale: vector(source.scale, fallback.scale).map((entry) => bounded(entry, 1, .01, 100)) as DirectorVector3,
      color: color(source.color, fallback.color),
      visible: boolean(source.visible, true),
      locked: boolean(source.locked, false),
      fov: bounded(source.fov, fallback.fov, 15, 120),
      followTargetId: typeof source.followTargetId === "string" ? source.followTargetId.slice(0, 160) : null,
      followOffset: source.followOffset == null ? null : vector(source.followOffset, fallback.followOffset ?? [0, 0, 0]),
      lookAtMode: source.lookAtMode === "point" || source.lookAtMode === "object" ? source.lookAtMode : "rotation",
      lookAtTargetId: typeof source.lookAtTargetId === "string" ? source.lookAtTargetId.slice(0, 160) : null,
      lookAt: vector(source.lookAt, fallback.lookAt),
      shots,
    };
  }
  if (source.kind === "prop") {
    const id = text(source.id, `prop-${crypto.randomUUID()}`, 160);
    return {
      id,
      kind: "prop",
      name: text(source.name, `道具${index + 1}`),
      shape: source.shape === "sphere" || source.shape === "cylinder" ? source.shape : "box",
      position: vector(source.position, [0, .5, 0]),
      rotation: vector(source.rotation, [0, 0, 0]),
      scale: vector(source.scale, [1, 1, 1]).map((entry) => bounded(entry, 1, .01, 100)) as DirectorVector3,
      color: color(source.color, "#7A8490"),
      visible: boolean(source.visible, true),
      locked: boolean(source.locked, false),
      ...(typeof source.referenceAttachmentId === "string" ? { referenceAttachmentId: source.referenceAttachmentId.slice(0, 160) } : {}),
    };
  }
  return null;
}

export function normalizeDirectorScene(value: unknown): DirectorSceneState {
  const fallback = createDefaultDirectorScene();
  if (!value || typeof value !== "object") return fallback;
  const source = value as Partial<DirectorSceneState>;
  if (source.schema !== "labutv-director/v1" || !Array.isArray(source.objects)) return fallback;
  const objects = source.objects.slice(0, 100).map(normalizeObject).filter((item): item is DirectorSceneState["objects"][number] => Boolean(item));
  const cameras = objects.filter((item): item is DirectorCamera => item.kind === "camera");
  if (!cameras.length) objects.unshift(fallback.objects[0]);
  const sceneSource: Partial<DirectorSceneState["scene"]> = source.scene && typeof source.scene === "object" ? source.scene : {};
  const timelineSource = source.timeline && typeof source.timeline === "object" ? source.timeline as Partial<DirectorSceneState["timeline"]> & { trackObjectIds?: unknown } : {};
  const timelineDuration = bounded(timelineSource.duration, fallback.timeline.duration, .5, 120);
  const objectIds = new Set(objects.map((item) => item.id));
  const objectById = new Map(objects.map((item) => [item.id, item]));
  const normalizedTracks = Array.isArray(timelineSource.tracks) ? timelineSource.tracks.slice(0, 100).flatMap((track) => {
    if (!track || typeof track !== "object") return [];
    const sourceTrack = track as Record<string, unknown>;
    const objectId = typeof sourceTrack.objectId === "string" && objectIds.has(sourceTrack.objectId) ? sourceTrack.objectId : "";
    if (!objectId) return [];
    const object = objectById.get(objectId)!;
    const keyframes = Array.isArray(sourceTrack.keyframes) ? sourceTrack.keyframes.slice(0, 200).flatMap((frame, frameIndex) => {
      if (!frame || typeof frame !== "object") return [];
      const sourceFrame = frame as Record<string, unknown>;
      return [{
        id: text(sourceFrame.id, `keyframe-${objectId}-${frameIndex}`, 160),
        time: bounded(sourceFrame.time, 0, 0, timelineDuration),
        position: vector(sourceFrame.position, object.position),
        rotation: vector(sourceFrame.rotation, object.rotation),
        scale: vector(sourceFrame.scale, object.scale).map((entry) => bounded(entry, 1, .01, 100)) as DirectorVector3,
      }];
    }).sort((left, right) => left.time - right.time) : [];
    return [{ objectId, keyframes }];
  }) : Array.isArray(timelineSource.trackObjectIds) ? (timelineSource.trackObjectIds as unknown[]).flatMap((id) => {
    if (typeof id !== "string" || !objectIds.has(id)) return [];
    const object = objectById.get(id)!;
    return [{ objectId: id, keyframes: [{ id: `keyframe-${crypto.randomUUID()}`, time: 0, position: object.position, rotation: object.rotation, scale: object.scale }] }];
  }) : [];
  const aspectRatio = ASPECTS.has(source.aspectRatio ?? "") ? source.aspectRatio! : fallback.aspectRatio;
  return {
    schema: "labutv-director/v1",
    panel: PANELS.has(source.panel ?? "") ? source.panel! : fallback.panel,
    tool: TOOLS.has(source.tool ?? "") ? source.tool! : fallback.tool,
    viewMode: VIEW_MODES.has(source.viewMode ?? "") ? source.viewMode! : fallback.viewMode,
    aspectRatio,
    compositionGuide: aspectRatio === "adaptive" ? false : boolean(source.compositionGuide, false),
    objects,
    timeline: {
      duration: timelineDuration,
      head: bounded(timelineSource.head, fallback.timeline.head, 0, timelineDuration),
      loop: boolean(timelineSource.loop, fallback.timeline.loop),
      autoFrame: boolean(timelineSource.autoFrame, fallback.timeline.autoFrame),
      tracks: normalizedTracks.filter((track, index) => normalizedTracks.findIndex((candidate) => candidate.objectId === track.objectId) === index),
    },
    activeCameraId: objects.some((item) => item.kind === "camera" && item.id === source.activeCameraId) ? source.activeCameraId ?? null : (objects.find((item) => item.kind === "camera")?.id ?? null),
    selectedObjectId: source.selectedObjectId === null ? null : objects.some((item) => item.id === source.selectedObjectId) ? source.selectedObjectId ?? null : (objects.find((item) => item.kind === "actor")?.id ?? objects[0]?.id ?? null),
    scene: {
      position: vector(sceneSource.position, fallback.scene.position),
      rotation: vector(sceneSource.rotation, fallback.scene.rotation),
      scale: bounded(sceneSource.scale, fallback.scene.scale, .1, 5),
      skyColor: color(sceneSource.skyColor, fallback.scene.skyColor),
      panoramaAttachmentId: typeof sceneSource.panoramaAttachmentId === "string" ? sceneSource.panoramaAttachmentId.slice(0, 160) : null,
      panoramaRotation: bounded(sceneSource.panoramaRotation, 0, -180, 180),
      panoramaRadius: bounded(sceneSource.panoramaRadius, 60, 10, 120),
      showLabels: boolean(sceneSource.showLabels, true),
      gridSnap: boolean(sceneSource.gridSnap, false),
      groundSnap: boolean(sceneSource.groundSnap, true),
      showGround: boolean(sceneSource.showGround, true),
      groundOpacity: bounded(sceneSource.groundOpacity, .4, 0, 1),
      groundHeight: bounded(sceneSource.groundHeight, 0, -5, 5),
    },
  };
}

export function cameraPresetValues(preset: string) {
  return CAMERA_PRESET_VALUES[preset] ?? CAMERA_PRESET_VALUES["正面中景"];
}

export function buildDirectorSceneFromPrompt(prompt: string, current: DirectorSceneState): DirectorSceneState {
  const text = prompt.trim().toLocaleLowerCase();
  if (!text) return current;
  let objects = [...current.objects];
  let actors = objects.filter((item): item is DirectorActor => item.kind === "actor");
  let desiredActors: number | null = null;
  if (/单人|一人|一名|1\s*(?:人|名)/.test(text)) desiredActors = 1;
  else if (/双人|两人|两名|二人|2\s*(?:人|名)|一男一女/.test(text)) desiredActors = 2;
  else if (/三人|三名|3\s*(?:人|名)/.test(text)) desiredActors = 3;
  else if (/群像|人群|群众|九人|9\s*(?:人|名)/.test(text)) desiredActors = 0;
  const archetype: DirectorActorArchetype = /女孩|女性|女人|女主/.test(text)
    ? "standard-female"
    : /儿童|孩子|小孩/.test(text)
      ? "child"
      : /少年|学生/.test(text)
        ? "teen"
        : /健硕|肌肉|壮汉/.test(text)
          ? "strong"
          : "standard-male";
  if (desiredActors === 0) {
    objects = objects.filter((item) => item.kind !== "actor");
    actors = [];
  }
  while (desiredActors !== null && desiredActors > 0 && actors.length < desiredActors) {
    const actor = createDirectorActor(actors.length, actors.length === 0 ? archetype : /女性|女孩/.test(text) && actors.length === 1 ? "standard-female" : archetype);
    actors.push(actor);
    objects.push(actor);
  }
  if (desiredActors !== null && desiredActors > 0 && actors.length > desiredActors) {
    const removedIds = new Set(actors.slice(desiredActors).map((actor) => actor.id));
    objects = objects.filter((item) => !removedIds.has(item.id));
    actors = actors.slice(0, desiredActors);
  }
  if (/人群|群众|九人/.test(text) && !objects.some((item) => item.kind === "actor" && item.archetype === "crowd")) {
    const crowd = createDirectorActor(actors.length, "crowd");
    actors.push(crowd);
    objects.push(crowd);
  }
  const archetypeExplicit = /女孩|女性|女人|女主|男性|男人|男主|一男一女|儿童|孩子|小孩|少年|学生|健硕|肌肉|壮汉/.test(text);
  if (archetypeExplicit) {
    objects = objects.map((item) => item.kind === "actor" ? {
      ...item,
      archetype: /一男一女/.test(text)
        ? (actors.findIndex((actor) => actor.id === item.id) === 1 ? "standard-female" : "standard-male")
        : archetype,
    } : item);
    actors = objects.filter((item): item is DirectorActor => item.kind === "actor");
  }
  const cameraPreset = /荷兰角/.test(text) ? "荷兰角"
    : /过肩镜头（右）|右过肩/.test(text) ? "过肩镜头（右）"
      : /过肩/.test(text) ? "过肩镜头"
        : /鸟瞰|顶视/.test(text) ? "鸟瞰"
          : /45[°度]\s*俯拍/.test(text) ? "45° 俯拍"
            : /俯拍全景/.test(text) ? "俯拍全景"
              : /俯拍/.test(text) ? "45° 俯拍"
                : /低角度广角/.test(text) ? "低角度广角"
                  : /仰拍|低角度/.test(text) ? "低角度仰拍"
                    : /正面全景/.test(text) ? "正面全景"
                      : /正面特写|特写|近脸/.test(text) ? "正面特写"
                        : /正面中景/.test(text) ? "正面中景"
                          : /侧面跟拍|跟拍/.test(text) ? "侧面跟拍"
                            : /侧面近景|侧面|侧拍/.test(text) ? "侧面近景"
                              : /背面|背影/.test(text) ? "背面中景"
                                : null;
  const cameras = objects.filter((item): item is DirectorCamera => item.kind === "camera");
  const activeCamera = cameras.find((item) => item.id === current.activeCameraId) ?? cameras[0];
  if (activeCamera && cameraPreset) {
    const preset = cameraPresetValues(cameraPreset);
    objects = objects.map((item) => item.id === activeCamera.id ? {
      ...item,
      position: preset.position,
      rotation: preset.rotation,
      fov: preset.fov,
      followTargetId: null,
      followOffset: null,
      lookAtMode: "rotation" as const,
      lookAtTargetId: null,
    } : item);
  }
  if (cameraPreset === "侧面跟拍" || cameraPreset === "侧面近景") {
    const stagedActors = objects.filter((item): item is DirectorActor => item.kind === "actor");
    const middle = (stagedActors.length - 1) / 2;
    const positions = new Map(stagedActors.map((actor, index) => [actor.id, [
      Number(((index - middle) * .34).toFixed(2)),
      actor.position[1],
      Number(((index - middle) * 1.25).toFixed(2)),
    ] as DirectorVector3]));
    objects = objects.map((item) => item.kind === "actor" && positions.has(item.id) ? { ...item, position: positions.get(item.id)! } : item);
  }
  const actorIds = objects.filter((item) => item.kind === "actor").map((item) => item.id);
  const posePreset: DirectorPosePreset = /奔跑|跑步|追逐/.test(text) ? "run"
    : /行走|走路/.test(text) ? "walk"
      : /坐下|坐在|坐姿/.test(text) ? "sit"
        : /战斗|格斗|对打/.test(text) ? "fight"
          : /招手/.test(text) ? "wave"
            : "stand";
  objects = objects.map((item) => actorIds.includes(item.id) && item.kind === "actor" ? { ...item, posePreset } : item);
  const skyColor = /夜晚|夜景|星空|月光/.test(text) ? "#050711"
    : /黄昏|夕阳|日落/.test(text) ? "#2A1515"
      : /白天|日光|晴天/.test(text) ? "#647A91"
        : current.scene.skyColor;
  const aspectRatio = /竖屏|9[:：]16/.test(text) ? "9:16"
    : /3[:：]4/.test(text) ? "3:4"
    : /方形|1[:：]1/.test(text) ? "1:1"
      : /宽银幕|21[:：]9/.test(text) ? "21:9"
        : /4[:：]3/.test(text) ? "4:3"
          : /横屏|16[:：]9/.test(text) ? "16:9"
        : current.aspectRatio;
  const validObjectIds = new Set(objects.map((item) => item.id));
  objects = objects.map((item) => item.kind === "camera" ? {
    ...item,
    followTargetId: item.followTargetId && validObjectIds.has(item.followTargetId) ? item.followTargetId : null,
    followOffset: item.followTargetId && validObjectIds.has(item.followTargetId) ? item.followOffset : null,
    lookAtTargetId: item.lookAtTargetId && validObjectIds.has(item.lookAtTargetId) ? item.lookAtTargetId : null,
    lookAtMode: item.lookAtMode === "object" && (!item.lookAtTargetId || !validObjectIds.has(item.lookAtTargetId)) ? "rotation" as const : item.lookAtMode,
  } : item);
  return {
    ...current,
    objects,
    aspectRatio,
    activeCameraId: activeCamera?.id ?? current.activeCameraId,
    selectedObjectId: actors[0]?.id ?? current.selectedObjectId,
    scene: { ...current.scene, skyColor },
    timeline: { ...current.timeline, tracks: current.timeline.tracks.filter((track) => validObjectIds.has(track.objectId)) },
  };
}
