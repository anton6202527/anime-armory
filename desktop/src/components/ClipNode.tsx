import { memo, useEffect, useRef, useState, useSyncExternalStore, type CSSProperties, type MouseEvent as ReactMouseEvent } from "react";
import { createPortal } from "react-dom";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { getMediaPort, mediaUrl, saveCanvasCapture, subscribeMediaPort } from "../api";
import { useI18n } from "../i18n";
import type { CanvasClip, CanvasFrame } from "../types";
import { DecodedImage } from "../mediaPreview/DecodedImage";

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
  onEdit?: () => void;
};

interface MediaDetailReference {
  id: string;
  label: string;
  url: string;
  role?: string;
}

interface MediaDetailState {
  kind: "image" | "video";
  title: string;
  subtitle?: string;
  prompt?: string;
  mediaUrl?: string;
  references: MediaDetailReference[];
  anchor: { x: number; y: number };
  expanded?: boolean;
}

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
type MediaDetailToolIconName = "reference" | "mark" | "effects" | "character" | "cameraMove";

function VideoControlIcon({ name }: { name: VideoControlIconName }) {
  switch (name) {
    case "play":
      return (
        <svg className="cv-icon cv-icon-play" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
          <path className="cv-fill" d="M13.5 8.6 31.8 20 13.5 31.4Z" />
        </svg>
      );
    case "pause":
      return (
        <svg className="cv-icon cv-icon-pause" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
          <rect className="cv-fill" x="12" y="9" width="5.8" height="22" rx="1.4" />
          <rect className="cv-fill" x="22.2" y="9" width="5.8" height="22" rx="1.4" />
        </svg>
      );
    case "volumeOn":
      return (
        <svg className="cv-icon cv-icon-volume-on" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
          <path className="cv-fill" d="M5.5 15.2h7.2L22 7.4v25.2l-9.3-7.8H5.5Z" />
          <path className="cv-stroke" d="M26.2 14.1a8 8 0 0 1 0 11.8" />
          <path className="cv-stroke" d="M30.4 10.2a13.8 13.8 0 0 1 0 19.6" />
        </svg>
      );
    case "volumeOff":
      return (
        <svg className="cv-icon cv-icon-volume-off" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
          <path className="cv-fill" d="M5.2 15.2h7.2L21.8 7.4v25.2l-9.4-7.8H5.2Z" />
          <path className="cv-stroke muted-wave" d="M26.2 14.1a8 8 0 0 1 0 11.8" />
          <path className="cv-stroke muted-wave" d="M30.4 10.2a13.8 13.8 0 0 1 0 19.6" />
          <path className="cv-stroke cv-mute-slash" d="M7.4 7.4 33.2 33.2" />
        </svg>
      );
    case "camera":
      return (
        <svg className="cv-icon cv-icon-camera" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
          <path className="cv-stroke" d="M8.3 14.3h5.8l2.3-3.6h7.2l2.3 3.6h5.8a3.2 3.2 0 0 1 3.2 3.2v11.2a3.2 3.2 0 0 1-3.2 3.2H8.3a3.2 3.2 0 0 1-3.2-3.2V17.5a3.2 3.2 0 0 1 3.2-3.2Z" />
          <circle className="cv-stroke" cx="20" cy="23.2" r="6.2" />
        </svg>
      );
  }
}

function MediaDetailExpandIcon({ expanded }: { expanded: boolean }) {
  if (expanded) {
    return (
      <svg className="media-detail-expand-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M9.5 4.5v5h-5" />
        <path d="M4.8 9.2 10.7 3.3" />
        <path d="M14.5 19.5v-5h5" />
        <path d="M19.2 14.8 13.3 20.7" />
      </svg>
    );
  }
  return (
    <svg className="media-detail-expand-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M14.5 4.5h5v5" />
      <path d="M19.2 4.8 13.3 10.7" />
      <path d="M9.5 19.5h-5v-5" />
      <path d="M4.8 19.2 10.7 13.3" />
    </svg>
  );
}

