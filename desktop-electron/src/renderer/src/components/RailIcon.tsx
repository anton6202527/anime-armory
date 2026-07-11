import type { ReactNode } from "react";

export type RailIconName = "files" | "search" | "changes" | "skills" | "canvas" | "review";

const ICON_CLASS: Record<RailIconName, string> = {
  files: "rail-icon-files",
  search: "rail-icon-search",
  changes: "rail-icon-changes",
  skills: "rail-icon-skills",
  canvas: "rail-icon-canvas",
  review: "rail-icon-review",
};

function Svg({
  name,
  children,
}: {
  name: RailIconName;
  children: ReactNode;
}) {
  return (
    <svg
      className={`rail-icon ${ICON_CLASS[name]}`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export function RailIcon({ name }: { name: RailIconName }) {
  switch (name) {
    case "files":
      return (
        <Svg name={name}>
          <path d="M7.2 4.2h7.2l3.4 3.5v11.9H7.2z" />
          <path d="M14.1 4.2v3.8h3.7" />
          <path d="M5.1 6.5v13.3h10.4" />
        </Svg>
      );
    case "search":
      return (
        <Svg name={name}>
          <circle cx="10.7" cy="10.7" r="5.6" />
          <path d="M14.8 14.8l4.6 4.6" />
        </Svg>
      );
    case "changes":
      return (
        <Svg name={name}>
          <circle cx="7.1" cy="5.9" r="2" />
          <circle cx="7.1" cy="18.1" r="2" />
          <circle cx="17.2" cy="12" r="2" />
          <path d="M7.1 7.9v8.2" />
          <path d="M8.8 7.1c3.6 1.1 5.7 2.5 7 3.7" />
        </Svg>
      );
    case "skills":
      return (
        <Svg name={name}>
          <path d="M14.6 5.4a4.2 4.2 0 0 1 5.2-.8l-2.9 2.9 1.6 1.6 2.9-2.9a4.2 4.2 0 0 1-5.2 5.2l-7.7 7.7a2.2 2.2 0 0 1-3.1-3.1l7.7-7.7a4.2 4.2 0 0 1 1.5-2.9z" />
          <circle cx="7" cy="17.5" r=".7" />
        </Svg>
      );
    case "canvas":
      return (
        <Svg name={name}>
          <rect x="4.5" y="5" width="5.7" height="5" rx="1.2" />
          <rect x="13.8" y="5" width="5.7" height="5" rx="1.2" />
          <rect x="4.5" y="14" width="5.7" height="5" rx="1.2" />
          <rect x="13.8" y="14" width="5.7" height="5" rx="1.2" />
          <path d="M10.2 7.5h3.6M7.4 10v4M16.6 10v4M10.2 16.5h3.6" />
        </Svg>
      );
    case "review":
      return (
        <Svg name={name}>
          <path d="M8.8 4.6h6.4" />
          <path d="M10 4.6v4.3l-4.5 8.2a2 2 0 0 0 1.8 3h9.4a2 2 0 0 0 1.8-3L14 8.9V4.6" />
          <path d="M7.6 15.1h8.8" />
          <path d="M9.2 18h5.6" />
        </Svg>
      );
  }
}
