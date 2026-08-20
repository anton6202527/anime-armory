// Renderer-side access to the Electron preload bridge. This is the ONLY
// module allowed to touch window.armory — everything else goes through
// api.ts (commands) or platform helpers here (events, platform, file paths).
import type { ArmoryBridge, IpcEventName, IpcEvents } from '@shared/ipc'

declare global {
  interface Window {
    armory: ArmoryBridge
  }
}

export const bridge: ArmoryBridge = window.armory

/** Typed main→renderer event subscription; returns an unsubscribe fn. */
export function onAppEvent<E extends IpcEventName>(
  event: E,
  cb: (payload: IpcEvents[E]) => void,
): () => void {
  return bridge.on(event, cb)
}

export const isMacPlatform = bridge.platform === 'darwin'

/** Write text to the OS clipboard without granting renderer clipboard read access. */
export function writeClipboardText(text: string): void {
  bridge.writeClipboardText(text)
}

/** Absolute path of a File dropped from the OS. */
export function getPathForFile(file: File): string {
  return bridge.getPathForFile(file)
}
