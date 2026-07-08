const GLYPHS = {
  add: "\uea60",
  files: "\ueaf0",
  file: "\uea7b",
  close: "\uea76",
  discard: "\ueae2",
  goToFile: "\uea94",
  trash: "\uea81",
  wrench: "\ueb65",
  sourceControl: "\uea68",
  deviceCameraVideo: "\uead9",
  beaker: "\uea79",
  layout: "\uebeb",
  project: "\ueb30",
  checklist: "\ueab3",
  warning: "\uea6c",
  search: "\uea6d",
  refresh: "\ueb37",
  clearAll: "\ueabf",
  collapseAll: "\ueac5",
  caseSensitive: "\ueab1",
  wholeWord: "\ueb7e",
  regex: "\ueb38",
  preserveCase: "\ueb2e",
  replaceAll: "\ueb3c",
  more: "\uea7c",
  sparkle: "\uec10",
  chevronDown: "\ueab4",
  chevronLeft: "\ueab5",
  chevronRight: "\ueab6",
  settingsGear: "\ueb51",
  settings: "\ueb52",
  bell: "\uea8f",
} as const;

const CLASS_NAMES = {
  add: "add",
  files: "files",
  file: "file",
  close: "close",
  discard: "discard",
  goToFile: "go-to-file",
  trash: "trash",
  wrench: "wrench",
  sourceControl: "source-control",
  deviceCameraVideo: "device-camera-video",
  beaker: "beaker",
  layout: "layout",
  project: "project",
  checklist: "checklist",
  warning: "warning",
  search: "search",
  refresh: "refresh",
  clearAll: "clear-all",
  collapseAll: "collapse-all",
  caseSensitive: "case-sensitive",
  wholeWord: "whole-word",
  regex: "regex",
  preserveCase: "preserve-case",
  replaceAll: "replace-all",
  more: "more",
  sparkle: "sparkle",
  chevronDown: "chevron-down",
  chevronLeft: "chevron-left",
  chevronRight: "chevron-right",
  settingsGear: "settings-gear",
  settings: "settings",
  bell: "bell",
} as const satisfies Record<keyof typeof GLYPHS, string>;

export type CodiconName = keyof typeof GLYPHS;

export function Codicon({ name, className = "" }: { name: CodiconName; className?: string }) {
  const classes = `aa-codicon aa-codicon-${CLASS_NAMES[name]}${className ? ` ${className}` : ""}`;
  return (
    <span className={classes} aria-hidden="true">
      {GLYPHS[name]}
    </span>
  );
}
