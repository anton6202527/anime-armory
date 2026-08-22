import { memo, useEffect, useRef, useState, useSyncExternalStore, type CSSProperties, type MouseEvent as ReactMouseEvent } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { getMediaPort, mediaUrl, saveCanvasCapture, subscribeMediaPort } from "../api";
import { useI18n } from "../i18n";
import type {
  CanvasAgentDispatchContext,
  CanvasAgentDispatchResult,
  CanvasClip,
  CanvasFrame,
  CanvasGenerationProfile,
  LineKey,
} from "../types";
import { DecodedImage } from "../mediaPreview/DecodedImage";
import { canvasFrameTargetSlot, canvasImageTargetRel, canvasVideoTargetRel, stableCanvasSlotToken } from "../../../shared/canvasTargets";
import {
  CanvasMediaDetailDialog,
  type CanvasMediaDetailReference,
  type CanvasMediaDetailState,
} from "./CanvasMediaDetailDialog";

type CanvasNodeVariant = "asset-anchor" | "character" | "reference" | "frame" | "shot" | "video" | "lane";
interface SharedAssetImage {
  id: string;
  label: string;
  abs: string;
  exists: boolean;
  revision?: string;
  prompt?: string;
  clipIds: string[];
  roles: string[];
}
type EditableCanvasClip = CanvasClip & {
  variant?: CanvasNodeVariant;
  clipCount?: number;
  laneMeta?: string[];
  promptTooltip?: string;
  assetImages?: SharedAssetImage[];
  refImageAbs?: string;
  refImageExists?: boolean;
  refImageRevision?: string;
  refRoles?: string[];
  rootPath?: string;
  repoRoot?: string;
  episode?: string;
  line?: LineKey;
  generationProfile?: CanvasGenerationProfile;
  contentHash?: string;
  targetFrameIndex?: number;
  onGeneratePrompt?: (prompt: string, task?: CanvasAgentDispatchContext) => Promise<CanvasAgentDispatchResult>;
  onEdit?: () => void;
};

function detailAnchor(event: ReactMouseEvent<HTMLElement>): { x: number; y: number } {
  return { x: event.clientX, y: event.clientY };
}

function clipScoreTone(clip: CanvasClip): string {
  if (clip.qa_blocks > 0) return "block";
  if (clip.score == null) return clip.qa_warnings > 0 ? "warn" : "info";
  if (clip.score < 60) return "block";
  if (clip.score < 80 || clip.qa_warnings > 0) return "warn";
  return "pass";
}

function fmtScore(score?: number): string {
  if (score == null) return "—";
  return Number.isInteger(score) ? String(score) : score.toFixed(1);
}

function isReferenceInputFrame(frame: CanvasFrame): boolean {
  const text = `${frame.role || ""} ${frame.label || ""} ${frame.abs || ""}`;
  return /出图[\\/]共享|shared_asset|入参|参考|引用|reference|ref|asset|input|consumed|style/i.test(text);
}

function targetSlotForFrame(frame: CanvasFrame, allFrames: CanvasFrame[], stableIndex?: number): string {
  const index = stableIndex == null ? Math.max(0, allFrames.indexOf(frame)) : stableIndex;
  return canvasFrameTargetSlot(frame, index);
}

function joinWorkPath(root: string, rel: string): string {
  const separator = root.includes("\\") && !root.includes("/") ? "\\" : "/";
  return `${root.replace(/[\\/]+$/, "")}${separator}${rel.replace(/[\\/]+/g, separator).replace(/^[\\/]+/, "")}`;
}

function formatVideoTime(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0:00";
  const total = Math.max(0, Math.floor(value));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function waitForSeek(video: HTMLVideoElement, time: number): Promise<void> {
  return new Promise((resolve) => {
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      video.removeEventListener("seeked", done);
      resolve();
    };
    video.addEventListener("seeked", done, { once: true });
    video.currentTime = time;
    window.setTimeout(done, 900);
  });
}

type VideoControlIconName = "play" | "pause" | "volumeOn" | "volumeOff" | "camera";

