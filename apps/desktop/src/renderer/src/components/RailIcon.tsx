import { Codicon, type CodiconName } from "./Codicon";

export type RailIconName = "files" | "search" | "changes" | "skills" | "canvas" | "review";

const ICON_NAME: Record<RailIconName, CodiconName> = {
  files: "files",
  search: "search",
  changes: "sourceControl",
  skills: "wrench",
  canvas: "layout",
  review: "beaker",
};

export function RailIcon({ name }: { name: RailIconName }) {
  return <Codicon name={ICON_NAME[name]} className={`rail-icon rail-icon-${name}`} />;
}
