import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  type MutableRefObject,
} from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import type {
  DirectorActor,
  DirectorAspectRatio,
  DirectorCamera,
  DirectorCaptureResult,
  DirectorObject,
  DirectorSceneState,
  DirectorVector3,
  DirectorViewportHandle,
} from "./types";

type DirectorViewportProps = {
  value: DirectorSceneState;
  panoramaUrl?: string;
  referenceUrls?: Readonly<Record<string, string>>;
  onSelect: (objectId: string | null) => void;
  onTransform: (objectId: string, patch: Pick<DirectorObject, "position" | "rotation" | "scale">) => void;
  onWebglError?: (message: string) => void;
};

type ViewportRuntime = {
  disposed: boolean;
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  world: THREE.Group;
  directorCamera: THREE.PerspectiveCamera;
  orbit: OrbitControls;
  transform: TransformControls;
  transformHelper: THREE.Object3D;
  grid: THREE.GridHelper;
  ground: THREE.Mesh;
  objects: Map<string, THREE.Object3D>;
  cameraHelpers: Map<string, THREE.CameraHelper>;
  resizeObserver: ResizeObserver;
  disposePointerHandlers: () => void;
};

const toRadians = THREE.MathUtils.degToRad;
const toDegrees = THREE.MathUtils.radToDeg;

function disposeObject(root: THREE.Object3D) {
  root.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry.dispose();
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.forEach((material) => {
        if (material instanceof THREE.MeshStandardMaterial || material instanceof THREE.MeshBasicMaterial) material.map?.dispose();
        material.dispose();
      });
    }
    if (child instanceof THREE.Sprite) {
      child.material.map?.dispose();
      child.material.dispose();
    }
  });
}

function disposeMaterial(value: THREE.Material | THREE.Material[]) {
  (Array.isArray(value) ? value : [value]).forEach((entry) => entry.dispose());
}

function renderScene(runtime: ViewportRuntime, camera: THREE.PerspectiveCamera, gizmoCamera = camera, hideAllCameraGizmos = false) {
  const cameraChildren = hideAllCameraGizmos
    ? [...runtime.objects.values()].flatMap((object) => object instanceof THREE.PerspectiveCamera ? object.children : [])
    : gizmoCamera.children;
  const childVisibility = cameraChildren.map((child) => child.visible);
  cameraChildren.forEach((child) => { child.visible = false; });
  try {
    runtime.renderer.render(runtime.scene, camera);
  } finally {
    cameraChildren.forEach((child, index) => { child.visible = childVisibility[index] ?? true; });
  }
}

function material(color: string, roughness = .56) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: .08 });
}

function capsule(radius: number, length: number, color: string) {
  const mesh = new THREE.Mesh(new THREE.CapsuleGeometry(radius, length, 7, 12), material(color));
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function joint(name: string) {
  const group = new THREE.Group();
  group.name = name;
  return group;
}

function makeLabel(text: string, color: string) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  if (context) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.font = "600 28px Inter, PingFang SC, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.lineWidth = 6;
    context.strokeStyle = "rgba(0,0,0,.72)";
    context.strokeText(text, 128, 32);
    context.fillStyle = color;
    context.fillText(text, 128, 32);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false }));
  sprite.name = "object-label";
  sprite.scale.set(.5, .12, 1);
  sprite.position.set(0, 2.62, 0);
  sprite.renderOrder = 20;
  return sprite;
}

function actorDimensions(actor: DirectorActor) {
  switch (actor.archetype) {
    case "strong": return { width: 1.24, height: 1.04, head: 1.04 };
    case "slim": return { width: .78, height: 1.08, head: .94 };
    case "teen": return { width: .82, height: .9, head: 1.02 };
    case "child": return { width: .72, height: .72, head: 1.18 };
    case "broad": return { width: 1.34, height: .98, head: 1.08 };
    case "chibi": return { width: .92, height: .58, head: 1.58 };
    case "standard-female": return { width: .84, height: 1, head: .96 };
    default: return { width: 1, height: 1, head: 1 };
  }
}