function VideoControlIcon({ name }: { name: VideoControlIconName }) {
  switch (name) {
    case "play":
      return (
        <svg className="cv-icon cv-icon-play" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
          <path className="cv-fill" d="M13 7 32 20 13 33Z" />
        </svg>
      );
    case "pause":
      return (
        <svg className="cv-icon cv-icon-pause" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
          <rect className="cv-fill" x="11.5" y="6" width="5.2" height="28" rx="1.2" />
          <rect className="cv-fill" x="23.3" y="6" width="5.2" height="28" rx="1.2" />
        </svg>
      );
    case "volumeOn":
      return (
        <svg className="cv-icon cv-icon-volume-on" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
          <path
            className="cv-stroke cv-speaker"
            d="M4.2 9.4h5.4L18 3.5c.8-.6 1.9 0 1.9 1v23c0 1-1.1 1.6-1.9 1l-8.4-5.8H4.2a1.8 1.8 0 0 1-1.8-1.8v-9.7a1.8 1.8 0 0 1 1.8-1.8Z"
          />
          <path className="cv-stroke cv-sound-wave" d="M26.1 10.1c3.6 3.2 3.6 8.6 0 11.8" />
        </svg>
      );
    case "volumeOff":
      return (
        <svg className="cv-icon cv-icon-volume-off" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
          <path
            className="cv-stroke cv-speaker"
            d="M4.2 9.4h5.4L18 3.5c.8-.6 1.9 0 1.9 1v23c0 1-1.1 1.6-1.9 1l-8.4-5.8H4.2a1.8 1.8 0 0 1-1.8-1.8v-9.7a1.8 1.8 0 0 1 1.8-1.8Z"
          />
          <path className="cv-stroke cv-mute-mark" d="m22 12 7 8m0-8-7 8" />
        </svg>
      );
    case "camera":
      return (
        <svg className="cv-icon cv-icon-camera" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
          <path
            className="cv-stroke"
            d="M5 11h4.5l3.2-4.5h6.6l3.2 4.5H27a2.5 2.5 0 0 1 2.5 2.5v13A2.5 2.5 0 0 1 27 29H5a2.5 2.5 0 0 1-2.5-2.5v-13A2.5 2.5 0 0 1 5 11Z"
          />
          <circle className="cv-stroke" cx="16" cy="19.5" r="4.6" />
        </svg>
      );
  }
}

