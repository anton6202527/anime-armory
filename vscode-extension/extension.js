// anime-armory — VS Code factory browser.
// SELF-CONTAINED: public usage docs and optional skills are BUNDLED inside the
// extension (./assets, synced from the repo by sync-assets.js). 作品区 defaults to
// the extension's own bundled work root, independent from the parent repo.
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

function isDir(p) { try { return fs.statSync(p).isDirectory(); } catch { return false; } }
function exists(p) { try { fs.accessSync(p); return true; } catch { return false; } }
function listDirs(p) {
  try {
    return fs.readdirSync(p, { withFileTypes: true })
      .filter((d) => d.isDirectory() && !d.name.startsWith('.') && d.name !== '__pycache__')
      .map((d) => d.name)
      .sort((a, b) => a.localeCompare(b, 'zh'));
  } catch { return []; }
}

// generic directory listing → tree nodes (folders first, then files).
// `writable` marks live-project nodes (CRUD allowed); bundled/read-only nodes get
// a different contextValue so the New/Rename/Delete menu items don't show on them.
function fsChildren(dir, writable) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return []; }
  entries = entries.filter((e) =>
    !e.name.startsWith('.') && e.name !== '__pycache__' && e.name !== 'node_modules');
  const cmp = (a, b) => a.localeCompare(b, 'zh');
  const dirs = entries.filter((e) => e.isDirectory()).map((e) => e.name).sort(cmp);
  const files = entries.filter((e) => !e.isDirectory()).map((e) => e.name).sort(cmp);
  const rw = writable ? '-rw' : '-ro';
  const nodes = [];
  for (const name of dirs) {
    const p = path.join(dir, name);
    const t = new vscode.TreeItem(vscode.Uri.file(p), vscode.TreeItemCollapsibleState.Collapsed);
    t.kind = 'fsdir'; t.dirPath = p; t.writable = !!writable; t.contextValue = 'fsdir' + rw;
    nodes.push(t);
  }
  for (const name of files) {
    const p = path.join(dir, name);
    const t = new vscode.TreeItem(vscode.Uri.file(p), vscode.TreeItemCollapsibleState.None);
    t.kind = 'fsfile'; t.fsPath = p; t.writable = !!writable; t.contextValue = 'fsfile' + rw;
    t.command = { command: 'vscode.open', title: 'Open', arguments: [vscode.Uri.file(p)] };
    nodes.push(t);
  }
  return nodes;
}