function createSingleActor(actor: DirectorActor, suffix = "") {
  const root = new THREE.Group();
  root.name = `actor-root${suffix}`;
  const dims = actorDimensions(actor);
  const body = joint("body");
  root.add(body);

  const pelvis = capsule(.24 * dims.width, .22 * dims.height, actor.color);
  pelvis.name = "pelvis";
  pelvis.rotation.z = Math.PI / 2;
  pelvis.position.y = .83 * dims.height;
  body.add(pelvis);

  const torso = joint("torso");
  torso.position.y = .95 * dims.height;
  const torsoMesh = capsule(.31 * dims.width, .55 * dims.height, actor.color);
  torsoMesh.name = "torso-mesh";
  torsoMesh.position.y = .34 * dims.height;
  torso.add(torsoMesh);
  body.add(torso);

  const head = joint("head");
  head.position.y = 1.83 * dims.height;
  const headMesh = new THREE.Mesh(new THREE.SphereGeometry(.23 * dims.head, 20, 16), material(actor.color, .5));
  headMesh.castShadow = true;
  headMesh.name = "head-mesh";
  head.add(headMesh);
  body.add(head);

  const addArm = (side: "left" | "right") => {
    const direction = side === "left" ? -1 : 1;
    const shoulder = joint(`${side}-shoulder`);
    shoulder.position.set(direction * .4 * dims.width, 1.57 * dims.height, 0);
    const upper = capsule(.11 * dims.width, .36 * dims.height, actor.color);
    upper.position.y = -.25 * dims.height;
    shoulder.add(upper);
    const elbow = joint(`${side}-elbow`);
    elbow.position.y = -.53 * dims.height;
    const forearm = capsule(.095 * dims.width, .34 * dims.height, actor.color);
    forearm.position.y = -.23 * dims.height;
    elbow.add(forearm);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(.12 * dims.width, 12, 10), material(actor.color));
    hand.position.y = -.48 * dims.height;
    elbow.add(hand);
    shoulder.add(elbow);
    body.add(shoulder);
  };
  addArm("left");
  addArm("right");

  const addLeg = (side: "left" | "right") => {
    const direction = side === "left" ? -1 : 1;
    const hip = joint(`${side}-hip`);
    hip.position.set(direction * .17 * dims.width, .76 * dims.height, 0);
    const thigh = capsule(.135 * dims.width, .46 * dims.height, actor.color);
    thigh.position.y = -.3 * dims.height;
    hip.add(thigh);
    const knee = joint(`${side}-knee`);
    knee.position.y = -.62 * dims.height;
    const shin = capsule(.115 * dims.width, .45 * dims.height, actor.color);
    shin.position.y = -.3 * dims.height;
    knee.add(shin);
    const foot = new THREE.Mesh(new THREE.BoxGeometry(.24 * dims.width, .14 * dims.height, .42), material(actor.color));
    foot.position.set(0, -.58 * dims.height, .09);
    foot.castShadow = true;
    knee.add(foot);
    hip.add(knee);
    body.add(hip);
  };
  addLeg("left");
  addLeg("right");
  root.add(makeLabel(actor.name, "#f4f4f4"));
  return root;
}

function createActorObject(actor: DirectorActor) {
  const root = new THREE.Group();
  root.userData.objectId = actor.id;
  root.userData.objectKind = actor.kind;
  root.userData.archetype = actor.archetype;
  if (actor.archetype === "crowd") {
    for (let z = -1; z <= 1; z += 1) for (let x = -1; x <= 1; x += 1) {
      const person = createSingleActor({ ...actor, name: "" }, `-${x}-${z}`);
      person.position.set(x * 1.05, 0, z * .9);
      person.scale.setScalar(.72);
      const unusedLabel = person.getObjectByName("object-label");
      if (unusedLabel) {
        unusedLabel.removeFromParent();
        disposeObject(unusedLabel);
      }
      root.add(person);
    }
    root.add(makeLabel(actor.name, "#f4f4f4"));
  } else if (actor.archetype === "geometry") {
    const geometry = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), material(actor.color));
    geometry.position.y = .5;
    geometry.castShadow = true;
    root.add(geometry, makeLabel(actor.name, "#f4f4f4"));
  } else {
    root.add(createSingleActor(actor));
  }
  return root;
}

function poseDelta(preset: DirectorActor["posePreset"]): Partial<Record<string, [number, number, number]>> {
  switch (preset) {
    case "t-pose": return { "left-shoulder": [0, 0, -90], "right-shoulder": [0, 0, 90], "left-elbow": [0, 0, 0], "right-elbow": [0, 0, 0] };
    case "walk": return { "left-shoulder": [28, 0, 4], "right-shoulder": [-28, 0, -4], "left-hip": [-22, 0, 0], "right-hip": [25, 0, 0], "left-knee": [18, 0, 0] };
    case "run": return { body: [14, 0, 0], "left-shoulder": [55, 0, 10], "right-shoulder": [-55, 0, -10], "left-hip": [-42, 0, 0], "right-hip": [48, 0, 0], "left-knee": [68, 0, 0], "right-knee": [28, 0, 0] };
    case "sit": return { body: [-4, 0, 0], "left-hip": [-78, 0, 0], "right-hip": [-78, 0, 0], "left-knee": [82, 0, 0], "right-knee": [82, 0, 0] };
    case "squat": return { body: [14, 0, 0], "left-hip": [-55, 0, 8], "right-hip": [-55, 0, -8], "left-knee": [100, 0, 0], "right-knee": [100, 0, 0] };
    case "kneel-one": return { "left-hip": [-68, 0, 0], "left-knee": [115, 0, 0], "right-knee": [75, 0, 0] };
    case "kneel-two": return { "left-hip": [-35, 0, 0], "right-hip": [-35, 0, 0], "left-knee": [120, 0, 0], "right-knee": [120, 0, 0] };
    case "hands-hips": return { "left-shoulder": [0, 0, -42], "right-shoulder": [0, 0, 42], "left-elbow": [75, 0, 0], "right-elbow": [75, 0, 0] };
    case "lean": return { body: [0, 0, -16], torso: [0, 0, -8] };
    case "bow": return { body: [42, 0, 0], torso: [16, 0, 0], head: [-20, 0, 0] };
    case "think": return { "right-shoulder": [-48, 0, 18], "right-elbow": [112, 0, 0], head: [-8, -12, 0] };
    case "fight": return { body: [8, 24, 0], "left-shoulder": [-55, 0, -24], "right-shoulder": [-42, 0, 30], "left-elbow": [85, 0, 0], "right-elbow": [95, 0, 0] };
    case "kick": return { body: [4, 0, -8], "right-hip": [68, 0, 0], "left-knee": [18, 0, 0] };
    case "throw": return { body: [-8, -18, 0], "right-shoulder": [-125, 0, 24], "right-elbow": [55, 0, 0] };
    case "push": return { body: [12, 0, 0], "left-shoulder": [-88, 0, -8], "right-shoulder": [-88, 0, 8] };
    case "wave": return { "right-shoulder": [0, 0, 125], "right-elbow": [64, 0, 0] };
    case "reach": return { "right-shoulder": [-94, 0, 8], "right-elbow": [8, 0, 0] };
    case "arms-crossed": return { "left-shoulder": [-42, 0, -34], "right-shoulder": [-42, 0, 34], "left-elbow": [105, 0, 0], "right-elbow": [105, 0, 0] };
    case "phone": return { "left-shoulder": [-28, 0, -12], "right-shoulder": [-28, 0, 12], "left-elbow": [92, 0, 0], "right-elbow": [92, 0, 0], head: [-14, 0, 0] };
    default: return {};
  }
}

