import type {
  AgentInfo,
  CanvasData,
  CanvasLayout,
  CanvasNodePosition,
  ClipEditData,
  ClipEditPatch,
  CloudAuthStatus,
  CloudProjectBinding,
  CloudProjectInfo,
  CloudPublicConfig,
  CloudSyncProgress,
  CloudSyncResult,
  DemoDownloadInfo,
  DemoInstallResult,
  EpisodeWorkspace,
  ImportWorkSourcesResult,
  LineInfo,
  QualityInsights,
  SkillInfo,
  SkillTreeEntry,
  WorkChangeDetail,
  WorkChanges,
  WorkChangeSummary,
  WorkDirListing,
  WorkFileWriteResult,
  WorkSearchResponse,
  WorkSnapshot,
} from './types'

/**
 * The complete typed IPC surface. One entry per command: `(args) => result`.
 * Main registers a handler per key; the renderer client is derived from the
 * same map, so a channel-name typo or arg-shape drift is a compile error —
 * this replaces the Tauri app's stringly-typed `invoke()` calls.
 */
export interface IpcCommands {
  // workspace / lines
  'workspace.scan': (a: { repoRoot: string }) => LineInfo[]
  'workspace.default': (a?: undefined) => string
  'workspace.resolveRepo': (a: { devRepo: string }) => string
  'workspace.createWork': (a: { dir: string; repoRoot: string; name: string }) => string
  'workspace.deleteWork': (a: { workspaceRoot: string; repoRoot: string; path: string }) => void
  'workspace.pickDirectory': (a: { title?: string }) => string | null

  // demos
  'demos.list': (a: { workspaceRoot: string }) => DemoDownloadInfo[]
  'demos.install': (a: { workspaceRoot: string; rel: string }) => DemoInstallResult
  'demos.seed': (a: { workspaceRoot: string }) => number

  // authenticated cloud projects and explicit work sync
  'cloud.authStatus': (a: { config: CloudPublicConfig }) => CloudAuthStatus
  'cloud.signIn': (a: { config: CloudPublicConfig; email: string; password: string }) => CloudAuthStatus
  'cloud.signOut': (a: { config: CloudPublicConfig }) => void
  'cloud.listProjects': (a: { config: CloudPublicConfig }) => CloudProjectInfo[]
  'cloud.getBinding': (a: { root: string }) => CloudProjectBinding | null
  'cloud.bindProject': (a: {
    config: CloudPublicConfig
    root: string
    projectId: string
  }) => CloudProjectBinding
  'cloud.unbindProject': (a: { root: string }) => void
  'cloud.syncUpload': (a: {
    config: CloudPublicConfig
    root: string
    projectName: string
    operationId: string
  }) => CloudSyncResult
  'cloud.syncDownload': (a: {
    config: CloudPublicConfig
    root: string
    projectId: string
    operationId: string
  }) => CloudSyncResult
  'cloud.cancelSync': (a: { operationId: string }) => void

  // skills
  'skills.list': (a: { repoRoot: string; line: string }) => SkillInfo[]
  'skills.tree': (a: { repoRoot: string; dir: string }) => SkillTreeEntry[]
  'skills.readFile': (a: { repoRoot: string; dir: string; rel: string }) => string

  // work file tree / files
  'work.tree': (a: { root: string }) => SkillTreeEntry[]
  'work.dir': (a: { root: string; rel?: string; offset?: number; limit?: number }) => WorkDirListing
  'work.snapshot': (a: { root: string }) => WorkSnapshot
  'work.isEmpty': (a: { root: string }) => boolean
  'work.readFile': (a: { root: string; rel: string }) => string
  'work.readDocx': (a: { root: string; rel: string }) => string
  'work.writeFile': (a: {
    root: string
    rel: string
    text: string
    expectedMtime?: number | null
  }) => WorkFileWriteResult
  'work.saveCanvasCapture': (a: {
    root: string
    imageData: string
    label: string
  }) => { rel: string; path: string }
  'work.createEntry': (a: {
    root: string
    parentRel: string
    name: string
    kind: 'file' | 'folder'
  }) => string
  'work.renameEntry': (a: { root: string; rel: string; newName: string }) => string
  'work.deleteEntry': (a: { root: string; rel: string }) => void
  'work.importSources': (a: { root: string; sources: string[] }) => string[]
  'work.importN2dNovel': (a: { root: string; sources: string[] }) => ImportWorkSourcesResult
  'work.revealEntry': (a: { root: string; rel: string }) => void
  'work.openEntry': (a: { root: string; rel: string }) => void
  'work.search': (a: {
    root: string
    query: string
    caseSensitive?: boolean
    wholeWord?: boolean
    useRegex?: boolean
  }) => WorkSearchResponse
  'work.pickImportFiles': (a: { extensions: string[]; title?: string }) => string[]