function MediaDetailToolIcon({ name }: { name: MediaDetailToolIconName }) {
  switch (name) {
    case "reference":
      return (
        <svg className="media-detail-tool-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d="M10 3.2v13.6M3.2 10h13.6" />
        </svg>
      );
    case "mark":
      return (
        <svg className="media-detail-tool-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d="M15.4 8.4c0 4.1-5.4 8-5.4 8s-5.4-3.9-5.4-8a5.4 5.4 0 0 1 10.8 0Z" />
          <circle cx="10" cy="8.4" r="1.6" />
          <path d="M15.8 13.5v3.4M14.1 15.2h3.4" />
        </svg>
      );
    case "effects":
      return (
        <svg className="media-detail-tool-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d="M4.1 7.1h11.8v8.3H4.1Z" />
          <path d="m7 7.1 1.2-2h3.6l1.2 2" />
          <circle cx="10" cy="11.2" r="2.3" />
        </svg>
      );
    case "character":
      return (
        <svg className="media-detail-tool-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d="M10 3.2 15.5 5.6v4.1c0 3.5-2.3 5.8-5.5 7.1-3.2-1.3-5.5-3.6-5.5-7.1V5.6Z" />
          <path d="m7.7 9.9 1.6 1.6 3.2-3.4" />
        </svg>
      );
    case "cameraMove":
      return (
        <svg className="media-detail-tool-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d="M3.8 6.2h8.1v7.6H3.8Z" />
          <path d="m11.9 8.2 4.3-2.4v8.4l-4.3-2.4" />
        </svg>
      );
  }
}