function setJointRotation(root: THREE.Object3D, name: string, rotation: DirectorVector3, delta?: DirectorVector3) {
  const target = root.getObjectByName(name);
  if (!target) return;
  target.rotation.set(
    toRadians(rotation[0] + (delta?.[0] ?? 0)),
    toRadians(rotation[1] + (delta?.[1] ?? 0)),
    toRadians(rotation[2] + (delta?.[2] ?? 0)),
  );
}

function applyActorPose(root: THREE.Object3D, actor: DirectorActor) {
  if (actor.archetype === "crowd") {
    root.children.filter((child) => child.name.startsWith("actor-root-")).forEach((person) => applyActorPose(person, { ...actor, archetype: "standard-male" }));
    return;
  }
  const p = actor.pose;
  const d = poseDelta(actor.posePreset);
  setJointRotation(root, "body", [p.bodyPitch, p.bodyTurn, p.bodyRoll], d.body);
  setJointRotation(root, "torso", [p.torsoPitch, p.torsoTwist, p.torsoRoll], d.torso);
  setJointRotation(root, "head", [p.headPitch, p.headTurn, p.headRoll], d.head);
  setJointRotation(root, "left-shoulder", [p.leftShoulderPitch, p.leftShoulderTwist, -p.leftShoulderOut], d["left-shoulder"]);
  setJointRotation(root, "right-shoulder", [p.rightShoulderPitch, p.rightShoulderTwist, p.rightShoulderOut], d["right-shoulder"]);
  setJointRotation(root, "left-elbow", [p.leftElbow, 0, 0], d["left-elbow"]);
  setJointRotation(root, "right-elbow", [p.rightElbow, 0, 0], d["right-elbow"]);
  setJointRotation(root, "left-hip", [p.leftHipPitch, p.leftHipTwist, -p.leftHipOut], d["left-hip"]);
  setJointRotation(root, "right-hip", [p.rightHipPitch, p.rightHipTwist, p.rightHipOut], d["right-hip"]);
  setJointRotation(root, "left-knee", [p.leftKnee, 0, 0], d["left-knee"]);
  setJointRotation(root, "right-knee", [p.rightKnee, 0, 0], d["right-knee"]);
}

function createCameraObject(camera: DirectorCamera) {
  const object = new THREE.PerspectiveCamera(camera.fov, 16 / 9, .05, 200);
  object.userData.objectId = camera.id;
  object.userData.objectKind = camera.kind;
  const body = new THREE.Mesh(new THREE.BoxGeometry(.44, .28, .5), material("#2d333a"));
  body.position.z = .08;
  body.castShadow = true;
  const lens = new THREE.Mesh(new THREE.CylinderGeometry(.12, .17, .24, 16), material("#59616a"));
  lens.rotation.x = Math.PI / 2;
  lens.position.z = -.32;
  object.add(body, lens);
  return object;
}

function createPropObject(object: Extract<DirectorObject, { kind: "prop" }>) {
  const geometry = object.referenceAttachmentId
    ? new THREE.PlaneGeometry(1, 1)
    : object.shape === "sphere"
    ? new THREE.SphereGeometry(.5, 20, 16)
    : object.shape === "cylinder"
      ? new THREE.CylinderGeometry(.45, .45, 1, 20)
      : new THREE.BoxGeometry(1, 1, 1);
  const root = new THREE.Group();
  root.userData.objectId = object.id;
  root.userData.objectKind = object.kind;
  const meshMaterial = material(object.color);
  if (object.referenceAttachmentId) meshMaterial.side = THREE.DoubleSide;
  const mesh = new THREE.Mesh(geometry, meshMaterial);
  mesh.name = "prop-surface";
  mesh.position.y = object.referenceAttachmentId ? 0 : .5;
  mesh.castShadow = !object.referenceAttachmentId;
  mesh.receiveShadow = true;
  root.add(mesh, makeLabel(object.name, "#f4f4f4"));
  return root;
}

function createSceneObject(object: DirectorObject) {
  return object.kind === "actor" ? createActorObject(object) : object.kind === "camera" ? createCameraObject(object) : createPropObject(object);
}

