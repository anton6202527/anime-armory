import { useEffect, useState } from "react";
import { useI18n } from "../i18n";

export function VideoPreview({ src }: { src: string }) {
  const { t } = useI18n();
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => setState("loading"), [src]);

  return (
    <div className="files-video-preview">
      {state === "loading" && <div className="files-video-status">{t("files.videoPreparing")}</div>}
      {state === "error" && <div className="files-video-status error">{t("files.videoFailed")}</div>}
      <video
        src={src}
        controls
        preload="metadata"
        onCanPlay={() => setState("ready")}
        onError={() => setState("error")}
      />
    </div>
  );
}