const CanvasVideoPlayer = memo(function CanvasVideoPlayer(props: {
  videoUrl: string;
  posterUrl: string;
  label: string;
  rootPath?: string;
  durationHint?: number;
  noVideoLabel: string;
  onOpenDetail: (event: ReactMouseEvent<HTMLElement>) => void;
}) {
  const { videoUrl, posterUrl, label, rootPath, durationHint, noVideoLabel, onOpenDetail } = props;
  const { t } = useI18n();
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [activated, setActivated] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [volumeOpen, setVolumeOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [savingCapture, setSavingCapture] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(durationHint ?? 0);
  const lastTimeUpdateRef = useRef(0);

  useEffect(() => {
    setPlaying(false);
    setActivated(false);
    setCurrent(0);
    setDuration(durationHint ?? 0);
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
    setMuted(next <= 0);
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
      setCaptureOpen(false);
      if (wasPlaying) await video.play().catch(() => undefined);
    }
  }

  const progress = duration > 0 ? Math.max(0, Math.min(100, (current / duration) * 100)) : 0;
  const rangeStyle = { "--video-progress": `${progress}%` } as CSSProperties;
  const volumeValue = muted ? 0 : volume;

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
        <span className="canvas-video-dormant-play"><VideoControlIcon name="play" /></span>
      </button>
    );
  }

  return (
    <>
      <div
        ref={playerRef}
        className="canvas-video-player"
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
          preload="none"
          muted={muted}
          onLoadedMetadata={(event) => {
            const nextDuration = event.currentTarget.duration;
            if (Number.isFinite(nextDuration)) setDuration(nextDuration);
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
          <div
            className="canvas-video-volume"
            onPointerEnter={() => setVolumeOpen(true)}
            onPointerLeave={() => setVolumeOpen(false)}
          >
            {volumeOpen && (
              <div className="canvas-video-volume-popover">
                <span>{Math.round(volumeValue * 100)}</span>
                <input
                  className="canvas-video-volume-range"
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={volumeValue}
                  aria-label={muted ? t("canvas.unmuteVideo") : t("canvas.muteVideo")}
                  onChange={(event) => changeVolume(Number(event.target.value))}
                />
              </div>
            )}
            <button
              type="button"
              className="canvas-video-icon"
              aria-label={muted ? t("canvas.unmuteVideo") : t("canvas.muteVideo")}
              onClick={() => {
                setVolumeOpen(true);
                setMuted((value) => !value);
              }}
            >
              <VideoControlIcon name={muted ? "volumeOff" : "volumeOn"} />
            </button>
          </div>
          <div className="canvas-video-capture">
            {captureOpen && (
              <div
                className="canvas-video-capture-menu"
                onPointerDown={(event) => event.stopPropagation()}
                onClick={(event) => event.stopPropagation()}
              >
                <button type="button" disabled={savingCapture} onClick={() => captureFrame("first")}>{t("canvas.captureFirstFrame")}</button>
                <button type="button" disabled={savingCapture} onClick={() => captureFrame("last")}>{t("canvas.captureLastFrame")}</button>
                <button type="button" disabled={savingCapture} onClick={() => captureFrame("current")}>{t("canvas.captureCurrentFrame")}</button>
              </div>
            )}
            <button
              type="button"
              className="canvas-video-icon canvas-video-capture-btn"
              aria-label={t("canvas.captureFrame")}
              aria-expanded={captureOpen}
              onClick={() => setCaptureOpen((value) => !value)}
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
  const [mediaDetail, setMediaDetail] = useState<MediaDetailState | null>(null);
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

  function mediaRefsFromFrames(sourceFrames: CanvasFrame[]): MediaDetailReference[] {
    const seen = new Set<string>();
    return sourceFrames.flatMap((frame, index) => {
      if (!frame.exists || !frame.abs || seen.has(frame.abs)) return [];
      seen.add(frame.abs);
      return [{
        id: `${frame.role || "frame"}-${frame.abs}-${index}`,
        label: frame.label || t("canvas.imageNumber", { count: index + 1 }),
        role: frame.role,
        url: withRevision(mediaUrl(frame.abs), frame.revision),
      }];
    }).slice(0, 14);
  }

  function mediaRefsFromAssets(assets: SharedAssetImage[]): MediaDetailReference[] {
    return assets.flatMap((asset, index) => {
      if (!asset.exists || !asset.abs) return [];
      return [{
        id: asset.id,
        label: asset.label || t("canvas.imageNumber", { count: index + 1 }),
        role: asset.roles[0],
        url: withRevision(mediaUrl(asset.abs), asset.revision),
      }];
    }).slice(0, 14);
  }

  function openFrameDetail(frame: CanvasFrame, event: ReactMouseEvent<HTMLElement>) {
    if (!frame.exists || !frame.abs) return;
    const referenceSource = referenceFrames.length ? [frame, ...referenceFrames] : [frame, ...shownFrames];
    setMediaDetail({
      kind: "image",
      title: frame.label || clip.label,
      subtitle: clip.number != null ? `${clip.number}. ${clip.label}` : clip.label,
      prompt: detailPrompt(frame),
      mediaUrl: withRevision(mediaUrl(frame.abs), frame.revision),
      references: mediaRefsFromFrames(referenceSource),
      anchor: detailAnchor(event),
    });
  }

  function openAssetDetail(asset: SharedAssetImage, event: ReactMouseEvent<HTMLElement>) {
    if (!asset.exists || !asset.abs) return;
    setMediaDetail({
      kind: "image",
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
      title: clip.label,
      subtitle: t("canvas.characterLane"),
      prompt: detailPrompt(),
      mediaUrl: refImageUrl,
      references: [{
        id: `${clip.id}-reference`,
        label: clip.label,
        role: "reference",
        url: refImageUrl,
      }],
      anchor: detailAnchor(event),
    });
  }

  function openVideoDetail(event: ReactMouseEvent<HTMLElement>) {
    const referenceSource = posterFrame ? [posterFrame, ...referenceFrames] : referenceFrames;
    setMediaDetail({
      kind: "video",
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
    if (!mediaDetail) return null;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const expanded = Boolean(mediaDetail.expanded);
    const width = expanded
      ? Math.min(1600, Math.max(760, viewportWidth - 96))
      : Math.min(1320, Math.max(640, viewportWidth - 160));
    const height = expanded
      ? Math.min(1160, Math.max(520, viewportHeight - 96))
      : Math.min(560, Math.max(380, viewportHeight - 112));
    const left = Math.max(24, (viewportWidth - width) / 2);
    const top = expanded
      ? Math.max(24, Math.min(32, (viewportHeight - height) / 2))
      : Math.max(24, Math.min(44, (viewportHeight - height) / 2));
    const cardStyle: CSSProperties = { width, height, maxHeight: height, left, top };
    const references = mediaDetail.references.length
      ? mediaDetail.references
      : mediaDetail.mediaUrl
        ? [{
            id: "current-media",
            label: mediaDetail.kind === "video" ? t("canvas.video") : t("canvas.imageNumber", { count: 1 }),
            url: mediaDetail.mediaUrl,
          }]
        : [];

    return createPortal(
      <div
        className="canvas-media-detail-backdrop"
        role="dialog"
        aria-modal="true"
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => {
          event.stopPropagation();
          setMediaDetail(null);
        }}
      >
        <div
          className={"canvas-media-detail-card" + (expanded ? " expanded" : "")}
          style={cardStyle}
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => event.stopPropagation()}
        >
          <div className="canvas-media-detail-head">
            <div className="canvas-media-detail-actions">
              <span className="canvas-media-detail-pill"><MediaDetailToolIcon name="reference" />{t("canvas.mediaDetailReference")}</span>
              <span className="canvas-media-detail-pill"><MediaDetailToolIcon name="mark" />{t("canvas.mediaDetailMark")}</span>
              <span className="canvas-media-detail-pill"><MediaDetailToolIcon name="effects" />{t("canvas.mediaDetailEffects")}</span>
              <span className="canvas-media-detail-pill"><MediaDetailToolIcon name="character" />{t("canvas.mediaDetailCharacterLibrary")}</span>
              <span className="canvas-media-detail-pill"><MediaDetailToolIcon name="cameraMove" />{t("canvas.mediaDetailCameraMove")}</span>
            </div>
            <button
              type="button"
              className="canvas-media-detail-expand-btn"
              aria-label={expanded ? t("canvas.mediaDetailCollapse") : t("canvas.mediaDetailExpand")}
              title={expanded ? t("canvas.mediaDetailCollapse") : t("canvas.mediaDetailExpand")}
              onClick={() => setMediaDetail((current) => current ? { ...current, expanded: !current.expanded } : current)}
            >
              <MediaDetailExpandIcon expanded={expanded} />
            </button>
          </div>
          {references.length > 0 && (
            <div className="canvas-media-detail-refs">
              {references.map((reference, index) => (
                <div className="canvas-media-detail-ref" key={reference.id}>
                  <DecodedImage src={reference.url} alt={reference.label} maxDecodeDimension={256} />
                  <span className="canvas-media-detail-ref-index">{index + 1}</span>
                  {reference.role && <span className="canvas-media-detail-ref-role">{reference.role}</span>}
                </div>
              ))}
            </div>
          )}
          <div className="canvas-media-detail-text">
            <p>{mediaDetail.prompt || t("canvas.mediaDetailNoPrompt")}</p>
          </div>
          <div className="canvas-media-detail-footer">
            <span>{mediaDetail.kind === "video" ? t("canvas.video") : t("canvas.mediaDetailReference")}</span>
            <span>·</span>
            <span>{references.length}{t("canvas.mediaDetailRefUnit")}</span>
            {clip.duration != null && (
              <>
                <span>·</span>
                <span>{clip.duration}s</span>
              </>
            )}
            <span className="canvas-media-detail-footer-spacer" />
            <span className="canvas-media-detail-send">↑</span>
          </div>
        </div>
      </div>,
      document.body,
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