function updateObject(root: THREE.Object3D, object: DirectorObject, showLabels: boolean) {
  root.position.fromArray(object.position);
  root.rotation.set(toRadians(object.rotation[0]), toRadians(object.rotation[1]), toRadians(object.rotation[2]));
  root.scale.fromArray(object.scale);
  root.visible = object.visible;
  root.userData.locked = object.locked;
  let label = root.getObjectByName("object-label");
  if (object.kind === "camera") {
    if (label) {
      label.removeFromParent();
      disposeObject(label);
      label = undefined;
    }
    root.userData.labelName = undefined;
  } else {
    if (!label || root.userData.labelName !== object.name) {
      if (label) {
        label.removeFromParent();
        disposeObject(label);
      }
      label = makeLabel(object.name, "#f4f4f4");
      root.add(label);
      root.userData.labelName = object.name;
    }
    label.visible = showLabels;
  }
  if (object.kind === "actor") applyActorPose(root, object);
  if (object.kind === "camera" && root instanceof THREE.PerspectiveCamera) {
    root.fov = object.fov;
    root.updateProjectionMatrix();
  }
  root.traverse((child) => {
    if (!(child instanceof THREE.Mesh) || !(child.material instanceof THREE.MeshStandardMaterial)) return;
    if (object.kind !== "camera") child.material.color.set(object.kind === "prop" && object.referenceAttachmentId && child.material.map ? "#ffffff" : object.color);
  });
}

function applyReferenceTextures(runtime: ViewportRuntime, value: DirectorSceneState, urls: Readonly<Record<string, string>>) {
  value.objects.forEach((object) => {
    if (object.kind !== "prop" || !object.referenceAttachmentId) return;
    const root = runtime.objects.get(object.id);
    const mesh = root?.getObjectByName("prop-surface");
    if (!(mesh instanceof THREE.Mesh) || !(mesh.material instanceof THREE.MeshStandardMaterial)) return;
    const url = urls[object.id] ?? "";
    if (root!.userData.referenceUrl === url) return;
    root!.userData.referenceUrl = url;
    root!.userData.referenceLoadFailed = false;
    mesh.material.map?.dispose();
    mesh.material.map = null;
    mesh.material.color.set(object.color);
    mesh.material.needsUpdate = true;
    if (!url) return;
    new THREE.TextureLoader().load(url, (texture) => {
      if (runtime.disposed || runtime.objects.get(object.id) !== root || root!.userData.referenceUrl !== url) {
        texture.dispose();
        return;
      }
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = Math.min(8, runtime.renderer.capabilities.getMaxAnisotropy());
      mesh.material.map?.dispose();
      mesh.material.map = texture;
      mesh.material.color.set("#ffffff");
      mesh.material.needsUpdate = true;
    }, undefined, () => {
      if (root!.userData.referenceUrl === url) root!.userData.referenceLoadFailed = true;
    });
  });
}

function adaptiveAspect(container: HTMLElement) {
  return Math.max(.4, Math.min(2.4, container.clientWidth / Math.max(1, container.clientHeight)));
}