const CanvasVideoPlayer = memo(function CanvasVideoPlayer(props: {
  videoUrl: string;
  posterUrl: string;
  label: string;
  nodeLabel: string;
  rootPath?: string;
  durationHint?: number;
  noVideoLabel: string;
  onOpenDetail: (event: ReactMouseEvent<HTMLElement>) => void;
}) {
  const { videoUrl, posterUrl, label, nodeLabel, rootPath, durationHint, noVideoLabel, onOpenDetail } = props;
  const { t } = useI18n();
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [activated, setActivated] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const previousVolumeRef = useRef(1);
  const [savingCapture, setSavingCapture] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(durationHint ?? 0);
  const [resolution, setResolution] = useState("");
  const lastTimeUpdateRef = useRef(0);

  useEffect(() => {
    setPlaying(false);
    setActivated(false);
    setCurrent(0);
    setDuration(durationHint ?? 0);
    setResolution("");
  }, [durationHint, videoUrl]);

  useEffect(() => {
    if (videoRef.current) videoRef.current.volume = Math.max(0, Math.min(1, volume));
  }, [volume, videoUrl]);

  async function togglePlay() {
    const video = videoRef.current;
    if (!video || !videoUrl) return;
    if (video.paused) {
      await video.play().catch(() => undefined);
    } else {
      video.pause();
    }
  }

  function seek(value: number) {
    const video = videoRef.current;
    if (!video || !Number.isFinite(value)) return;
    video.currentTime = value;
    setCurrent(value);
  }

  function changeVolume(value: number) {
    const next = Math.max(0, Math.min(1, value));
    setVolume(next);
    if (next > 0) previousVolumeRef.current = next;
    setMuted(next <= 0);
  }

  function toggleMute() {
    if (muted || volume <= 0) {
      const restored = volume > 0 ? volume : Math.max(0.01, previousVolumeRef.current);
      setVolume(restored);
      setMuted(false);
      return;
    }
    previousVolumeRef.current = volume;
    setMuted(true);
  }

  async function captureFrame(kind: "first" | "current" | "last") {
    const video = videoRef.current;
    if (!video || !videoUrl || !rootPath || savingCapture) return;
    const wasPlaying = !video.paused;
    video.pause();
    const target =
      kind === "first"
        ? 0
        : kind === "last"
          ? Math.max(0, (duration || video.duration || 0) - 0.05)
          : video.currentTime;
    if (Math.abs(video.currentTime - target) > 0.03) await waitForSeek(video, target);
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    try {
      canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/png");
      setSavingCapture(true);
      await saveCanvasCapture(rootPath, dataUrl, `${label}-${kind}-${formatVideoTime(video.currentTime)}`);
    } catch (error) {
      console.error("failed to save canvas capture", error);
    } finally {
      setSavingCapture(false);
      if (wasPlaying) await video.play().catch(() => undefined);
    }
  }

  const progress = duration > 0 ? Math.max(0, Math.min(100, (current / duration) * 100)) : 0;
  const rangeStyle = { "--video-progress": `${progress}%` } as CSSProperties;
  const effectivelyMuted = muted || volume <= 0;
  const volumeValue = effectivelyMuted ? 0 : volume;

  if (!videoUrl) {
    return (
      <div
        className="canvas-video-player missing"
        onClick={(event) => {
          event.stopPropagation();
          onOpenDetail(event);
        }}
      >
        {posterUrl ? <DecodedImage src={posterUrl} alt="" maxDecodeDimension={1280} /> : null}
        <span>{noVideoLabel}</span>
      </div>
    );
  }

  if (!activated) {
    return (
      <button
        type="button"
        className="canvas-video-player dormant"
        aria-label={t("canvas.playVideo")}
        onPointerEnter={() => setActivated(true)}
        onFocus={() => setActivated(true)}
        onClick={(event) => {
          event.stopPropagation();
          setActivated(true);
        }}
        onDoubleClick={(event) => {
          event.stopPropagation();
          onOpenDetail(event);
        }}
      >
        {posterUrl ? <DecodedImage src={posterUrl} alt="" maxDecodeDimension={1280} /> : null}
        <span className="canvas-video-node-label"><VideoControlIcon name="play" />{nodeLabel}</span>
      </button>
    );
  }

  return (
    <>
      <div
        ref={playerRef}
        className={"canvas-video-player active" + (playing ? " playing" : "")}
        onClick={(event) => {
          event.stopPropagation();
          onOpenDetail(event);
        }}
        onDoubleClick={(event) => event.stopPropagation()}
      >
        <video
          ref={videoRef}
          src={videoUrl}
          poster={posterUrl || undefined}
          crossOrigin="anonymous"
          playsInline
          preload="metadata"
          muted={effectivelyMuted}
          onLoadedMetadata={(event) => {
            const nextDuration = event.currentTarget.duration;
            if (Number.isFinite(nextDuration)) setDuration(nextDuration);
            const { videoWidth, videoHeight } = event.currentTarget;
            setResolution(videoWidth && videoHeight ? `${videoWidth} × ${videoHeight}` : "");
          }}
          onDurationChange={(event) => {
            const nextDuration = event.currentTarget.duration;
            if (Number.isFinite(nextDuration)) setDuration(nextDuration);
          }}
          onTimeUpdate={(event) => {
            const now = window.performance.now();
            if (now - lastTimeUpdateRef.current < 250) return;
            lastTimeUpdateRef.current = now;
            setCurrent(event.currentTarget.currentTime);
          }}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
        />
        <div className="canvas-video-node-meta" aria-hidden="true">
          <span className="canvas-video-node-label"><VideoControlIcon name="play" />{nodeLabel}</span>
          {resolution && <span className="canvas-video-resolution">{resolution}</span>}
        </div>
        <div
          className="canvas-video-controls nodrag"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            className="canvas-video-play"
            aria-label={playing ? t("canvas.pauseVideo") : t("canvas.playVideo")}
            onClick={togglePlay}
          >
            <VideoControlIcon name={playing ? "pause" : "play"} />
          </button>
          <span className="canvas-video-time">{formatVideoTime(current)}</span>
          <input
            className="canvas-video-range"
            type="range"
            min="0"
            max={duration || 0}
            step="0.01"
            value={Math.min(current, duration || current)}
            aria-label={t("canvas.videoSeek")}
            onPointerDown={(event) => event.stopPropagation()}
            onChange={(event) => seek(Number(event.target.value))}
            style={rangeStyle}
          />
          <span className="canvas-video-time">{formatVideoTime(duration)}</span>
          <div className="canvas-video-volume">
            <div className="canvas-video-volume-popover">
              <span>{Math.round(volumeValue * 100)}</span>
              <div className="canvas-video-volume-slider">
                <input
                  className="canvas-video-volume-range"
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={volumeValue}
                  style={{ "--volume-level": `${volumeValue * 100}%` } as CSSProperties}
                  aria-label={effectivelyMuted ? t("canvas.unmuteVideo") : t("canvas.muteVideo")}
                  onChange={(event) => changeVolume(Number(event.target.value))}
                />
              </div>
            </div>
            <button
              type="button"
              className="canvas-video-icon"
              aria-label={effectivelyMuted ? t("canvas.unmuteVideo") : t("canvas.muteVideo")}
              onClick={toggleMute}
            >
              <VideoControlIcon name={effectivelyMuted ? "volumeOff" : "volumeOn"} />
            </button>
          </div>
          <div className="canvas-video-capture">
            <div
              className="canvas-video-capture-menu"
              onPointerDown={(event) => event.stopPropagation()}
              onClick={(event) => event.stopPropagation()}
            >
              <button type="button" disabled={savingCapture} onClick={() => captureFrame("first")}>{t("canvas.captureFirstFrame")}</button>
              <button type="button" disabled={savingCapture} onClick={() => captureFrame("last")}>{t("canvas.captureLastFrame")}</button>
              <button type="button" disabled={savingCapture} onClick={() => captureFrame("current")}>{t("canvas.captureCurrentFrame")}</button>
            </div>
            <button
              type="button"
              className="canvas-video-icon canvas-video-capture-btn"
              aria-label={t("canvas.captureFrame")}
            >
              <VideoControlIcon name="camera" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
});

// Custom React Flow node = one storyboard Clip card with a frame thumbnail,
// rhythm chip, duration, and QA badges.
function ClipNodeComponent({ data, selected }: NodeProps) {
  const { t } = useI18n();
  const clip = data as unknown as EditableCanvasClip;
  const variant = clip.variant ?? "shot";
  const isCharacter = variant === "character";
  const isReference = variant === "reference";
  const isFrame = variant === "frame";
  const isShot = variant === "shot";
  const isVideo = variant === "video";
  const isLane = variant === "lane";
  const isAssetAnchor = variant === "asset-anchor";
  const [mediaDetail, setMediaDetail] = useState<CanvasMediaDetailState | null>(null);
  // re-render once the media server port is ready (else thumbs stay "未出图")
  useSyncExternalStore(subscribeMediaPort, getMediaPort);
  const withRevision = (url: string, revision?: string) =>
    url && revision ? `${url}&v=${encodeURIComponent(revision)}` : url;
  const frames = (clip.frames || []).filter((frame) => isFrame || frame.abs || frame.exists);
  const visibleFrames = (isShot || isFrame) ? frames.filter((frame) => isFrame || !isReferenceInputFrame(frame)) : frames;
  const shownFrames = visibleFrames.length
    ? visibleFrames
    : clip.first_frame_abs
      ? [{
          role: "first",
          label: "首帧",
          abs: clip.first_frame_abs,
          exists: clip.first_frame_exists,
          prompt: clip.prompt,
        }]
      : [];
  const posterFrame = shownFrames.find((frame) => frame.exists && frame.abs);
  const posterUrl = posterFrame?.abs ? withRevision(mediaUrl(posterFrame.abs), posterFrame.revision) : "";
  const videoUrl = clip.video_exists && clip.video_abs
    ? withRevision(mediaUrl(clip.video_abs), clip.video_revision)
    : "";
  const refImageUrl = clip.refImageExists && clip.refImageAbs
    ? withRevision(mediaUrl(clip.refImageAbs), clip.refImageRevision)
    : "";
  const referenceFrames = frames.filter((frame) => frame.exists && frame.abs && isReferenceInputFrame(frame));
  const clipTooltip = clip.promptTooltip || [
    clip.label,
    clip.scene || "",
    clip.template ? `template: ${clip.template}` : "",
    clip.prompt || "",
  ].filter(Boolean).join("\n");
  const nodeClass = [
    "clip-node",
    `${variant}-node`,
    selected ? "selected" : "",
  ].filter(Boolean).join(" ");

  useEffect(() => {
    if (!mediaDetail) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMediaDetail(null);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mediaDetail]);

  function detailPrompt(frame?: CanvasFrame): string {
    return [
      frame?.prompt || clip.prompt || "",
      clip.scene || "",
      clip.rhythm || "",
      clip.template || "",
    ].filter(Boolean).join("\n");
  }

  function mediaRefsFromFrames(sourceFrames: CanvasFrame[]): CanvasMediaDetailReference[] {
    const seen = new Set<string>();
    return sourceFrames.flatMap((frame, index) => {
      if (!frame.exists || !frame.abs || seen.has(frame.abs)) return [];
      seen.add(frame.abs);
      return [{
        id: `${frame.role || "frame"}-${frame.abs}-${index}`,
        label: frame.label || t("canvas.imageNumber", { count: index + 1 }),
        role: frame.role,
        url: withRevision(mediaUrl(frame.abs), frame.revision),
        path: frame.abs,
      }];
    }).slice(0, 14);
  }

  function mediaRefsFromAssets(assets: SharedAssetImage[]): CanvasMediaDetailReference[] {
    return assets.flatMap((asset, index) => {
      if (!asset.exists || !asset.abs) return [];
      return [{
        id: asset.id,
        label: asset.label || t("canvas.imageNumber", { count: index + 1 }),
        role: asset.roles[0],
        url: withRevision(mediaUrl(asset.abs), asset.revision),
        path: asset.abs,
      }];
    }).slice(0, 14);
  }

  function openFrameDetail(frame: CanvasFrame, event: ReactMouseEvent<HTMLElement>) {
    const targetSlot = targetSlotForFrame(frame, shownFrames, clip.targetFrameIndex);
    const fallbackRel = clip.line === "comic" && targetSlot === "panel"
      ? `出图/${clip.episode}/panels/${clip.id}.png`
      : canvasImageTargetRel(clip.episode || "", clip.id, targetSlot);
    const targetOutputPath = frame.abs || joinWorkPath(clip.rootPath || "", fallbackRel);
    const referenceSource = (referenceFrames.length ? referenceFrames : shownFrames)
      .filter((candidate) => !targetOutputPath || candidate.abs !== targetOutputPath);
    const currentMediaUrl = frame.exists && frame.abs
      ? withRevision(mediaUrl(frame.abs), frame.revision)
      : "";
    setMediaDetail({
      kind: "image",
      targetSlot,
      targetOutputPath,
      title: frame.label || clip.label,
      subtitle: clip.number != null ? `${clip.number}. ${clip.label}` : clip.label,
      prompt: detailPrompt(frame),
      mediaUrl: currentMediaUrl,
      references: mediaRefsFromFrames(referenceSource),
      anchor: detailAnchor(event),
    });
  }

  function openAssetDetail(asset: SharedAssetImage, event: ReactMouseEvent<HTMLElement>) {
    if (!asset.exists || !asset.abs) return;
    setMediaDetail({
      kind: "image",
      targetSlot: `asset:${stableCanvasSlotToken(asset.id)}`,
      targetOutputPath: asset.abs,
      title: asset.label,
      subtitle: asset.roles.join(" / ") || t("canvas.characterLane"),
      prompt: [
        asset.prompt || "",
        asset.roles.length ? asset.roles.join(" / ") : "",
        t("canvas.referenceCount", { count: asset.clipIds.length }),
      ].filter(Boolean).join("\n"),
      mediaUrl: withRevision(mediaUrl(asset.abs), asset.revision),
      references: mediaRefsFromAssets(clip.assetImages || []),
      anchor: detailAnchor(event),
    });
  }

  function openReferenceDetail(event: ReactMouseEvent<HTMLElement>) {
    if (!refImageUrl || !clip.refImageAbs) return;
    setMediaDetail({
      kind: "image",
      targetSlot: "reference",
      targetOutputPath: clip.refImageAbs,
      title: clip.label,
      subtitle: t("canvas.characterLane"),
      prompt: detailPrompt(),
      mediaUrl: refImageUrl,
      references: [{
        id: `${clip.id}-reference`,
        label: clip.label,
        role: "reference",
        url: refImageUrl,
        path: clip.refImageAbs,
      }],
      anchor: detailAnchor(event),
    });
  }

  function openVideoDetail(event: ReactMouseEvent<HTMLElement>) {
    const referenceSource = posterFrame ? [posterFrame, ...referenceFrames] : referenceFrames;
    setMediaDetail({
      kind: "video",
      targetSlot: "video",
      targetOutputPath: clip.video_abs || joinWorkPath(
        clip.rootPath || "",
        canvasVideoTargetRel(clip.episode || "", clip.id),
      ),
      title: clip.label,
      subtitle: clip.number != null ? `${clip.number}. ${clip.label}` : clip.label,
      prompt: [
        detailPrompt(),
        clip.duration != null ? `${clip.duration}s` : "",
      ].filter(Boolean).join("\n"),
      mediaUrl: posterUrl,
      references: mediaRefsFromFrames(referenceSource),
      anchor: detailAnchor(event),
    });
  }

  function renderMediaDetail() {
    if (!mediaDetail || !clip.rootPath || !clip.episode || !clip.line) return null;
    return (
      <CanvasMediaDetailDialog
        detail={mediaDetail}
        clip={clip}
        line={clip.line}
        repoRoot={clip.repoRoot ?? ""}
        rootPath={clip.rootPath}
        episode={clip.episode}
        profile={clip.generationProfile}
        expectedContentHash={clip.contentHash}
        onClose={() => setMediaDetail(null)}
        onGeneratePrompt={clip.onGeneratePrompt}
      />
    );
  }

  if (isLane) {
    const laneMeta = clip.laneMeta || [];
    return (
      <div className="canvas-lane-node" data-tooltip={clipTooltip} data-tooltip-placement="bottom">
        <span className="canvas-lane-label">{clip.label}</span>
        {laneMeta.map((item) => <span className="canvas-lane-chip" key={item}>{item}</span>)}
      </div>
    );
  }

  if (isAssetAnchor) {
    return (
      <div className="canvas-asset-anchor" aria-hidden="true">
        <Handle type="source" position={Position.Right} />
      </div>
    );
  }

  if (isCharacter) {
    const assetImages = clip.assetImages || [];
    return (
      <>
        <div className={nodeClass}>
          <div className="character-node-mark">{t("canvas.characterLane")}</div>
          {assetImages.length > 0 && (
            <div className="shared-asset-grid">
              {assetImages.map((asset) => {
                const url = asset.exists && asset.abs
                  ? withRevision(mediaUrl(asset.abs), asset.revision)
                  : "";
                return (
                  <span className="shared-asset-thumb-wrap" key={asset.id}>
                    <button
                      type="button"
                      className={"shared-asset-thumb nodrag" + (url ? "" : " missing")}
                      onPointerDown={(event) => event.stopPropagation()}
                      onClick={(event) => {
                        event.stopPropagation();
                        openAssetDetail(asset, event);
                      }}
                    >
                      {url ? <DecodedImage src={url} alt={asset.label} maxDecodeDimension={320} /> : <span>{t("canvas.noImage")}</span>}
                    </button>
                    <Handle type="source" id={asset.id} position={Position.Right} className="shared-asset-handle" />
                  </span>
                );
              })}
            </div>
          )}
          {assetImages.length === 0 && <Handle type="source" position={Position.Right} />}
        </div>
        {renderMediaDetail()}
      </>
    );
  }

  if (isReference) {
    return (
      <>
        <div className={nodeClass}>
          <button
            type="button"
            className={"reference-thumb nodrag" + (refImageUrl ? "" : " missing")}
            onPointerDown={(event) => event.stopPropagation()}
            onClick={(event) => {
              event.stopPropagation();
              openReferenceDetail(event);
            }}
          >
            {refImageUrl ? <DecodedImage src={refImageUrl} alt={clip.label} maxDecodeDimension={512} /> : <span>{t("canvas.noImage")}</span>}
          </button>
          <div className="body">
            <div className="clip-head">
              <div className="label">{clip.label}</div>
            </div>
            <div className="row">
              <span className="chip">{t("canvas.referenceCount", { count: clip.clipCount ?? 0 })}</span>
            </div>
            {clip.scene && <div className="character-node-meta">{clip.scene}</div>}
          </div>
          <Handle type="source" position={Position.Right} />
        </div>
        {renderMediaDetail()}
      </>
    );
  }

  if (isFrame) {
    const frame = shownFrames[0] ?? {
      role: "missing",
      label: clip.label,
      abs: "",
      exists: false,
      prompt: clip.prompt,
    };
    const url = frame.exists && frame.abs ? withRevision(mediaUrl(frame.abs), frame.revision) : "";
    return (
      <>
        <div
          className={nodeClass}
          onDoubleClick={(event) => {
            event.stopPropagation();
            clip.onEdit?.();
          }}
        >
          <Handle type="target" position={Position.Left} />
          <button
            type="button"
            className={"frame-single-thumb" + (url ? "" : " missing")}
            onClick={(event) => {
              event.stopPropagation();
              openFrameDetail(frame, event);
            }}
          >
            <span className="frame-label">{frame.label || frame.role || clip.label}</span>
            {url ? (
              <DecodedImage src={url} alt={`${clip.label} ${frame.label || frame.role || ""}`} maxDecodeDimension={640} />
            ) : (
              <span>{t("canvas.noImage")}</span>
            )}
          </button>
          <Handle type="source" position={Position.Right} />
        </div>
        {renderMediaDetail()}
      </>
    );
  }

  return (
    <>
    <div
      className={nodeClass}
      onDoubleClick={(event) => {
        event.stopPropagation();
        clip.onEdit?.();
      }}
    >
      <Handle type="target" position={Position.Left} />
      {isShot && (
        <div className="frame-strip" aria-label={`${clip.label} frames`}>
          {shownFrames.length ? shownFrames.map((frame, idx) => {
            const url = frame.exists && frame.abs ? withRevision(mediaUrl(frame.abs), frame.revision) : "";
            return (
              <button
                key={`${frame.role}-${frame.abs || idx}`}
                type="button"
                className={"frame-thumb" + (url ? "" : " missing")}
                onClick={(event) => {
                  event.stopPropagation();
                  openFrameDetail(frame, event);
                }}
              >
                <span className="frame-label">{frame.label || frame.role || `帧${idx + 1}`}</span>
                {url ? <DecodedImage src={url} alt={`${clip.label} ${frame.label || idx + 1}`} maxDecodeDimension={640} /> : <span>{t("canvas.noImage")}</span>}
              </button>
            );
          }) : (
            <div className="frame-thumb missing">
              <span>{t("canvas.noImage")}</span>
            </div>
          )}
        </div>
      )}
      {isVideo && (
        <CanvasVideoPlayer
          videoUrl={videoUrl}
          posterUrl={posterUrl}
          label={clip.label}
          nodeLabel={t("canvas.videoNode", { number: clip.number ?? clip.label })}
          rootPath={clip.rootPath}
          durationHint={clip.duration}
          noVideoLabel={t("canvas.noVideo")}
          onOpenDetail={openVideoDetail}
        />
      )}
      <div className="body">
        <div className="clip-head">
          <div className="label">
            {clip.number != null ? `${clip.number}. ` : ""}
            {clip.label}
          </div>
          {clip.onEdit && (
            <button
              type="button"
              className="clip-edit-btn nodrag"
              title={t("canvas.editTitle")}
              aria-label={t("canvas.editTitle")}
              onPointerDown={(event) => event.stopPropagation()}
              onClick={(event) => {
                event.stopPropagation();
                clip.onEdit?.();
              }}
            >
              ✎
            </button>
          )}
        </div>
        <div className="row">
          {clip.duration != null && <span className="chip">{clip.duration}s</span>}
          {clip.rhythm && <span className="chip rhythm">{clip.rhythm}</span>}
          {clip.template && <span className="chip">{clip.template}</span>}
        </div>
        {(clip.score != null || clip.qa_blocks > 0 || clip.qa_warnings > 0) && (
          <div className="quality-mini">
            {clip.score != null && <span className={"score-chip " + clipScoreTone(clip)}>{t("review.scoreShort", { score: fmtScore(clip.score) })}</span>}
            {clip.qa_blocks > 0 && <span className="block">{t("review.blocks", { count: clip.qa_blocks })}</span>}
            {clip.qa_warnings > 0 && <span className="warn">{t("review.warnings", { count: clip.qa_warnings })}</span>}
          </div>
        )}
        {clip.scene && <div className="row" style={{ marginTop: 4 }}>{clip.scene}</div>}
        {clip.qa.length > 0 && (
          <div className="qa">
            {clip.qa.slice(0, 4).map((f, i) => (
              <span key={i} className={"badge " + (f.severity || "info")} title={f.message || ""}>
                {f.dimension || f.severity}
              </span>
            ))}
          </div>
        )}
      </div>
      {isShot && <Handle type="source" position={Position.Right} />}
    </div>
    {renderMediaDetail()}
    </>
  );
}

export const ClipNode = memo(ClipNodeComponent);
