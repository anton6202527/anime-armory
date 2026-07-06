const GLYPHS = {
  files: "\ueaf0",
  wrench: "\ueb65",
  sourceControl: "\uea68",
  deviceCameraVideo: "\uead9",
  checklist: "\ueab3",
  warning: "\uea6c",
  chevronLeft: "\ueab5",
  chevronRight: "\ueab6",
  settingsGear: "\ueb51",
} as const;

const CLASS_NAMES = {
  files: "files",
  wrench: "wrench",
  sourceControl: "source-control",
  deviceCameraVideo: "device-camera-video",
  checklist: "checklist",
  warning: "warning",
  chevronLeft: "chevron-left",
  chevronRight: "chevron-right",
  settingsGear: "settings-gear",
} as const satisfies Record<keyof typeof GLYPHS, string>;

export type CodiconName = keyof typeof GLYPHS;

export function Codicon({ name, className = "" }: { name: CodiconName; className?: string }) {
  const classes = `codicon codicon-${CLASS_NAMES[name]} aa-codicon${className ? ` ${className}` : ""}`;
  return (
    <span className={classes} aria-hidden="true">
      {GLYPHS[name]}
    </span>
  );
}
