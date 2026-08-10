export type DirectorVector3 = [number, number, number];

export type DirectorTool = "select" | "translate" | "rotate" | "scale";
export type DirectorViewMode = "director" | "camera";
export type DirectorAspectRatio = "adaptive" | "21:9" | "16:9" | "4:3" | "1:1" | "3:4" | "9:16";
export type DirectorPanel = "scene" | "actors" | "cameras" | "panorama" | "ratio";
export type DirectorActorArchetype =
  | "standard-male"
  | "standard-female"
  | "strong"
  | "slim"
  | "teen"
  | "child"
  | "broad"
  | "chibi"
  | "crowd"
  | "geometry";

export type DirectorPosePreset =
  | "stand"
  | "t-pose"
  | "walk"
  | "run"
  | "sit"
  | "squat"
  | "kneel-one"
  | "kneel-two"
  | "hands-hips"
  | "lean"
  | "bow"
  | "think"
  | "fight"
  | "kick"
  | "throw"
  | "push"
  | "wave"
  | "reach"
  | "arms-crossed"
  | "phone";

export type DirectorPoseKey =
  | "bodyPitch"
  | "bodyTurn"
  | "bodyRoll"
  | "torsoPitch"
  | "torsoTwist"
  | "torsoRoll"
  | "headPitch"
  | "headTurn"
  | "headRoll"
  | "leftShoulderPitch"
  | "leftShoulderOut"
  | "leftShoulderTwist"
  | "rightShoulderPitch"
  | "rightShoulderOut"
  | "rightShoulderTwist"
  | "leftElbow"
  | "rightElbow"
  | "leftHipPitch"
  | "leftHipOut"
  | "leftHipTwist"
  | "rightHipPitch"
  | "rightHipOut"
  | "rightHipTwist"
  | "leftKnee"
  | "rightKnee";

export type DirectorPose = Record<DirectorPoseKey, number>;

export type DirectorShot = {
  id: string;
  name: string;
  attachmentId: string;
  mimeType: string;
  width: number;
  height: number;
  createdAt: string;
};

type DirectorObjectBase = {
  id: string;
  name: string;
  position: DirectorVector3;
  rotation: DirectorVector3;
  scale: DirectorVector3;
  color: string;
  visible: boolean;
  locked: boolean;
};

export type DirectorActor = DirectorObjectBase & {
  kind: "actor";
  archetype: DirectorActorArchetype;
  posePreset: DirectorPosePreset;
  pose: DirectorPose;
};

export type DirectorCamera = DirectorObjectBase & {
  kind: "camera";
  fov: number;
  followTargetId: string | null;
  followOffset: DirectorVector3 | null;
  lookAtMode: "rotation" | "point" | "object";
  lookAtTargetId: string | null;
  lookAt: DirectorVector3;
  shots: DirectorShot[];
};

export type DirectorProp = DirectorObjectBase & {
  kind: "prop";
  shape: "box" | "sphere" | "cylinder";
  referenceAttachmentId?: string;
};

export type DirectorObject = DirectorActor | DirectorCamera | DirectorProp;

export type DirectorSceneSettings = {
  position: DirectorVector3;
  rotation: DirectorVector3;
  scale: number;
  skyColor: string;
  panoramaAttachmentId: string | null;
  panoramaRotation: number;
  panoramaRadius: number;
  showLabels: boolean;
  gridSnap: boolean;
  groundSnap: boolean;
  showGround: boolean;
  groundOpacity: number;
  groundHeight: number;
};

export type DirectorTimelineState = {
  duration: number;
  head: number;
  loop: boolean;
  autoFrame: boolean;
  tracks: Array<{
    objectId: string;
    keyframes: Array<{
      id: string;
      time: number;
      position: DirectorVector3;
      rotation: DirectorVector3;
      scale: DirectorVector3;
    }>;
  }>;
};

export type DirectorSceneState = {
  schema: "labutv-director/v1";
  panel: DirectorPanel;
  tool: DirectorTool;
  viewMode: DirectorViewMode;
  aspectRatio: DirectorAspectRatio;
  compositionGuide: boolean;
  selectedObjectId: string | null;
  activeCameraId: string | null;
  objects: DirectorObject[];
  scene: DirectorSceneSettings;
  timeline: DirectorTimelineState;
};

export type DirectorCaptureResult = {
  blob: Blob;
  width: number;
  height: number;
  cameraPosition: DirectorVector3;
  cameraRotation: DirectorVector3;
  fov: number;
};

export type DirectorViewportHandle = {
  capture: (aspectRatio: DirectorAspectRatio, cameraId?: string) => Promise<DirectorCaptureResult>;
  getCurrentView: () => Pick<DirectorCaptureResult, "cameraPosition" | "cameraRotation" | "fov"> | null;
  resetView: () => void;
  setAxisView: (view: "front" | "top" | "right") => void;
};
