import { ipcMain, shell } from 'electron'
import { IPC_INVOKE_CHANNEL, type IpcArgs, type IpcChannel, type IpcCommands } from '@shared/ipc'
import { WorkspaceService } from './services/workspace'
import { SkillsService } from './services/skills'
import { WorkFsService } from './services/workfs'
import { BaselineService } from './services/baseline'
import { PtyService } from './services/pty'
import { WatchService } from './services/watch'
import { MediaService } from './services/media'
import { LocalBridgeService } from './services/localBridge'
import { detectAgents } from './services/agents'
import { readNextAction } from './services/pipeline'
import { installDemo, listDemoDownloads, seedDemos } from './services/demos'
import * as canvas from './services/canvas'
import { readQualityInsights } from './services/quality'
import type { AppUiState } from './menu'

type HandlerMap = {
  [C in IpcChannel]: (args: IpcArgs<C>) => Promise<Awaited<ReturnType<IpcCommands[C]>>> | Awaited<ReturnType<IpcCommands[C]>>
}

export interface MainServices {
  workspace: WorkspaceService
  skills: SkillsService
  baseline: BaselineService
  workfs: WorkFsService
  pty: PtyService
  watch: WatchService
  media: MediaService
  bridge: LocalBridgeService
  ui: AppUiState
}

export function createServices(ui: AppUiState): MainServices {
  const baseline = new BaselineService()
  const workspace = new WorkspaceService()
  return {
    workspace,
    skills: new SkillsService(),
    baseline,
    workfs: new WorkFsService(baseline),
    pty: new PtyService(),
    watch: new WatchService(),
    media: new MediaService(),
    bridge: new LocalBridgeService(workspace),
    ui,
  }
}

