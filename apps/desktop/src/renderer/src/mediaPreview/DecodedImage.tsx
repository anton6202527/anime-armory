import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { resolveImagePreviewPlugin } from "./registry";
import { imageDecodeRuntime } from "./runtime";

export type DecodedImageMetadata = {
  width: number;
  height: number;
  strategy: "worker-bitmap" | "native-image";
};

export function DecodedImage({
  src,
  alt,
  className = "",
  style,
  loading = "lazy",
  maxDecodeDimension = 0,
  onDecoded,
  onError,
}: {
  src: string;
  alt: string;
  className?: string;
  style?: CSSProperties;
  loading?: "eager" | "lazy";
  maxDecodeDimension?: number;
  onDecoded?: (metadata: DecodedImageMetadata) => void;
  onError?: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const onDecodedRef = useRef(onDecoded);
  const onErrorRef = useRef(onError);
  const plugin = useMemo(() => resolveImagePreviewPlugin(src), [src]);
  const [visible, setVisible] = useState(loading === "eager");
  const [nativeFallback, setNativeFallback] = useState(plugin.strategy === "native-image");

  useEffect(() => {
    onDecodedRef.current = onDecoded;
    onErrorRef.current = onError;
  }, [onDecoded, onError]);

  useEffect(() => {
    setNativeFallback(plugin.strategy === "native-image");
    setVisible(loading === "eager");
  }, [loading, plugin.id, src]);

  useEffect(() => {
    if (visible || nativeFallback) return;
    const element = canvasRef.current;
    if (!element || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      setVisible(true);
      observer.disconnect();
    }, { rootMargin: "480px" });
    observer.observe(element);
    return () => observer.disconnect();
  }, [nativeFallback, visible]);

  useEffect(() => {
    if (!src || !visible || nativeFallback || plugin.strategy !== "worker-bitmap") return;
    let alive = true;
    const lease = imageDecodeRuntime.acquire(src, maxDecodeDimension);
    lease.promise
      .then((result) => {
        if (!alive) return;
        if (result.kind === "native") {
          setNativeFallback(true);
          return;
        }
        const canvas = canvasRef.current;
        if (!canvas) return;
        canvas.width = result.width;
        canvas.height = result.height;
        const context = canvas.getContext("2d", { alpha: true, desynchronized: true });
        if (!context) throw new Error("2D canvas unavailable");
        context.clearRect(0, 0, result.width, result.height);
        context.drawImage(result.bitmap, 0, 0);
        canvas.dataset.ready = "true";
        onDecodedRef.current?.({
          width: result.originalWidth,
          height: result.originalHeight,
          strategy: "worker-bitmap",
        });
      })
      .catch((error) => {
        if (!alive || (error instanceof DOMException && error.name === "AbortError")) return;
        setNativeFallback(true);
      });
    return () => {
      alive = false;
      lease.release();
    };
  }, [maxDecodeDimension, nativeFallback, plugin.strategy, src, visible]);

  const mergedClassName = `decoded-image ${className}`.trim();
  if (nativeFallback) {
    return (
      <img
        src={src}
        alt={alt}
        className={mergedClassName}
        style={style}
        loading={loading}
        decoding="async"
        draggable={false}
        onLoad={(event) => onDecodedRef.current?.({
          width: event.currentTarget.naturalWidth || event.currentTarget.width || 1,
          height: event.currentTarget.naturalHeight || event.currentTarget.height || 1,
          strategy: "native-image",
        })}
        onError={() => onErrorRef.current?.()}
      />
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className={mergedClassName}
      style={style}
      role="img"
      aria-label={alt}
      data-ready="false"
    />
  );
}