// ── SKILL.md frontmatter parse ─────────────────────────────────────────────
function parseFrontmatter(mdPath) {
  try {
    const txt = fs.readFileSync(mdPath, 'utf8');
    const m = txt.match(/^---\s*\r?\n([\s\S]*?)\r?\n---/);
    if (!m) return {};
    const grab = (key) => {
      const mm = m[1].match(new RegExp('^' + key + ':[ \\t]*(.*)$', 'm'));
      return mm ? mm[1].trim().replace(/^["']|["']$/g, '') : '';
    };
    return { name: grab('name'), description: grab('description') };
  } catch { return {}; }
}
function shortDesc(d) {
  if (!d) return '';
  d = d.replace(/\s+/g, ' ').trim();
  let cut = d.length;
  const cjk = d.indexOf('。'); if (cjk > 0) cut = Math.min(cut, cjk);
  const en = d.search(/\.\s/); if (en > 0) cut = Math.min(cut, en);
  const dash = d.search(/——| — /); if (dash > 0) cut = Math.min(cut, dash);
  const s = d.slice(0, cut).trim();
  return s.length > 64 ? s.slice(0, 64) + '…' : s;
}

const FAMILIES = [
  { id: 'novel', label: '✍️ 写小说 novel-*', test: (n) => n.startsWith('novel-') },
  { id: 'n2d', label: '🎬 制漫剧 n2d-*', test: (n) => n.startsWith('n2d-') || n === 'novel2drama' },
  { id: 'shared', label: '🔧 共享能力', test: () => true },
];
function scanSkills(skillsDir) {
  const out = {}; FAMILIES.forEach((f) => (out[f.id] = []));
  for (const name of listDirs(skillsDir)) {
    const dir = path.join(skillsDir, name);
    const skillMd = path.join(dir, 'SKILL.md');
    if (!exists(skillMd)) continue;
    const fm = parseFrontmatter(skillMd);
    out[FAMILIES.find((f) => f.test(name)).id].push({ name, dir, description: fm.description || '' });
  }
  return out;
}

const WORK_LINES = [
  { label: '✍️ 写小说', dir: '写小说' },
  { label: '🎬 制漫剧', dir: '制漫剧' },
];
const DOCS = [
  { rel: 'README.md', desc: '使用说明 · 工作流与批量生产' },
];
const FIRST_OPEN_TERMINAL_MESSAGE = '进入ai，输入‘/制漫剧/本宫才是这皇宫最大的妖/小说/本宫才是这皇宫最大的妖.txt 拆脚本’，开始你的漫剧制作吧！';

// 作品区 source: prefer the extension's own bundled work root, then an explicitly
// configured external root, then the open workspace.
function hasProjectMarkers(root) {
  return root && (exists(path.join(root, 'skills', 'README.md')) ||
    WORK_LINES.some((l) => isDir(path.join(root, l.dir))));
}

function findProjectRoot(start) {
  if (!start) return null;
  let cur = path.resolve(start);
  if (!isDir(cur)) cur = path.dirname(cur);
  while (cur && cur !== path.dirname(cur)) {
    if (hasProjectMarkers(cur)) return cur;
    cur = path.dirname(cur);
  }
  return hasProjectMarkers(cur) ? cur : null;
}

function resolveWorkRoot(defaultRoot) {
  const cfg = vscode.workspace.getConfiguration('animeArsenal');
  const useExternalWorks = cfg.get('useExternalWorks', false);
  const configuredRoot = cfg.get('repoRoot');
  const resolvedConfiguredRoot = findProjectRoot(configuredRoot);
  if (useExternalWorks && resolvedConfiguredRoot) return resolvedConfiguredRoot;

  const bundledRoot = findProjectRoot(defaultRoot);
  if (bundledRoot) return bundledRoot;

  if (resolvedConfiguredRoot) return resolvedConfiguredRoot;

  for (const f of (vscode.workspace.workspaceFolders || [])) {
    const root = findProjectRoot(f.uri.fsPath);
    if (root) {
      return root;
    }
  }
  const ws = vscode.workspace.workspaceFolders;
  if (ws && ws[0]) return ws[0].uri.fsPath;
  return configuredRoot && isDir(configuredRoot) ? configuredRoot : null;
}

// ── tree provider ──────────────────────────────────────────────────────────
class FactoryProvider {
  constructor(extensionRoot, assetsRoot) {
    this._onDidChange = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChange.event;
    this.extensionRoot = extensionRoot;    // bundled sample works live here
    this.assetsRoot = assetsRoot;          // bundled skills + docs (always present)
    this.skillsDir = path.join(assetsRoot, 'skills');
  }
  refresh() { this._onDidChange.fire(); }
  getTreeItem(el) { return el; }

  getChildren(el) {
    if (!el) return this._roots();
    switch (el.kind) {
      case 'group-docs': return this._docs();
      case 'group-skills': return this._families();
      case 'family': return this._skills(el.familyId);
      case 'skill': return fsChildren(el.dirPath, false);          // bundled = read-only
      case 'fsdir': return fsChildren(el.dirPath, el.writable);    // inherit writability
      default: return [];
    }
  }

  _roots() {
    const mk = (label, kind, icon, desc, state = vscode.TreeItemCollapsibleState.Collapsed) => {
      const t = new vscode.TreeItem(label, state);
      t.kind = kind; t.iconPath = new vscode.ThemeIcon(icon); t.contextValue = kind;
      if (desc) t.description = desc;
      return t;
    };
    const roots = [
      ...this._lines(),
      ...this._docs(),
    ];
    if (vscode.workspace.getConfiguration('animeArsenal').get('showSkills', false)) {
      roots.push(mk('🧩 Skills', 'group-skills', 'extensions', '高级'));
    }
    return roots;
  }

  _docs() {
    const out = [];
    for (const d of DOCS) {
      const p = path.join(this.assetsRoot, d.rel);
      if (!exists(p)) continue;
      const t = new vscode.TreeItem(path.basename(d.rel), vscode.TreeItemCollapsibleState.None);
      t.kind = 'doc'; t.description = d.desc; t.tooltip = d.desc;
      t.iconPath = new vscode.ThemeIcon('markdown');
      t.command = { command: 'vscode.open', title: 'Open', arguments: [vscode.Uri.file(p)] };
      out.push(t);
    }
    return out;
  }

  _families() {
    this._cache = scanSkills(this.skillsDir);
    return FAMILIES.filter((f) => (this._cache[f.id] || []).length).map((f) => {
      const t = new vscode.TreeItem(f.label, vscode.TreeItemCollapsibleState.Collapsed);
      t.kind = 'family'; t.familyId = f.id; t.description = String(this._cache[f.id].length);
      return t;
    });
  }

  _skills(familyId) {
    const skills = (this._cache && this._cache[familyId]) || scanSkills(this.skillsDir)[familyId] || [];
    return skills.map((s) => {
      const t = new vscode.TreeItem(s.name, vscode.TreeItemCollapsibleState.Collapsed);
      t.kind = 'skill'; t.dirPath = s.dir; t.contextValue = 'skill';
      t.description = shortDesc(s.description);
      t.resourceUri = vscode.Uri.file(s.dir);
      const md = new vscode.MarkdownString();
      md.appendMarkdown(`**${s.name}**\n\n${s.description || '_无 description_'}`);
      t.tooltip = md;
      // no `command` → clicking expands into SKILL.md / references/ / scripts/
      return t;
    });
  }

  _lines() {
    // 作品区 = bundled work root by default, or the selected external root. WRITABLE: 新建/重命名/删除可用。
    const root = resolveWorkRoot(this.extensionRoot);
    if (!root) {
      const t = new vscode.TreeItem('打开一个工作区后在这里创作自己的作品', vscode.TreeItemCollapsibleState.None);
      t.kind = 'hint'; t.contextValue = 'hint';
      t.iconPath = new vscode.ThemeIcon('info');
      return [t];
    }
    return WORK_LINES.map((line) => {
      const dir = path.join(root, line.dir);
      const t = new vscode.TreeItem(line.label, vscode.TreeItemCollapsibleState.Collapsed);
      t.kind = 'fsdir'; t.dirPath = dir; t.writable = true; t.contextValue = 'workline-rw';
      t.description = isDir(dir) ? String(listDirs(dir).length) : '新建';
      t.resourceUri = vscode.Uri.file(dir);
      return t;
    });
  }
}

// Create a file/folder under a writable node (or its parent if invoked on a file).
async function createEntry(node, isFolder, provider) {
  if (!node) return;
  const base = node.dirPath || (node.fsPath && path.dirname(node.fsPath));
  if (!base) return;
  const name = await vscode.window.showInputBox({
    prompt: isFolder ? '新建文件夹名称' : '新建文件名称（可含子路径，如 设定/角色卡.md）',
    placeHolder: isFolder ? '新文件夹' : '新文件.md',
  });
  if (!name) return;
  const target = path.join(base, name);
  try {
    await vscode.workspace.fs.createDirectory(vscode.Uri.file(base));
    if (isFolder) {
      await vscode.workspace.fs.createDirectory(vscode.Uri.file(target));
    } else {
      await vscode.workspace.fs.createDirectory(vscode.Uri.file(path.dirname(target)));
      try { await vscode.workspace.fs.stat(vscode.Uri.file(target)); /* exists */ }
      catch { await vscode.workspace.fs.writeFile(vscode.Uri.file(target), new Uint8Array()); }
      await vscode.window.showTextDocument(vscode.Uri.file(target));
    }
  } catch (e) { vscode.window.showErrorMessage('创建失败：' + e.message); return; }
  provider.refresh();
}

// Uri for any node (file / dir / skill dir).
function nodeUri(node) {
  if (!node) return undefined;
  if (node.resourceUri) return node.resourceUri;
  const p = node.dirPath || node.fsPath;
  return p ? vscode.Uri.file(p) : undefined;
}

// Where a freshly-opened terminal should cd to: the project root, else extension folder.
function terminalCwd(extensionRoot) {
  return resolveWorkRoot(extensionRoot) || extensionRoot || undefined;
}
function openArsenalTerminal(extensionRoot, initialMessage = '', reuseExisting = false) {
  const sendInitialMessage = (term) => {
    if (initialMessage) term.sendText(`# ${initialMessage}`, true);
  };
  if (reuseExisting) {
    const existing = vscode.window.terminals.find((t) => t.name === 'anime-armory');
    if (existing) {
      existing.show();
      sendInitialMessage(existing);
      return existing;
    }
  }
  const term = vscode.window.createTerminal({ name: 'anime-armory', cwd: terminalCwd(extensionRoot) });
  term.show();
  // Show the onboarding line once without executing anything; using a shell
  // comment avoids the command-echo + printed-output double line from echo/printf.
  sendInitialMessage(term);
  return term;
}

function activate(context) {
  const assetsRoot = path.join(context.extensionPath, 'assets');
  const provider = new FactoryProvider(context.extensionPath, assetsRoot);

  // Create the view (not just register the provider) so we get visibility events.
  const treeView = vscode.window.createTreeView('animeArsenalView', { treeDataProvider: provider });
  let termOpened = false;
  const maybeOpenTerminal = () => {
    if (termOpened || !treeView.visible) return;
    termOpened = true; // once per window session
    if (!vscode.workspace.getConfiguration('animeArsenal').get('openTerminalOnReveal', true)) return;
    openArsenalTerminal(context.extensionPath, FIRST_OPEN_TERMINAL_MESSAGE, true);
  };
  treeView.onDidChangeVisibility(() => maybeOpenTerminal());
  maybeOpenTerminal(); // in case the view is already visible at activation

  context.subscriptions.push(
    treeView,
    vscode.commands.registerCommand('animeArsenal.openTerminal', () => openArsenalTerminal(context.extensionPath)),
    vscode.commands.registerCommand('animeArsenal.refresh', () => provider.refresh()),
    vscode.commands.registerCommand('animeArsenal.selectRepo', async () => {
      const pick = await vscode.window.showOpenDialog({
        canSelectFolders: true, canSelectFiles: false, canSelectMany: false,
        openLabel: '选含 写小说/制漫剧 的项目根（用于作品区）',
      });
      if (!pick || !pick[0]) return;
      const dir = findProjectRoot(pick[0].fsPath) || pick[0].fsPath;
      await vscode.workspace.getConfiguration('animeArsenal')
        .update('repoRoot', dir, vscode.ConfigurationTarget.Global);
      await vscode.workspace.getConfiguration('animeArsenal')
        .update('useExternalWorks', true, vscode.ConfigurationTarget.Global);
      provider.refresh();
      vscode.window.showInformationMessage('作品区目录已设为：' + dir);
    }),
    // ── native-style passthroughs (extract Uri from node → built-in command) ──
    vscode.commands.registerCommand('animeArsenal.revealInExplorer', (node) => {
      const uri = nodeUri(node);
      if (uri) vscode.commands.executeCommand('revealInExplorer', uri);
    }),
    vscode.commands.registerCommand('animeArsenal.revealInOS', (node) => {
      const uri = nodeUri(node);
      if (uri) vscode.commands.executeCommand('revealFileInOS', uri);
    }),
    vscode.commands.registerCommand('animeArsenal.openToSide', (node) => {
      const uri = nodeUri(node);
      if (uri) vscode.commands.executeCommand('vscode.open', uri, { viewColumn: vscode.ViewColumn.Beside });
    }),
    vscode.commands.registerCommand('animeArsenal.openInTerminal', (node) => {
      const uri = nodeUri(node);
      if (!uri) return;
      // open at the folder (for a file, use its parent)
      const p = node.dirPath || (node.fsPath && path.dirname(node.fsPath)) || uri.fsPath;
      vscode.window.createTerminal({ name: 'anime-armory', cwd: p }).show();
    }),
    vscode.commands.registerCommand('animeArsenal.copyPath', (node) => {
      const uri = nodeUri(node);
      if (uri) vscode.env.clipboard.writeText(uri.fsPath);
    }),
    vscode.commands.registerCommand('animeArsenal.copyRelativePath', (node) => {
      const uri = nodeUri(node);
      if (!uri) return;
      const rel = vscode.workspace.asRelativePath(uri, false);
      vscode.env.clipboard.writeText(rel);
    }),
    // ── file management on writable (live-project) nodes ──────────────────────
    vscode.commands.registerCommand('animeArsenal.newFile', (node) => createEntry(node, false, provider)),
    vscode.commands.registerCommand('animeArsenal.newFolder', (node) => createEntry(node, true, provider)),
    vscode.commands.registerCommand('animeArsenal.rename', async (node) => {
      const p = node && (node.dirPath || node.fsPath);
      if (!p) return;
      const cur = path.basename(p);
      const name = await vscode.window.showInputBox({ prompt: '重命名为', value: cur });
      if (!name || name === cur) return;
      const dest = path.join(path.dirname(p), name);
      try { await vscode.workspace.fs.rename(vscode.Uri.file(p), vscode.Uri.file(dest), { overwrite: false }); }
      catch (e) { vscode.window.showErrorMessage('重命名失败：' + e.message); return; }
      provider.refresh();
    }),
    vscode.commands.registerCommand('animeArsenal.delete', async (node) => {
      const p = node && (node.dirPath || node.fsPath);
      if (!p) return;
      const ok = await vscode.window.showWarningMessage(
        `删除 “${path.basename(p)}”？此操作移到回收站。`, { modal: true }, '删除');
      if (ok !== '删除') return;
      try { await vscode.workspace.fs.delete(vscode.Uri.file(p), { recursive: true, useTrash: true }); }
      catch (e) { vscode.window.showErrorMessage('删除失败：' + e.message); return; }
      provider.refresh();
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(() => provider.refresh()),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('animeArsenal.repoRoot') ||
          e.affectsConfiguration('animeArsenal.useExternalWorks') ||
          e.affectsConfiguration('animeArsenal.showSkills')) {
        provider.refresh();
      }
    })
  );

  // Auto-refresh the tree when files appear/disappear/change on disk. Scripts,
  // AI agents, and terminal commands write output OUTSIDE the extension's own
  // CRUD path, so without this the generated files never show up until a manual
  // refresh.
  let refreshTimer;
  const debouncedRefresh = () => {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => provider.refresh(), 300);
  };

  // (1) Watch the open workspace — covers a work root that IS the opened folder.
  // The window-focus refresh is a cheap fallback for everything else.
  const wsWatcher = vscode.workspace.createFileSystemWatcher('**/*');
  context.subscriptions.push(
    wsWatcher,
    wsWatcher.onDidCreate(debouncedRefresh),
    wsWatcher.onDidDelete(debouncedRefresh),
    wsWatcher.onDidChange(debouncedRefresh),
    vscode.window.onDidChangeWindowState((s) => { if (s.focused) debouncedRefresh(); })
  );

  // (2) Also watch the RESOLVED work root directly. The default bundled root and
  // any external 作品区 chosen via 选择仓库目录 live OUTSIDE the workspace, so the
  // workspace watcher above never sees scripts/agents writing there — produced
  // files would only surface on manual refresh / window re-focus. A RelativePattern
  // watcher recursively covers any folder, in- or out-of-workspace. Recreated
  // whenever the resolved root changes (config / workspace folders).
  let rootWatcher, watchedRoot;
  const syncRootWatcher = () => {
    const root = resolveWorkRoot(context.extensionPath);
    if (root === watchedRoot) return;          // unchanged → keep existing watcher
    watchedRoot = root;
    if (rootWatcher) { rootWatcher.dispose(); rootWatcher = undefined; }
    if (!root) return;
    rootWatcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(vscode.Uri.file(root), '**/*'));
    rootWatcher.onDidCreate(debouncedRefresh);
    rootWatcher.onDidDelete(debouncedRefresh);
    rootWatcher.onDidChange(debouncedRefresh);
    context.subscriptions.push(rootWatcher);
  };
  syncRootWatcher();
  context.subscriptions.push(
    vscode.workspace.onDidChangeWorkspaceFolders(() => syncRootWatcher()),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('animeArsenal.repoRoot') ||
          e.affectsConfiguration('animeArsenal.useExternalWorks')) {
        syncRootWatcher();
      }
    })
  );
}
function deactivate() {}
module.exports = { activate, deactivate };