function outputSize(aspect: DirectorAspectRatio, container: HTMLElement) {
  if (aspect === "adaptive") {
    const ratio = adaptiveAspect(container);
    return ratio >= 1 ? { width: 1920, height: Math.round(1920 / ratio) } : { width: Math.round(1280 * ratio), height: 1280 };
  }
  const ratios: Record<Exclude<DirectorAspectRatio, "adaptive">, number> = { "21:9": 21 / 9, "16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1, "3:4": 3 / 4, "9:16": 9 / 16 };
  const ratio = ratios[aspect];
  return ratio >= 1 ? { width: 2276, height: Math.round(2276 / ratio) } : { width: Math.round(1280 * ratio), height: 1280 };
}

function aspectValue(aspect: DirectorAspectRatio, container: HTMLElement) {
  if (aspect === "adaptive") return adaptiveAspect(container);
  const ratios: Record<Exclude<DirectorAspectRatio, "adaptive">, number> = { "21:9": 21 / 9, "16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1, "3:4": 3 / 4, "9:16": 9 / 16 };
  return ratios[aspect];
}

function viewportBounds(aspect: DirectorAspectRatio, container: HTMLElement) {
  const width = Math.max(1, container.clientWidth);
  const height = Math.max(1, container.clientHeight);
  const ratio = aspectValue(aspect, container);
  let viewportWidth = width;
  let viewportHeight = Math.round(viewportWidth / ratio);
  if (viewportHeight > height) {
    viewportHeight = height;
    viewportWidth = Math.round(viewportHeight * ratio);
  }
  return {
    x: Math.floor((width - viewportWidth) / 2),
    y: Math.floor((height - viewportHeight) / 2),
    width: viewportWidth,
    height: viewportHeight,
    ratio,
  };
}

function vectorFromEuler(euler: THREE.Euler): DirectorVector3 {
  return [Number(toDegrees(euler.x).toFixed(2)), Number(toDegrees(euler.y).toFixed(2)), Number(toDegrees(euler.z).toFixed(2))];
}

function runtimeCamera(runtime: ViewportRuntime, value: DirectorSceneState) {
  if (value.viewMode === "camera" && value.activeCameraId) {
    const camera = runtime.objects.get(value.activeCameraId);
    if (camera instanceof THREE.PerspectiveCamera) return camera;
  }
  return runtime.directorCamera;
}

function persistedCameraPose(runtime: ViewportRuntime, camera: THREE.PerspectiveCamera) {
  runtime.world.updateMatrixWorld(true);
  camera.updateMatrixWorld(true);
  const worldPosition = new THREE.Vector3();
  const worldQuaternion = new THREE.Quaternion();
  const worldGroupQuaternion = new THREE.Quaternion();
  camera.getWorldPosition(worldPosition);
  camera.getWorldQuaternion(worldQuaternion);
  runtime.world.getWorldQuaternion(worldGroupQuaternion);
  const localPosition = runtime.world.worldToLocal(worldPosition.clone());
  const localQuaternion = worldGroupQuaternion.invert().multiply(worldQuaternion);
  return {
    position: [Number(localPosition.x.toFixed(2)), Number(localPosition.y.toFixed(2)), Number(localPosition.z.toFixed(2))] as DirectorVector3,
    rotation: vectorFromEuler(new THREE.Euler(0, 0, 0, "XYZ").setFromQuaternion(localQuaternion)),
    fov: camera.fov,
  };
}

export const DirectorViewport = forwardRef<DirectorViewportHandle, DirectorViewportProps>(function DirectorViewport({
  value,
  panoramaUrl,
  referenceUrls = {},
  onSelect,
  onTransform,
  onWebglError,
}, forwardedRef) {
  const containerRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<ViewportRuntime | null>(null);
  const panoramaRef = useRef<{ texture: THREE.Texture; sphere: THREE.Mesh<THREE.SphereGeometry, THREE.MeshBasicMaterial> } | null>(null);
  const valueRef = useRef(value);
  const callbacksRef = useRef({ onSelect, onTransform });
  valueRef.current = value;
  callbacksRef.current = { onSelect, onTransform };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    } catch (error) {
      onWebglError?.(error instanceof Error ? error.message : "当前设备无法创建 WebGL 视口");
      return;
    }
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.domElement.className = "director-webgl-canvas";
    renderer.domElement.setAttribute("aria-label", "3D 场景视口");
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(valueRef.current.scene.skyColor);
    scene.fog = new THREE.Fog(valueRef.current.scene.skyColor, 15, 54);
    const world = new THREE.Group();
    world.name = "director-world";
    scene.add(world);

    const directorCamera = new THREE.PerspectiveCamera(45, 1, .05, 250);
    directorCamera.position.set(6.2, 4.2, 7.4);
    const orbit = new OrbitControls(directorCamera, renderer.domElement);
    orbit.target.set(0, 1, 0);
    orbit.enableDamping = true;
    orbit.dampingFactor = .075;
    orbit.minDistance = 1.5;
    orbit.maxDistance = 42;
    orbit.maxPolarAngle = Math.PI * .495;
    orbit.update();

    const transform = new TransformControls(directorCamera, renderer.domElement);
    transform.setSize(.86);
    const transformHelper = transform.getHelper();
    scene.add(transformHelper);
    let transformInteracting = false;
    transform.addEventListener("mouseDown", () => { transformInteracting = true; });
    transform.addEventListener("dragging-changed", (event) => { orbit.enabled = !(event as unknown as { value: boolean }).value; });
    transform.addEventListener("mouseUp", () => {
      const object = transform.object;
      const objectId = object?.userData.objectId as string | undefined;
      if (!object || !objectId) return;
      if (valueRef.current.scene.groundSnap && object.userData.objectKind !== "camera") {
        object.position.y = valueRef.current.scene.groundHeight;
      }
      callbacksRef.current.onTransform(objectId, {
        position: [Number(object.position.x.toFixed(2)), Number(object.position.y.toFixed(2)), Number(object.position.z.toFixed(2))],
        rotation: vectorFromEuler(object.rotation),
        scale: [Number(object.scale.x.toFixed(2)), Number(object.scale.y.toFixed(2)), Number(object.scale.z.toFixed(2))],
      });
      window.setTimeout(() => { transformInteracting = false; }, 0);
    });

    const hemisphere = new THREE.HemisphereLight("#dbe8ff", "#20252a", 1.5);
    scene.add(hemisphere);
    const keyLight = new THREE.DirectionalLight("#ffffff", 2.4);
    keyLight.position.set(4, 8, 5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(1024, 1024);
    keyLight.shadow.camera.left = -12;
    keyLight.shadow.camera.right = 12;
    keyLight.shadow.camera.top = 12;
    keyLight.shadow.camera.bottom = -12;
    scene.add(keyLight);
    const rim = new THREE.DirectionalLight("#478cff", 1.2);
    rim.position.set(-5, 4, -3);
    scene.add(rim);

    const grid = new THREE.GridHelper(80, 80, "#174360", "#143044");
    grid.material.transparent = true;
    grid.material.opacity = .56;
    world.add(grid);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), new THREE.MeshStandardMaterial({ color: "#11161d", roughness: .96, transparent: true, opacity: .4 }));
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    world.add(ground);

    const objects = new Map<string, THREE.Object3D>();
    const cameraHelpers = new Map<string, THREE.CameraHelper>();
    const resize = () => {
      const width = Math.max(1, container.clientWidth);
      const height = Math.max(1, container.clientHeight);
      const maxRatio = width * height > 2_500_000 ? 1 : 1.5;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, maxRatio));
      renderer.setSize(width, height, false);
      directorCamera.aspect = width / height;
      directorCamera.updateProjectionMatrix();
      objects.forEach((object) => {
        if (!(object instanceof THREE.PerspectiveCamera)) return;
        object.aspect = aspectValue(valueRef.current.aspectRatio, container);
        object.updateProjectionMatrix();
      });
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let pointerStart: { x: number; y: number } | null = null;
    const onPointerDown = (event: PointerEvent) => { if (event.button === 0) pointerStart = { x: event.clientX, y: event.clientY }; };
    const onPointerUp = (event: PointerEvent) => {
      if (event.button !== 0 || !pointerStart) return;
      const start = pointerStart;
      pointerStart = null;
      if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > 5 || transform.dragging || transformInteracting) return;
      const rect = renderer.domElement.getBoundingClientRect();
      const current = valueRef.current;
      const bounds = current.viewMode === "camera" ? viewportBounds(current.aspectRatio, container) : { x: 0, y: 0, width: rect.width, height: rect.height };
      const localX = event.clientX - rect.left - bounds.x;
      const localY = event.clientY - rect.top - bounds.y;
      if (localX < 0 || localY < 0 || localX > bounds.width || localY > bounds.height) return;
      pointer.x = (localX / bounds.width) * 2 - 1;
      pointer.y = -(localY / bounds.height) * 2 + 1;
      raycaster.setFromCamera(pointer, runtimeCamera(runtimeRef.current!, current));
      const matches = raycaster.intersectObjects([...objects.values()].filter((object) => object.visible), true);
      let selected: THREE.Object3D | null = matches[0]?.object ?? null;
      while (selected && !selected.userData.objectId) selected = selected.parent;
      callbacksRef.current.onSelect((selected?.userData.objectId as string | undefined) ?? null);
    };
    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointerup", onPointerUp);

    const runtime: ViewportRuntime = {
      disposed: false,
      renderer, scene, world, directorCamera, orbit, transform, transformHelper, grid, ground,
      objects, cameraHelpers, resizeObserver,
      disposePointerHandlers: () => {
        renderer.domElement.removeEventListener("pointerdown", onPointerDown);
        renderer.domElement.removeEventListener("pointerup", onPointerUp);
      },
    };
    runtimeRef.current = runtime;
    const cameraPosition = new THREE.Vector3();
    const labelPosition = new THREE.Vector3();
    renderer.setAnimationLoop(() => {
      const current = valueRef.current;
      const renderCamera = runtimeCamera(runtime, current);
      orbit.enabled = current.viewMode === "director" && !transform.dragging;
      orbit.update();
      transformHelper.visible = current.viewMode === "director" && Boolean(transform.object) && !Boolean(transform.object?.userData.locked);
      const width = Math.max(1, container.clientWidth);
      const height = Math.max(1, container.clientHeight);
      renderer.setRenderTarget(null);
      renderer.setViewport(0, 0, width, height);
      renderer.setScissorTest(false);
      if (current.viewMode === "camera") {
        renderer.setClearColor("#050506", 1);
        renderer.clear(true, true, true);
        const bounds = viewportBounds(current.aspectRatio, container);
        renderer.setViewport(bounds.x, bounds.y, bounds.width, bounds.height);
        renderer.setScissor(bounds.x, bounds.y, bounds.width, bounds.height);
        renderer.setScissorTest(true);
        renderCamera.aspect = bounds.ratio;
        renderCamera.updateProjectionMatrix();
      } else {
        renderCamera.aspect = width / height;
        renderCamera.updateProjectionMatrix();
      }
      renderCamera.getWorldPosition(cameraPosition);
      runtime.objects.forEach((object) => {
        const label = object.getObjectByName("object-label");
        if (!label) return;
        label.getWorldPosition(labelPosition);
        const heightScale = THREE.MathUtils.clamp(cameraPosition.distanceTo(labelPosition) * .011, .022, .15);
        label.scale.set(heightScale * 4.05, heightScale, 1);
      });
      renderScene(runtime, renderCamera, renderCamera, current.viewMode === "camera");
      renderer.setScissorTest(false);
    });

    const canvas = renderer.domElement;
    const onContextLost = (event: Event) => {
      event.preventDefault();
      onWebglError?.("3D 视口暂时不可用，请重新打开导演台恢复。场景数据已保留。");
    };
    canvas.addEventListener("webglcontextlost", onContextLost);
    return () => {
      runtime.disposed = true;
      canvas.removeEventListener("webglcontextlost", onContextLost);
      renderer.setAnimationLoop(null);
      runtime.disposePointerHandlers();
      resizeObserver.disconnect();
      transform.detach();
      transform.dispose();
      orbit.dispose();
      cameraHelpers.forEach((helper) => { helper.dispose(); helper.removeFromParent(); });
      objects.forEach((object) => { disposeObject(object); object.removeFromParent(); });
      objects.clear();
      cameraHelpers.clear();
      disposeObject(ground);
      grid.geometry.dispose();
      disposeMaterial(grid.material);
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
      runtimeRef.current = null;
    };
  }, [onWebglError]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    const activeIds = new Set(value.objects.map((object) => object.id));
    runtime.objects.forEach((object, id) => {
      if (activeIds.has(id)) return;
      if (runtime.transform.object === object) runtime.transform.detach();
      const helper = runtime.cameraHelpers.get(id);
      helper?.dispose();
      helper?.removeFromParent();
      runtime.cameraHelpers.delete(id);
      object.removeFromParent();
      disposeObject(object);
      runtime.objects.delete(id);
    });
    value.objects.forEach((object) => {
      let sceneObject = runtime.objects.get(object.id);
      const requiresActorRebuild = object.kind === "actor" && sceneObject?.userData.archetype !== object.archetype;
      if (sceneObject && requiresActorRebuild) {
        if (runtime.transform.object === sceneObject) runtime.transform.detach();
        sceneObject.removeFromParent();
        disposeObject(sceneObject);
        runtime.objects.delete(object.id);
        sceneObject = undefined;
      }
      if (!sceneObject) {
        sceneObject = createSceneObject(object);
        runtime.objects.set(object.id, sceneObject);
        runtime.world.add(sceneObject);
        if (sceneObject instanceof THREE.PerspectiveCamera) {
          const helper = new THREE.CameraHelper(sceneObject);
          helper.setColors(...["#25516a", "#25516a", "#1b4055", "#315e73", "#315e73"].map((entry) => new THREE.Color(entry)) as [THREE.Color, THREE.Color, THREE.Color, THREE.Color, THREE.Color]);
          helper.userData.objectId = object.id;
          runtime.cameraHelpers.set(object.id, helper);
          runtime.scene.add(helper);
        }
      }
      updateObject(sceneObject, object, value.scene.showLabels);
      if (sceneObject instanceof THREE.PerspectiveCamera && containerRef.current) {
        sceneObject.aspect = aspectValue(value.aspectRatio, containerRef.current);
        sceneObject.updateProjectionMatrix();
      }
      runtime.cameraHelpers.get(object.id)?.update();
    });

    value.objects.forEach((object) => {
      if (object.kind !== "camera") return;
      const camera = runtime.objects.get(object.id);
      if (!(camera instanceof THREE.PerspectiveCamera)) return;
      const followTarget = object.followTargetId ? runtime.objects.get(object.followTargetId) : null;
      if (followTarget) {
        const offset = object.followOffset ? new THREE.Vector3().fromArray(object.followOffset) : camera.position.clone().sub(followTarget.position);
        camera.position.copy(followTarget.position).add(offset);
      }
      const lookAtTarget = object.lookAtMode === "object" && object.lookAtTargetId ? runtime.objects.get(object.lookAtTargetId) : null;
      if (lookAtTarget) {
        const target = new THREE.Vector3();
        lookAtTarget.getWorldPosition(target);
        camera.lookAt(target);
      } else if (object.lookAtMode === "point") {
        const target = runtime.world.localToWorld(new THREE.Vector3().fromArray(object.lookAt));
        camera.lookAt(target);
      }
      camera.updateMatrixWorld(true);
    });

    const selected = value.selectedObjectId ? runtime.objects.get(value.selectedObjectId) : undefined;
    if (selected && !selected.userData.locked && value.viewMode === "director") runtime.transform.attach(selected);
    else runtime.transform.detach();
    runtime.transform.setMode(value.tool === "select" ? "translate" : value.tool);
    runtime.transform.translationSnap = value.scene.gridSnap ? .25 : null;
    runtime.transform.rotationSnap = value.scene.gridSnap ? toRadians(5) : null;
    runtime.transform.scaleSnap = value.scene.gridSnap ? .1 : null;

    runtime.world.position.fromArray(value.scene.position);
    runtime.world.rotation.set(toRadians(value.scene.rotation[0]), toRadians(value.scene.rotation[1]), toRadians(value.scene.rotation[2]));
    runtime.world.scale.setScalar(value.scene.scale / 3);
    runtime.grid.visible = value.scene.showGround;
    runtime.grid.position.y = value.scene.groundHeight + .003;
    runtime.ground.visible = value.scene.showGround;
    runtime.ground.position.y = value.scene.groundHeight;
    (runtime.ground.material as THREE.MeshStandardMaterial).opacity = value.scene.groundOpacity;
    runtime.cameraHelpers.forEach((helper, id) => {
      helper.visible = value.viewMode === "director" && value.objects.some((object) => object.id === id && object.visible);
    });
    applyReferenceTextures(runtime, value, referenceUrls);
  }, [referenceUrls, value]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    let disposed = false;
    let texture: THREE.Texture | null = null;
    let sphere: THREE.Mesh<THREE.SphereGeometry, THREE.MeshBasicMaterial> | null = null;
    if (!panoramaUrl) {
      panoramaRef.current = null;
      runtime.scene.background = new THREE.Color(value.scene.skyColor);
      runtime.scene.environment = null;
      runtime.scene.fog = new THREE.Fog(value.scene.skyColor, 15, 54);
      return;
    }
    new THREE.TextureLoader().load(panoramaUrl, (loaded) => {
      if (disposed) { loaded.dispose(); return; }
      texture = loaded;
      loaded.mapping = THREE.EquirectangularReflectionMapping;
      loaded.colorSpace = THREE.SRGBColorSpace;
      sphere = new THREE.Mesh(
        new THREE.SphereGeometry(1, 64, 32),
        new THREE.MeshBasicMaterial({ map: loaded, side: THREE.BackSide, fog: false, depthWrite: false }),
      );
      sphere.scale.setScalar(valueRef.current.scene.panoramaRadius);
      sphere.rotation.y = toRadians(valueRef.current.scene.panoramaRotation);
      sphere.renderOrder = -10;
      runtime.scene.add(sphere);
      panoramaRef.current = { texture: loaded, sphere };
      runtime.scene.background = new THREE.Color(valueRef.current.scene.skyColor);
      runtime.scene.environment = loaded;
      runtime.scene.fog = null;
    });
    return () => {
      disposed = true;
      if (panoramaRef.current?.texture === texture) panoramaRef.current = null;
      if (runtime.scene.environment === texture) runtime.scene.environment = null;
      if (sphere) {
        sphere.removeFromParent();
        sphere.geometry.dispose();
        sphere.material.dispose();
      }
      texture?.dispose();
    };
  }, [panoramaUrl]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    const panorama = panoramaRef.current;
    if (panorama) {
      panorama.sphere.scale.setScalar(value.scene.panoramaRadius);
      panorama.sphere.rotation.y = toRadians(value.scene.panoramaRotation);
      runtime.scene.background = new THREE.Color(value.scene.skyColor);
      runtime.scene.fog = null;
    } else if (!panoramaUrl) {
      runtime.scene.background = new THREE.Color(value.scene.skyColor);
      runtime.scene.fog = new THREE.Fog(value.scene.skyColor, 15, 54);
    }
  }, [panoramaUrl, value.scene.panoramaRadius, value.scene.panoramaRotation, value.scene.skyColor]);

  useImperativeHandle(forwardedRef, () => ({
    getCurrentView() {
      const runtime = runtimeRef.current;
      if (!runtime) return null;
      const pose = persistedCameraPose(runtime, runtimeCamera(runtime, valueRef.current));
      return { cameraPosition: pose.position, cameraRotation: pose.rotation, fov: pose.fov };
    },
    resetView() {
      const runtime = runtimeRef.current;
      if (!runtime) return;
      runtime.directorCamera.position.set(6.2, 4.2, 7.4);
      runtime.orbit.target.set(0, 1, 0);
      runtime.orbit.update();
    },
    setAxisView(view) {
      const runtime = runtimeRef.current;
      if (!runtime) return;
      const distance = 8;
      if (view === "front") runtime.directorCamera.position.set(0, 2.1, distance);
      else if (view === "top") runtime.directorCamera.position.set(0, distance, .001);
      else runtime.directorCamera.position.set(distance, 2.1, 0);
      runtime.orbit.target.set(0, 1, 0);
      runtime.orbit.update();
    },
    async capture(aspectRatio, cameraId): Promise<DirectorCaptureResult> {
      const runtime = runtimeRef.current;
      const container = containerRef.current;
      if (!runtime || !container) throw new Error("3D 视口尚未准备完成");
      const { width, height } = outputSize(aspectRatio, container);
      const requestedCamera = cameraId ? runtime.objects.get(cameraId) : null;
      const sourceCamera = requestedCamera instanceof THREE.PerspectiveCamera ? requestedCamera : runtimeCamera(runtime, valueRef.current);
      const worldPosition = new THREE.Vector3();
      const worldQuaternion = new THREE.Quaternion();
      sourceCamera.getWorldPosition(worldPosition);
      sourceCamera.getWorldQuaternion(worldQuaternion);
      const persistedPose = persistedCameraPose(runtime, sourceCamera);
      const camera = sourceCamera.clone() as THREE.PerspectiveCamera;
      camera.clear();
      camera.position.copy(worldPosition);
      camera.quaternion.copy(worldQuaternion);
      camera.scale.set(1, 1, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      camera.updateMatrixWorld(true);
      const target = new THREE.WebGLRenderTarget(width, height, { depthBuffer: true, stencilBuffer: false });
      target.texture.colorSpace = THREE.SRGBColorSpace;
      const previousTarget = runtime.renderer.getRenderTarget();
      const previousViewport = runtime.renderer.getViewport(new THREE.Vector4()).clone();
      const previousScissor = runtime.renderer.getScissor(new THREE.Vector4()).clone();
      const previousScissorTest = runtime.renderer.getScissorTest();
      const transformVisible = runtime.transformHelper.visible;
      const helperVisibility = new Map<string, boolean>();
      const editorObjectVisibility = new Map<THREE.Object3D, boolean>();
      runtime.transformHelper.visible = false;
      runtime.cameraHelpers.forEach((helper, id) => { helperVisibility.set(id, helper.visible); helper.visible = false; });
      runtime.objects.forEach((object) => {
        object.traverse((child) => {
          if ((object instanceof THREE.PerspectiveCamera && child !== object) || child.name === "object-label") {
            editorObjectVisibility.set(child, child.visible);
            child.visible = false;
          }
        });
      });
      try {
        runtime.renderer.setRenderTarget(target);
        runtime.renderer.setViewport(0, 0, width, height);
        runtime.renderer.setScissor(0, 0, width, height);
        runtime.renderer.setScissorTest(false);
        renderScene(runtime, camera, sourceCamera);
        const pixels = new Uint8Array(width * height * 4);
        await runtime.renderer.readRenderTargetPixelsAsync(target, 0, 0, width, height, pixels);
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext("2d");
        if (!context) throw new Error("无法创建截图画布");
        const flipped = new Uint8ClampedArray(pixels.length);
        const rowBytes = width * 4;
        for (let y = 0; y < height; y += 1) {
          flipped.set(pixels.subarray(y * rowBytes, (y + 1) * rowBytes), (height - y - 1) * rowBytes);
        }
        context.putImageData(new ImageData(flipped, width, height), 0, 0);
        const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob((result) => result ? resolve(result) : reject(new Error("截图编码失败")), "image/png"));
        return {
          blob,
          width,
          height,
          cameraPosition: persistedPose.position,
          cameraRotation: persistedPose.rotation,
          fov: sourceCamera.fov,
        };
      } finally {
        runtime.renderer.setRenderTarget(previousTarget);
        runtime.renderer.setViewport(previousViewport);
        runtime.renderer.setScissor(previousScissor);
        runtime.renderer.setScissorTest(previousScissorTest);
        runtime.transformHelper.visible = transformVisible;
        runtime.cameraHelpers.forEach((helper, id) => { helper.visible = helperVisibility.get(id) ?? false; });
        editorObjectVisibility.forEach((visible, object) => { object.visible = visible; });
        target.dispose();
      }
    },
  }), []);

  return <div ref={containerRef} className="director-viewport-canvas" />;
});
