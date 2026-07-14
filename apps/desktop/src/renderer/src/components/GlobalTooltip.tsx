import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";

type Placement = "top" | "right" | "bottom" | "left";

type TooltipState = {
  anchor: HTMLElement;
  text: string;
  preferred: Placement;
  align: "center" | "corner";
  anchorPoint: { x: number; y: number } | null;
  placement: Placement;
  ready: boolean;
  style: CSSProperties;
};

const MARGIN = 8;
const GAP = 8;
const CURSOR_GAP_X = 12;
const CURSOR_GAP_Y = 16;
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

function suppressNativeTitles(root: ParentNode = document): void {
  if (root instanceof HTMLElement) suppressNativeTitle(root);
  root.querySelectorAll?.<HTMLElement>("[title]").forEach(suppressNativeTitle);
}

function closestTooltipElement(target: EventTarget | null): HTMLElement | null {
  return target instanceof Element
    ? target.closest<HTMLElement>("[data-tooltip], [title], [data-aa-title]")
    : null;
}

function eventPoint(event: Event): { x: number; y: number } | null {
  return event instanceof MouseEvent
    ? { x: event.clientX, y: event.clientY }
    : null;
}

export function GlobalTooltip() {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const activeAnchorRef = useRef<HTMLElement | null>(null);
  const hideTimerRef = useRef<number | null>(null);
  const [tip, setTip] = useState<TooltipState | null>(null);

  function clearHideTimer() {
    if (hideTimerRef.current == null) return;
    window.clearTimeout(hideTimerRef.current);
    hideTimerRef.current = null;
  }

  function hideTooltip() {
    clearHideTimer();
    setTip(null);
  }

  function showTooltip(el: HTMLElement, point: { x: number; y: number } | null = null) {
    const text = tooltipText(el).trim();
    if (!text) return;
    suppressNativeTitle(el);
    const placementAttr = el.getAttribute("data-tooltip-placement");
    const hasExplicitPlacement = isPlacement(placementAttr);
    const preferred = hasExplicitPlacement ? placementAttr : "right";
    clearHideTimer();
    setTip({
      anchor: el,
      text,
      preferred,
      align: hasExplicitPlacement ? "center" : "corner",
      anchorPoint: hasExplicitPlacement ? null : point,
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
    suppressNativeTitles();
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "attributes" && mutation.target instanceof HTMLElement) {
          suppressNativeTitle(mutation.target);
          continue;
        }
        for (const node of mutation.addedNodes) {
          if (node instanceof HTMLElement) suppressNativeTitles(node);
        }
      }
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["title"],
      childList: true,
      subtree: true,
    });

    function onHoverIn(event: Event) {
      const el = closestTooltipElement(event.target);
      if (!el) return;
      showTooltip(el, eventPoint(event));
    }

    function onHoverOut(event: Event) {
      const current = activeAnchorRef.current;
      if (!current) return;
      const next = "relatedTarget" in event && event.relatedTarget instanceof Node ? event.relatedTarget : null;
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

    function onPointerMove(event: Event) {
      const current = activeAnchorRef.current;
      if (!current) return;
      const el = closestTooltipElement(event.target);
      if (el !== current) return;
      const point = eventPoint(event);
      if (!point) return;
      setTip((existing) => {
        if (!existing || existing.anchor !== current || existing.align !== "corner" || !existing.anchorPoint) {
          return existing;
        }
        if (
          Math.abs(existing.anchorPoint.x - point.x) < 2 &&
          Math.abs(existing.anchorPoint.y - point.y) < 2
        ) {
          return existing;
        }
        return { ...existing, anchorPoint: point, ready: false };
      });
    }

    window.addEventListener("pointerover", onHoverIn, true);
    window.addEventListener("pointerout", onHoverOut, true);
    window.addEventListener("pointermove", onPointerMove, true);
    window.addEventListener("mouseover", onHoverIn, true);
    window.addEventListener("mouseout", onHoverOut, true);
    window.addEventListener("focusin", onFocusIn, true);
    window.addEventListener("focusout", onFocusOut, true);
    window.addEventListener("resize", hideTooltip);
    window.addEventListener("scroll", hideTooltip, true);
    return () => {
      window.removeEventListener("pointerover", onHoverIn, true);
      window.removeEventListener("pointerout", onHoverOut, true);
      window.removeEventListener("pointermove", onPointerMove, true);
      window.removeEventListener("mouseover", onHoverIn, true);
      window.removeEventListener("mouseout", onHoverOut, true);
      window.removeEventListener("focusin", onFocusIn, true);
      window.removeEventListener("focusout", onFocusOut, true);
      window.removeEventListener("resize", hideTooltip);
      window.removeEventListener("scroll", hideTooltip, true);
      observer.disconnect();
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
    const align = tip.align;
    const anchorPoint = tip.anchorPoint;
    function coordinates(next: Placement): { left: number; top: number } {
      if (anchorPoint && align === "corner") {
        if (next === "left") {
          return { left: anchorPoint.x - width - CURSOR_GAP_X, top: anchorPoint.y + CURSOR_GAP_Y };
        }
        if (next === "top") {
          return { left: anchorPoint.x + CURSOR_GAP_X, top: anchorPoint.y - height - CURSOR_GAP_Y };
        }
        if (next === "bottom") {
          return { left: anchorPoint.x + CURSOR_GAP_X, top: anchorPoint.y + CURSOR_GAP_Y };
        }
        return { left: anchorPoint.x + CURSOR_GAP_X, top: anchorPoint.y + CURSOR_GAP_Y };
      }
      if (next === "right") {
        return {
          left: anchorRect.right + GAP,
          top: align === "corner" ? anchorRect.bottom + 2 : centerY - height / 2,
        };
      }
      if (next === "left") {
        return {
          left: anchorRect.left - width - GAP,
          top: align === "corner" ? anchorRect.bottom + 2 : centerY - height / 2,
        };
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
    const arrowSourceX = anchorPoint?.x ?? centerX;
    const arrowSourceY = anchorPoint?.y ?? centerY;
    const arrowX = clamp(arrowSourceX - left, 10, width - 10);
    const arrowY = clamp(arrowSourceY - top, 10, height - 10);

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
  }, [tip?.anchor, tip?.text, tip?.preferred, tip?.align, tip?.anchorPoint, tip?.ready]);

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
