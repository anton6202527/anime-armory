import { contextBridge, ipcRenderer, webUtils } from 'electron'
import {
  IPC_INVOKE_CHANNEL,
  type ArmoryBridge,
  type IpcArgs,
  type IpcChannel,
  type IpcEventName,
  type IpcEvents,
} from '@shared/ipc'

const bridge: ArmoryBridge = {
  invoke<C extends IpcChannel>(channel: C, args: IpcArgs<C>) {
    return ipcRenderer.invoke(IPC_INVOKE_CHANNEL, channel, args)
  },
  on<E extends IpcEventName>(event: E, cb: (payload: IpcEvents[E]) => void) {
    const listener = (_e: Electron.IpcRendererEvent, payload: IpcEvents[E]) => cb(payload)
    ipcRenderer.on(event, listener)
    return () => ipcRenderer.removeListener(event, listener)
  },
  platform: process.platform,
  getPathForFile(file: File) {
    return webUtils.getPathForFile(file)
  },
}

contextBridge.exposeInMainWorld('armory', bridge)

// Smoke-run diagnostics: collect DOM-level errors before any page script runs.
if (process.env.SMOKE_SHOT) {
  const errors: string[] = []
  window.addEventListener('error', (e) => {
    errors.push(`error:${e.message} @${e.filename}:${e.lineno}`)
  })
  contextBridge.exposeInMainWorld('armorySmokeErrors', () => [...errors])
}