export function registerIpc(s: MainServices) {
  const handlers: HandlerMap = {
    'workspace.scan': (a) => s.workspace.scan(a.repoRoot),
    'workspace.default': () => s.workspace.defaultWorkspace(),
    'workspace.resolveRepo': (a) => s.workspace.resolveRepo(a.devRepo),
    'workspace.createWork': (a) => s.workspace.createWork(a.dir, a.repoRoot, a.name),
    'workspace.deleteWork': (a) => s.workspace.deleteWork(a.workspaceRoot, a.repoRoot, a.path),
    'workspace.pickDirectory': (a) => s.workspace.pickDirectory(a.title),

    'demos.list': (a) => listDemoDownloads(a.workspaceRoot),
    'demos.install': (a) => installDemo(a.workspaceRoot, a.rel),
    'demos.seed': (a) => seedDemos(a.workspaceRoot),

    'skills.list': (a) => s.skills.list(a.repoRoot, a.line),
    'skills.tree': (a) => s.skills.tree(a.repoRoot, a.dir),
    'skills.readFile': (a) => s.skills.readFile(a.repoRoot, a.dir, a.rel),

    'work.tree': (a) => s.workfs.tree(a.root),
    'work.dir': (a) => s.workfs.dir(a.root, a.rel ?? '', a.offset ?? 0, a.limit ?? 500),
    'work.snapshot': (a) => s.workfs.snapshot(a.root),
    'work.isEmpty': (a) => s.workfs.isEmpty(a.root),
    'work.readFile': (a) => s.workfs.readFile(a.root, a.rel),
    'work.readDocx': (a) => s.workfs.readDocx(a.root, a.rel),
    'work.writeFile': (a) => s.workfs.writeFile(a.root, a.rel, a.text, a.expectedMtime),
    'work.saveCanvasCapture': (a) => s.workfs.saveCanvasCapture(a.root, a.imageData, a.label),
    'work.createEntry': (a) => s.workfs.createEntry(a.root, a.parentRel, a.name, a.kind),
    'work.renameEntry': (a) => s.workfs.renameEntry(a.root, a.rel, a.newName),
    'work.deleteEntry': (a) => s.workfs.deleteEntry(a.root, a.rel),
    'work.importSources': (a) => s.workfs.importSources(a.root, a.sources),
    'work.importN2dNovel': (a) => s.workfs.importN2dNovel(a.root, a.sources),
    'work.revealEntry': (a) => s.workfs.revealEntry(a.root, a.rel),
    'work.openEntry': (a) => s.workfs.openEntry(a.root, a.rel),
    'work.search': (a) => s.workfs.search(a.root, a.query, a.caseSensitive, a.wholeWord, a.useRegex),
    'work.pickImportFiles': (a) => s.workspace.pickImportFiles(a.extensions, a.title),

    'changes.summary': (a) => s.baseline.summary(a.root),
    'changes.list': (a) => s.baseline.changes(a.root),
    'changes.read': (a) => s.baseline.readChange(a.root, a.rel),
    'changes.archiveAll': (a) => s.baseline.archiveAll(a.root),
    'changes.archiveOne': (a) => s.baseline.archiveOne(a.root, a.rel),
    'changes.restoreAll': (a) => s.baseline.restoreAll(a.root),
    'changes.restoreOne': (a) => s.baseline.restoreOne(a.root, a.rel),
    'changes.deleted': (a) => s.baseline.deletedPaths(a.root),

    'canvas.read': (a) => canvas.readCanvas(a.root, a.ep, a.knownSig),
    'canvas.readLayout': (a) => canvas.readCanvasLayout(a.root, a.ep),
    'canvas.writeLayout': (a) => canvas.writeCanvasLayout(a.root, a.ep, a.nodes),
    'canvas.readClipEdit': (a) => canvas.readClipEdit(a.root, a.ep, a.clipId, a.number),
    'canvas.writeClipEdit': (a) => canvas.writeClipEdit(a.root, a.ep, a.clipId, a.number, a.patch),
    'canvas.readGenerationConfig': (a) => canvas.readCanvasGenerationConfig(a.root, a.ep, a.clipId, a.kind),
    'canvas.writeGenerationConfig': (a) => canvas.writeCanvasGenerationConfig(a.root, a.ep, a.clipId, a.config),
    'canvas.readEpisodeWorkspace': (a) => canvas.readEpisodeWorkspace(a.root, a.ep),
    'quality.read': (a) => readQualityInsights(a.root, a.line, a.ep),
    'pipeline.nextAction': (a) => readNextAction(a.repoRoot, a.root, a.ep),

    'agents.detect': (a) => detectAgents(Boolean(a?.force)),

    'pty.spawn': (a) => s.pty.spawn(a.cwd, a.rows, a.cols),
    'pty.write': (a) => s.pty.write(a.id, a.data),
    'pty.resize': (a) => s.pty.resize(a.id, a.rows, a.cols),
    'pty.kill': (a) => s.pty.kill(a.id),

    'watch.root': (a) => s.watch.watch(a.root),
    'watch.unroot': (a) => s.watch.unwatch(a.root),

    'media.start': () => s.media.start(),
    'media.allowRoot': (a) => s.media.allowRoot(a.root),

    'app.setLanguage': (a) => s.ui.setLanguage(a.language === 'en' ? 'en' : 'zh'),
    'app.setTerminalVisible': (a) => s.ui.setTerminalVisible(a.visible),
    'app.setRecentWorks': (a) => s.ui.setRecentWorks(a.works),
    'app.openSourceRepo': () => {
      shell.openExternal('https://github.com/anton6202527/anime-armory/releases')
    },
    'app.openExternalUrl': (a) => {
      const url = new URL(a.url)
      if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        throw new Error('仅允许打开 http/https 链接')
      }
      shell.openExternal(a.url)
    },
  }

  // These handlers expose file writes, shell opens, and pty spawns; only the
  // app's own top-level frame may call them (not iframes or stray webviews).
  const trustedSender = (frame: Electron.WebFrameMain | null): boolean => {
    if (!frame || frame.parent !== null) return false
    const url = frame.url
    return url.startsWith('file:') || url.startsWith('http://localhost:') || url.startsWith('http://127.0.0.1:')
  }

  const trace = Boolean(process.env.SMOKE_SHOT)
  ipcMain.handle(IPC_INVOKE_CHANNEL, async (event, channel: string, args: unknown) => {
    if (!trustedSender(event.senderFrame)) throw new Error('拒绝来自不可信来源的 IPC 调用')
    const handler = handlers[channel as IpcChannel]
    if (!handler) throw new Error(`未知命令: ${channel}`)
    if (!trace) return (handler as (x: unknown) => unknown)(args)
    const t0 = Date.now()
    console.log(`[ipc] -> ${channel}`)
    try {
      return await (handler as (x: unknown) => Promise<unknown>)(args)
    } finally {
      console.log(`[ipc] <- ${channel} ${Date.now() - t0}ms`)
    }
  })
}
