import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";

type Placement = "top" | "right" | "bottom" | "left";

type TooltipState = {
  anchor: HTMLElement;
  text: string;
  preferred: Placement;
  placement: Placement;
  ready: boolean;
  style: CSSProperties;
};

const MARGIN = 8;
const GAP = 8;
const MAX_WIDTH = 360;

function isPlacement(value: string | null): value is Placement {
  return value === "top" || value === "right" || value === "bottom" || value === "left";
}

function clamp(value: number, min: number, max: number): number {
  if (max < min) return min;
  return Math.min(max, Math.max(min, value));
}

function tooltipText(el: HTMLElement): string {
  return el.getAttribute("data-tooltip")
    || el.getAttribute("data-aa-title")
    || el.getAttribute("title")
    || "";
}

function suppressNativeTitle(el: HTMLElement): void {
  const title = el.getAttribute("title");
  if (!title) return;
  el.setAttribute("data-aa-title", title);
  el.removeAttribute("title");
}

function restoreNativeTitle(el: HTMLElement | null): void {
  if (!el) return;
  const title = el.getAttribute("data-aa-title");
  if (!title || el.hasAttribute("data-tooltip")) return;
  el.setAttribute("title", title);
  el.removeAttribute("data-aa-title");
}

function closestTooltipElement(target: EventTarget | null): HTMLElement | null {
  return target instanceof Element
    ? target.closest<HTMLElement>("[data-tooltip], [title], [data-aa-title]")
    : null;
}

export function GlobalTooltip() {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const activeAnchorRef = useRef<HTMLElement | null>(null);
  const titleOwnerRef = useRef<HTMLElement | null>(null);
  const hideTimerRef = useRef<number | null>(null);
  const [tip, setTip] = useState<TooltipState | null>(null);

  function clearHideTimer() {
    if (hideTimerRef.current == null) return;
    window.clearTimeout(hideTimerRef.current);
    hideTimerRef.current = null;
  }

  function hideTooltip() {
    clearHideTimer();
    restoreNativeTitle(titleOwnerRef.current);
    titleOwnerRef.current = null;
    setTip(null);
  }

  function showTooltip(el: HTMLElement) {
    const text = tooltipText(el).trim();
    if (!text) return;
    if (titleOwnerRef.current && titleOwnerRef.current !== el) {
      restoreNativeTitle(titleOwnerRef.current);
      titleOwnerRef.current = null;
    }
    if (el.hasAttribute("title")) {
      suppressNativeTitle(el);
      titleOwnerRef.current = el;
    }
    const placementAttr = el.getAttribute("data-tooltip-placement");
    const preferred = isPlacement(placementAttr) ? placementAttr : "top";
    clearHideTimer();
    setTip({
      anchor: el,
      text,
      preferred,
      placement: preferred,
      ready: false,
      style: {
        left: MARGIN,
        top: MARGIN,
        maxWidth: Math.max(120, Math.min(MAX_WIDTH, window.innerWidth - MARGIN * 2)),
      },
    });
  }

  useEffect(() => {
    activeAnchorRef.current = tip?.anchor ?? null;
  }, [tip?.anchor]);

  useEffect(() => {
    function onPointerOver(event: PointerEvent) {
      const el = closestTooltipElement(event.target);
      if (!el) return;
      showTooltip(el);
    }

    function onPointerOut(event: PointerEvent) {
      const current = activeAnchorRef.current;
      if (!current) return;
      const next = event.relatedTarget instanceof Node ? event.relatedTarget : null;
      if (next && current.contains(next)) return;
      hideTimerRef.current = window.setTimeout(hideTooltip, 60);
    }

    function onFocusIn(event: FocusEvent) {
      const el = closestTooltipElement(event.target);
      if (!el) return;
      showTooltip(el);
    }

    function onFocusOut(event: FocusEvent) {
      const current = activeAnchorRef.current;
      if (!current) return;
      const next = event.relatedTarget instanceof Node ? event.relatedTarget : null;
      if (next && current.contains(next)) return;
      hideTooltip();
    }

    window.addEventListener("pointerover", onPointerOver, true);
    window.addEventListener("pointerout", onPointerOut, true);
    window.addEventListener("focusin", onFocusIn, true);
    window.addEventListener("focusout", onFocusOut, true);
    window.addEventListener("resize", hideTooltip);
    window.addEventListener("scroll", hideTooltip, true);
    return () => {
      window.removeEventListener("pointerover", onPointerOver, true);
      window.removeEventListener("pointerout", onPointerOut, true);
      window.removeEventListener("focusin", onFocusIn, true);
      window.removeEventListener("focusout", onFocusOut, true);
      window.removeEventListener("resize", hideTooltip);
      window.removeEventListener("scroll", hideTooltip, true);
      hideTooltip();
    };
  }, []);

  useLayoutEffect(() => {
    if (!tip) return;
    const node = tooltipRef.current;
    if (!node) return;
    const anchorRect = tip.anchor.getBoundingClientRect();
    const widthLimit = Math.max(120, Math.min(MAX_WIDTH, window.innerWidth - MARGIN * 2));
    node.style.maxWidth = `${widthLimit}px`;
    const tipRect = node.getBoundingClientRect();
    const width = Math.min(tipRect.width, widthLimit);
    const height = tipRect.height;
    const centerX = anchorRect.left + anchorRect.width / 2;
    const centerY = anchorRect.top + anchorRect.height / 2;
    function coordinates(next: Placement): { left: number; top: number } {
      if (next === "right") {
        return { left: anchorRect.right + GAP, top: centerY - height / 2 };
      }
      if (next === "left") {
        return { left: anchorRect.left - width - GAP, top: centerY - height / 2 };
      }
      if (next === "bottom") {
        return { left: centerX - width / 2, top: anchorRect.bottom + GAP };
      }
      return { left: centerX - width / 2, top: anchorRect.top - height - GAP };
    }

    let placement = tip.preferred;
    let { left, top } = coordinates(placement);
    if (placement === "right" && left + width > window.innerWidth - MARGIN) {
      placement = "left";
      ({ left, top } = coordinates(placement));
    } else if (placement === "left" && left < MARGIN) {
      placement = "right";
      ({ left, top } = coordinates(placement));
    } else if (placement === "bottom" && top + height > window.innerHeight - MARGIN) {
      placement = "top";
      ({ left, top } = coordinates(placement));
    } else if (placement === "top" && top < MARGIN) {
      placement = "bottom";
      ({ left, top } = coordinates(placement));
    }
    left = clamp(left, MARGIN, window.innerWidth - width - MARGIN);
    top = clamp(top, MARGIN, window.innerHeight - height - MARGIN);
    const arrowX = clamp(centerX - left, 10, width - 10);
    const arrowY = clamp(centerY - top, 10, height - 10);

    setTip((current) => {
      if (!current || current.anchor !== tip.anchor || current.text !== tip.text) return current;
      return {
        ...current,
        placement,
        ready: true,
        style: {
          left,
          top,
          maxWidth: widthLimit,
          "--tooltip-arrow-x": `${arrowX}px`,
          "--tooltip-arrow-y": `${arrowY}px`,
        } as CSSProperties,
      };
    });
  }, [tip?.anchor, tip?.text, tip?.preferred, tip?.ready]);

  if (!tip) return null;

  return createPortal(
    <div
      ref={tooltipRef}
      className={`aa-tooltip aa-tooltip-${tip.placement}` + (tip.ready ? " ready" : "")}
      role="tooltip"
      style={tip.style}
    >
      {tip.text}
    </div>,
    document.body,
  );
}