  // change tracking (baseline)
  'changes.summary': (a: { root: string }) => WorkChangeSummary
  'changes.list': (a: { root: string }) => WorkChanges
  'changes.read': (a: { root: string; rel: string }) => WorkChangeDetail
  'changes.archiveAll': (a: { root: string }) => WorkChangeSummary
  'changes.archiveOne': (a: { root: string; rel: string }) => WorkChangeSummary
  'changes.restoreAll': (a: { root: string }) => WorkChangeSummary
  'changes.restoreOne': (a: { root: string; rel: string }) => WorkChangeSummary
  'changes.deleted': (a: { root: string }) => string[]

  // canvas / pipeline
  'canvas.read': (a: { root: string; ep: string }) => CanvasData
  'canvas.readLayout': (a: { root: string; ep: string }) => CanvasLayout
  'canvas.writeLayout': (a: { root: string; ep: string; nodes: CanvasNodePosition[] }) => void
  'canvas.readClipEdit': (a: {
    root: string
    ep: string
    clipId: string
    number?: number | null
  }) => ClipEditData
  'canvas.writeClipEdit': (a: {
    root: string
    ep: string
    clipId: string
    number?: number | null
    patch: Partial<ClipEditPatch>
  }) => ClipEditData
  'canvas.readEpisodeWorkspace': (a: { root: string; ep: string }) => EpisodeWorkspace | null
  'quality.read': (a: { root: string; line: string; ep?: string | null }) => QualityInsights
  'pipeline.nextAction': (a: { repoRoot: string; root: string; ep: string }) => string

  // agents
  'agents.detect': (a?: { force?: boolean }) => AgentInfo[]

  // pty
  'pty.spawn': (a: { cwd: string; rows: number; cols: number }) => number
  'pty.write': (a: { id: number; data: string }) => void
  'pty.resize': (a: { id: number; rows: number; cols: number }) => void
  'pty.kill': (a: { id: number }) => void

  // fs watch
  'watch.root': (a: { root: string }) => void
  'watch.unroot': (a: { root: string }) => void

  // media server
  'media.start': (a?: undefined) => number
  'media.allowRoot': (a: { root: string }) => void

  // app / shell
  'app.setLanguage': (a: { language: string }) => void
  'app.setTerminalVisible': (a: { visible: boolean }) => void
  'app.setRecentWorks': (a: { works: Array<{ path: string; name: string }> }) => void
  'app.openSourceRepo': (a?: undefined) => void
  'app.openExternalUrl': (a: { url: string }) => void
}

export type IpcChannel = keyof IpcCommands
export type IpcArgs<C extends IpcChannel> = Parameters<IpcCommands[C]>[0]
export type IpcResult<C extends IpcChannel> = ReturnType<IpcCommands[C]>

/** Push events, main → renderer. */
export interface IpcEvents {
  'pty-data': { id: number; data: string }
  'pty-exit': { id: number }
  'fs-changed': { root: string }
  'app:set-language': 'zh' | 'en'
  'app:switch-workspace': void
  'app:open-recent-work': string
  'app:new-terminal': void
  'app:toggle-terminal': boolean | undefined
  'cloud-sync-progress': CloudSyncProgress
}

export type IpcEventName = keyof IpcEvents

export const IPC_INVOKE_CHANNEL = 'armory:invoke'

/** Shape exposed on window.armory by the preload script. */
export interface ArmoryBridge {
  invoke<C extends IpcChannel>(channel: C, args: IpcArgs<C>): Promise<IpcResult<C>>
  on<E extends IpcEventName>(event: E, cb: (payload: IpcEvents[E]) => void): () => void
  platform: NodeJS.Platform
  /** Absolute path for a File dropped from the OS (Electron webUtils). */
  getPathForFile(file: File): string
}
