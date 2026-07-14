// anime-armory — VS Code factory browser.
// SELF-CONTAINED: public usage docs and optional skills are BUNDLED inside the
// extension (./assets, synced from the repo by sync-assets.js). 作品区 defaults to
// the extension's own bundled work root, independent from the parent repo.
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const fsp = fs.promises;

function isDir(p) { try { return fs.statSync(p).isDirectory(); } catch { return false; } }
function exists(p) { try { fs.accessSync(p); return true; } catch { return false; } }
function normPath(p) { return path.resolve(p); }
function listDirs(p) {
  try {
    return fs.readdirSync(p, { withFileTypes: true })
      .filter((d) => d.isDirectory() && isVisibleName(d.name))
      .map((d) => d.name)
      .sort(nameCmp);
  } catch { return []; }
}

const COLLATOR = new Intl.Collator('zh');
const DEFAULT_MAX_ITEMS_PER_DIRECTORY = 500;
const DEFAULT_MAX_WATCHED_DIRECTORIES = 96;
const IGNORED_NAMES = new Set(['__pycache__', 'node_modules']);
function nameCmp(a, b) { return COLLATOR.compare(a, b); }
function isVisibleName(name) { return !!name && !name.startsWith('.') && !IGNORED_NAMES.has(name); }
function configNumber(key, fallback, min, max) {
  const raw = vscode.workspace.getConfiguration('animeArmory').get(key, fallback);
  const n = Number(raw);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, Math.floor(n)));
}
function maxItemsPerDirectory() {
  return configNumber('maxItemsPerDirectory', DEFAULT_MAX_ITEMS_PER_DIRECTORY, 50, 10000);
}
function maxWatchedDirectories() {
  return configNumber('maxWatchedDirectories', DEFAULT_MAX_WATCHED_DIRECTORIES, 8, 512);
}
async function readDirents(dir) {
  try { return await fsp.readdir(dir, { withFileTypes: true }); } catch { return []; }
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
  { id: 'novel', label: '✍️ 写小说 novel-*', test: (n) => n.startsWith('novel-') || n === 'novel' },
  { id: 'n2d', label: '🎬 制漫剧 n2d-*', test: (n) => n.startsWith('n2d-') || n === 'n2d' },
  { id: 'comic', label: '🖼️ 画漫画 comic-*', test: (n) => n.startsWith('comic-') || n === 'comic' },
];
function scanSkills(skillsDir) {
  const out = {}; FAMILIES.forEach((f) => (out[f.id] = []));
  for (const name of listDirs(skillsDir)) {
    const dir = path.join(skillsDir, name);
    const skillMd = path.join(dir, 'SKILL.md');
    if (!exists(skillMd)) continue;
    const fm = parseFrontmatter(skillMd);
    const family = FAMILIES.find((f) => f.test(name));
    if (!family) continue;
    out[family.id].push({ name, dir, description: fm.description || '' });
  }
  return out;
}

const WORK_LINES = [
  { label: '✍️ 写小说', dir: path.join('创作区', '写小说') },
  { label: '🎬 制漫剧', dir: path.join('创作区', '制漫剧') },
  { label: '🖼️ 画漫画', dir: path.join('创作区', '画漫画') },
];
const DOCS = [
  { rel: 'README.md', label: 'README.md', desc: '使用说明 · 工作流与批量生产' },
  { rel: '创作区/使用手册.md', label: '创作区使用手册', desc: '三条创作线总览与小说 demo' },
  { rel: '创作区/写小说/使用手册.md', label: '写小说使用手册', desc: 'novel 项目开局、续写、审稿' },
  { rel: '创作区/制漫剧/使用手册.md', label: '制漫剧使用手册', desc: 'n2d 从小说到短剧成片' },
  { rel: '创作区/画漫画/使用手册.md', label: '画漫画使用手册', desc: 'comic 分格、排版、嵌字' },
];
const FIRST_OPEN_TERMINAL_MESSAGE = '在此进入ai agent，粘贴“写小说/那妖魔是姜大人 开始制作漫剧吧“';

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
  const cfg = vscode.workspace.getConfiguration('animeArmory');
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

function resolveAssetRoots(extensionRoot) {
  const bundled = path.join(extensionRoot, 'assets');
  if (exists(path.join(bundled, 'skills', 'README.md'))) {
    return { docsRoot: bundled, skillsDir: path.join(bundled, 'skills') };
  }

  // Local extension debugging may run before sync-assets.js has generated
  // assets/. Keep extension-specific docs, but read the three allowed skill
  // families from the adjacent repo checkout.
  const repoRoot = findProjectRoot(path.dirname(extensionRoot));
  if (repoRoot && exists(path.join(repoRoot, 'skills', 'README.md'))) {
    return { docsRoot: extensionRoot, skillsDir: path.join(repoRoot, 'skills') };
  }

  return { docsRoot: extensionRoot, skillsDir: path.join(bundled, 'skills') };
}

// ── tree provider ──────────────────────────────────────────────────────────
class FactoryProvider {
  constructor(extensionRoot, docsRoot, skillsDir) {
    this._onDidChange = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChange.event;
    this.extensionRoot = extensionRoot;    // bundled sample works live here
    this.assetsRoot = docsRoot;            // extension-specific docs, bundled or from source
    this.skillsDir = skillsDir;            // bundled subset, or filtered live repo skills in dev
    this.dirCache = new Map();             // dir -> { limit, writable, items }
    this.dirLimits = new Map();            // dir -> visible item budget
    this.nodeByDir = new Map();            // dir -> latest TreeItem for targeted refresh
  }
  refresh(el) {
    if (!el) this.clearCaches();
    this._onDidChange.fire(el);
  }
  clearCaches() {
    this.dirCache.clear();
    this.nodeByDir.clear();
  }
  invalidateDirectory(dir) {
    this.dirCache.delete(normPath(dir));
  }
  invalidatePath(p) {
    if (!p) return;
    this.invalidateDirectory(p);
    this.invalidateDirectory(path.dirname(p));
  }
  refreshPath(p) {
    if (!p) return this.refresh();
    const start = isDir(p) ? p : path.dirname(p);
    let cur = normPath(start);
    while (cur && cur !== path.dirname(cur)) {
      const node = this.nodeByDir.get(cur);
      if (node) {
        this.invalidateDirectory(cur);
        this._onDidChange.fire(node);
        return;
      }
      cur = path.dirname(cur);
    }
    this.refresh();
  }
  showMore(node) {
    const dir = node && node.dirPath;
    if (!dir) return;
    const key = normPath(dir);
    const base = maxItemsPerDirectory();
    const current = this.dirLimits.get(key) || base;
    this.dirLimits.set(key, Math.min(10000, current + base));
    this.invalidateDirectory(key);
    this._onDidChange.fire(this.nodeByDir.get(key));
  }
  registerDirNode(node) {
    if (node && node.dirPath) this.nodeByDir.set(normPath(node.dirPath), node);
  }
  getTreeItem(el) { return el; }

  async getChildren(el) {
    if (!el) return this._roots();
    switch (el.kind) {
      case 'group-docs': return this._docs();
      case 'group-skills': return this._families();
      case 'family': return this._skills(el.familyId);
      case 'skill': return this._directoryChildren(el.dirPath, false);          // bundled = read-only
      case 'fsdir': return this._directoryChildren(el.dirPath, el.writable);    // inherit writability
      default: return [];
    }
  }

  async _directoryChildren(dir, writable) {
    const key = normPath(dir);
    const limit = this.dirLimits.get(key) || maxItemsPerDirectory();
    const cached = this.dirCache.get(key);
    if (cached && cached.limit === limit && cached.writable === !!writable) return cached.items;

    const entries = (await readDirents(dir)).filter((e) => isVisibleName(e.name));
    const dirs = entries.filter((e) => e.isDirectory()).map((e) => e.name).sort(nameCmp);
    const files = entries.filter((e) => !e.isDirectory()).map((e) => e.name).sort(nameCmp);
    const names = [...dirs.map((name) => ({ name, isDir: true })), ...files.map((name) => ({ name, isDir: false }))];
    const visible = names.slice(0, limit);
    const rw = writable ? '-rw' : '-ro';
    const nodes = visible.map((entry) => {
      const p = path.join(dir, entry.name);
      if (entry.isDir) {
        const t = new vscode.TreeItem(vscode.Uri.file(p), vscode.TreeItemCollapsibleState.Collapsed);
        t.kind = 'fsdir'; t.dirPath = p; t.writable = !!writable; t.contextValue = 'fsdir' + rw;
        this.registerDirNode(t);
        return t;
      }
      const t = new vscode.TreeItem(vscode.Uri.file(p), vscode.TreeItemCollapsibleState.None);
      t.kind = 'fsfile'; t.fsPath = p; t.writable = !!writable; t.contextValue = 'fsfile' + rw;
      t.command = { command: 'vscode.open', title: 'Open', arguments: [vscode.Uri.file(p)] };
      return t;
    });
    if (names.length > visible.length) nodes.push(this._loadMoreNode(dir, writable, visible.length, names.length));
    this.dirCache.set(key, { limit, writable: !!writable, items: nodes });
    return nodes;
  }

  _loadMoreNode(dir, writable, shown, total) {
    const t = new vscode.TreeItem(`加载更多... ${shown}/${total}`, vscode.TreeItemCollapsibleState.None);
    t.kind = 'load-more';
    t.dirPath = dir;
    t.writable = !!writable;
    t.contextValue = 'load-more';
    t.iconPath = new vscode.ThemeIcon('ellipsis');
    t.command = { command: 'animeArmory.showMore', title: '加载更多', arguments: [t] };
    return t;
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
      ...this._docs((d) => d.rel === 'README.md'), // 只保留总 README，隐藏 4 个使用手册
    ];
    if (vscode.workspace.getConfiguration('animeArmory').get('showSkills', false)) {
      roots.push(mk('🧩 Skills', 'group-skills', 'extensions', '高级'));
    }
    return roots;
  }

  _docs(filter) {
    const out = [];
    for (const d of DOCS) {
      if (filter && !filter(d)) continue;
      const p = path.join(this.assetsRoot, d.rel);
      if (!exists(p)) continue;
      const t = new vscode.TreeItem(d.label || path.basename(d.rel), vscode.TreeItemCollapsibleState.None);
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
      this.registerDirNode(t);
      return t;
    });
  }
}

class VisibleDirectoryWatcher {
  constructor(context, provider, extensionRoot) {
    this.context = context;
    this.provider = provider;
    this.extensionRoot = extensionRoot;
    this.watchers = new Map();
    this.root = null;
    this.refreshTimer = undefined;
    this.eventTimer = undefined;
    this.pendingPaths = new Set();
  }

  dispose() {
    clearTimeout(this.refreshTimer);
    clearTimeout(this.eventTimer);
    for (const entry of this.watchers.values()) this._disposeEntry(entry);
    this.watchers.clear();
  }

  bind(treeView) {
    this.context.subscriptions.push(
      treeView.onDidExpandElement((e) => this.watchElement(e.element)),
      treeView.onDidCollapseElement((e) => this.unwatchElement(e.element)),
      vscode.window.onDidChangeWindowState((s) => { if (s.focused) this.refreshAllSoon(600); })
    );
    this.syncRoot();
  }

  syncRoot() {
    const root = resolveWorkRoot(this.extensionRoot);
    if (root === this.root) return;
    this.root = root;
    for (const entry of this.watchers.values()) this._disposeEntry(entry);
    this.watchers.clear();
    if (!root) return;
    for (const line of WORK_LINES) this.watchDir(path.join(root, line.dir), true);
  }

  refreshAllSoon(delay = 300) {
    clearTimeout(this.refreshTimer);
    this.refreshTimer = setTimeout(() => this.provider.refresh(), delay);
  }

  watchElement(el) {
    if (!el || el.kind !== 'fsdir') return;
    this.watchDir(el.dirPath, false);
  }

  unwatchElement(el) {
    if (!el || el.kind !== 'fsdir') return;
    const key = normPath(el.dirPath);
    const entry = this.watchers.get(key);
    if (!entry || entry.pinned) return;
    this._disposeEntry(entry);
    this.watchers.delete(key);
  }

  watchDir(dir, pinned) {
    if (!dir || !isDir(dir)) return;
    const key = normPath(dir);
    const existing = this.watchers.get(key);
    if (existing) {
      existing.pinned = existing.pinned || !!pinned;
      return;
    }
    const nonPinnedCount = [...this.watchers.values()].filter((entry) => !entry.pinned).length;
    if (!pinned && nonPinnedCount >= maxWatchedDirectories()) return;

    const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(dir), '*'));
    const onEvent = (uri) => {
      this.provider.invalidatePath(uri.fsPath);
      this.queuePath(uri.fsPath);
    };
    const disposables = [
      watcher,
      watcher.onDidCreate(onEvent),
      watcher.onDidDelete(onEvent),
      watcher.onDidChange(onEvent),
    ];
    this.watchers.set(key, { dir, pinned: !!pinned, disposables });
  }

  queuePath(p) {
    if (!p) return;
    this.pendingPaths.add(p);
    clearTimeout(this.eventTimer);
    this.eventTimer = setTimeout(() => this.flushPaths(), 250);
  }

  flushPaths() {
    const paths = [...this.pendingPaths];
    this.pendingPaths.clear();
    const refreshed = new Set();
    for (const p of paths) {
      const dir = normPath(isDir(p) ? p : path.dirname(p));
      if (refreshed.has(dir)) continue;
      refreshed.add(dir);
      this.provider.refreshPath(dir);
    }
  }

  _disposeEntry(entry) {
    for (const d of entry.disposables) d.dispose();
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
  provider.invalidatePath(target);
  provider.refreshPath(target);
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
function openArmoryTerminal(extensionRoot, initialMessage = '', reuseExisting = false) {
  const sendInitialMessage = (term) => {
    // Type the onboarding line at the prompt WITHOUT executing (second arg
    // false = no trailing newline). Running it — even as a `#` comment — makes
    // zsh's prompt redraw the line, so it appeared twice.
    if (initialMessage) term.sendText(`# ${initialMessage}`, false);
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

function shellQuote(value) {
  return "'" + String(value).replace(/'/g, "'\\''") + "'";
}

function n2dLineDir(extensionRoot) {
  const root = resolveWorkRoot(extensionRoot);
  return root ? path.join(root, '创作区', '制漫剧') : null;
}

function isN2DWorkRoot(dir) {
  return dir && exists(path.join(dir, '_进度.md')) &&
    path.normalize(dir).includes(path.normalize(path.join('创作区', '制漫剧')));
}

function findN2DWorkRootFromPath(start) {
  if (!start) return null;
  let cur = isDir(start) ? start : path.dirname(start);
  while (cur && cur !== path.dirname(cur)) {
    if (isN2DWorkRoot(cur)) return cur;
    cur = path.dirname(cur);
  }
  return isN2DWorkRoot(cur) ? cur : null;
}

function listN2DWorks(extensionRoot) {
  const lineDir = n2dLineDir(extensionRoot);
  if (!lineDir || !isDir(lineDir)) return [];
  return listDirs(lineDir)
    .map((name) => path.join(lineDir, name))
    .filter((dir) => exists(path.join(dir, '_进度.md')));
}

async function pickN2DWorkRoot(node, extensionRoot) {
  const uri = nodeUri(node);
  const direct = uri && findN2DWorkRootFromPath(uri.fsPath);
  if (direct) return direct;
  const works = listN2DWorks(extensionRoot);
  if (!works.length) {
    vscode.window.showInformationMessage('没有找到含 _进度.md 的制漫剧作品。');
    return null;
  }
  const picked = await vscode.window.showQuickPick(
    works.map((dir) => ({ label: path.basename(dir), description: dir, dir })),
    { placeHolder: '选择制漫剧作品' },
  );
  return picked && picked.dir;
}

function progressEpisodes(root) {
  try {
    const text = fs.readFileSync(path.join(root, '_进度.md'), 'utf8');
    const out = [];
    for (const line of text.split(/\r?\n/)) {
      const m = line.match(/^\|\s*(第\d+集)\s*\|/);
      if (m) out.push(m[1]);
    }
    return out;
  } catch { return []; }
}

function indexedEpisodes(root) {
  const indexPath = path.join(root, '生产数据', 'episode_index.json');
  try {
    const data = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
    return (data.episodes || []).map((ep) => ep.episode).filter(Boolean);
  } catch { return []; }
}

async function pickEpisode(root) {
  const episodes = indexedEpisodes(root);
  const fallback = progressEpisodes(root).filter((ep) => !episodes.includes(ep));
  const all = [...episodes, ...fallback];
  if (!all.length) {
    vscode.window.showInformationMessage('没有找到集号。先确认 _进度.md。');
    return null;
  }
  return vscode.window.showQuickPick(all, { placeHolder: '选择集' });
}

function sendRefreshEpisodeData(extensionRoot, root, episode) {
  const qroot = shellQuote(root);
  const cmd = episode
    ? `python3 skills/n2d-review-ui/scripts/episode_app.py ${qroot} --episode ${shellQuote(episode)} --write --index && python3 skills/n2d-review-ui/scripts/board.py ${qroot} --write --markdown`
    : `python3 skills/n2d-review-ui/scripts/episode_app.py ${qroot} --all --write && python3 skills/n2d-review-ui/scripts/board.py ${qroot} --write --markdown`;
  const term = openArmoryTerminal(extensionRoot, '', true);
  term.sendText(cmd, true);
}

async function openN2DBoard(node, extensionRoot) {
  const root = await pickN2DWorkRoot(node, extensionRoot);
  if (!root) return;
  const htmlPath = path.join(root, '生产数据', 'board.html');
  if (exists(htmlPath)) {
    vscode.commands.executeCommand('vscode.open', vscode.Uri.file(htmlPath), { viewColumn: vscode.ViewColumn.Beside });
    return;
  }
  sendRefreshEpisodeData(extensionRoot, root, null);
  vscode.window.showInformationMessage('生产看板未生成，已在终端启动刷新。');
}

async function openN2DEpisodeApp(node, extensionRoot) {
  const root = await pickN2DWorkRoot(node, extensionRoot);
  if (!root) return;
  const episode = await pickEpisode(root);
  if (!episode) return;
  const htmlPath = path.join(root, '生产数据', `episode_app_${episode}.html`);
  if (exists(htmlPath)) {
    vscode.commands.executeCommand('vscode.open', vscode.Uri.file(htmlPath), { viewColumn: vscode.ViewColumn.Beside });
    return;
  }
  sendRefreshEpisodeData(extensionRoot, root, episode);
  vscode.window.showInformationMessage(`${episode} 工作台未生成，已在终端启动刷新。`);
}

async function refreshN2DEpisodeData(node, extensionRoot) {
  const root = await pickN2DWorkRoot(node, extensionRoot);
  if (!root) return;
  sendRefreshEpisodeData(extensionRoot, root, null);
}

function activate(context) {
  const { docsRoot, skillsDir } = resolveAssetRoots(context.extensionPath);
  const provider = new FactoryProvider(context.extensionPath, docsRoot, skillsDir);
  const directoryWatcher = new VisibleDirectoryWatcher(context, provider, context.extensionPath);

  // Create the view (not just register the provider) so we get visibility events.
  const treeView = vscode.window.createTreeView('animeArmoryView', { treeDataProvider: provider });
  directoryWatcher.bind(treeView);
  let termOpened = false;
  const maybeOpenTerminal = () => {
    if (termOpened || !treeView.visible) return;
    termOpened = true; // once per window session
    if (!vscode.workspace.getConfiguration('animeArmory').get('openTerminalOnReveal', true)) return;
    openArmoryTerminal(context.extensionPath, FIRST_OPEN_TERMINAL_MESSAGE, true);
  };
  const visibilitySub = treeView.onDidChangeVisibility(() => maybeOpenTerminal());
  maybeOpenTerminal(); // in case the view is already visible at activation

  context.subscriptions.push(
    treeView,
    directoryWatcher,
    visibilitySub,
    vscode.commands.registerCommand('animeArmory.openTerminal', () => openArmoryTerminal(context.extensionPath)),
    vscode.commands.registerCommand('animeArmory.refresh', () => provider.refresh()),
    vscode.commands.registerCommand('animeArmory.showMore', (node) => provider.showMore(node)),
    vscode.commands.registerCommand('animeArmory.openN2DBoard', (node) => openN2DBoard(node, context.extensionPath)),
    vscode.commands.registerCommand('animeArmory.openN2DEpisodeApp', (node) => openN2DEpisodeApp(node, context.extensionPath)),
    vscode.commands.registerCommand('animeArmory.refreshN2DEpisodeData', (node) => refreshN2DEpisodeData(node, context.extensionPath)),
    vscode.commands.registerCommand('animeArmory.selectRepo', async () => {
      const pick = await vscode.window.showOpenDialog({
        canSelectFolders: true, canSelectFiles: false, canSelectMany: false,
        openLabel: '选含 创作区 的项目根（用于作品区）',
      });
      if (!pick || !pick[0]) return;
      const dir = findProjectRoot(pick[0].fsPath) || pick[0].fsPath;
      await vscode.workspace.getConfiguration('animeArmory')
        .update('repoRoot', dir, vscode.ConfigurationTarget.Global);
      await vscode.workspace.getConfiguration('animeArmory')
        .update('useExternalWorks', true, vscode.ConfigurationTarget.Global);
      provider.refresh();
      vscode.window.showInformationMessage('作品区目录已设为：' + dir);
    }),
    // ── native-style passthroughs (extract Uri from node → built-in command) ──
    vscode.commands.registerCommand('animeArmory.revealInExplorer', (node) => {
      const uri = nodeUri(node);
      if (uri) vscode.commands.executeCommand('revealInExplorer', uri);
    }),
    vscode.commands.registerCommand('animeArmory.revealInOS', (node) => {
      const uri = nodeUri(node);
      if (uri) vscode.commands.executeCommand('revealFileInOS', uri);
    }),
    vscode.commands.registerCommand('animeArmory.openToSide', (node) => {
      const uri = nodeUri(node);
      if (uri) vscode.commands.executeCommand('vscode.open', uri, { viewColumn: vscode.ViewColumn.Beside });
    }),
    vscode.commands.registerCommand('animeArmory.openInTerminal', (node) => {
      const uri = nodeUri(node);
      if (!uri) return;
      // open at the folder (for a file, use its parent)
      const p = node.dirPath || (node.fsPath && path.dirname(node.fsPath)) || uri.fsPath;
      vscode.window.createTerminal({ name: 'anime-armory', cwd: p }).show();
    }),
    vscode.commands.registerCommand('animeArmory.copyPath', (node) => {
      const uri = nodeUri(node);
      if (uri) vscode.env.clipboard.writeText(uri.fsPath);
    }),
    vscode.commands.registerCommand('animeArmory.copyRelativePath', (node) => {
      const uri = nodeUri(node);
      if (!uri) return;
      const rel = vscode.workspace.asRelativePath(uri, false);
      vscode.env.clipboard.writeText(rel);
    }),
    // ── file management on writable (live-project) nodes ──────────────────────
    vscode.commands.registerCommand('animeArmory.newFile', (node) => createEntry(node, false, provider)),
    vscode.commands.registerCommand('animeArmory.newFolder', (node) => createEntry(node, true, provider)),
    vscode.commands.registerCommand('animeArmory.rename', async (node) => {
      const p = node && (node.dirPath || node.fsPath);
      if (!p) return;
      const cur = path.basename(p);
      const name = await vscode.window.showInputBox({ prompt: '重命名为', value: cur });
      if (!name || name === cur) return;
      const dest = path.join(path.dirname(p), name);
      try { await vscode.workspace.fs.rename(vscode.Uri.file(p), vscode.Uri.file(dest), { overwrite: false }); }
      catch (e) { vscode.window.showErrorMessage('重命名失败：' + e.message); return; }
      provider.invalidatePath(p);
      provider.invalidatePath(dest);
      provider.refreshPath(dest);
    }),
    vscode.commands.registerCommand('animeArmory.delete', async (node) => {
      const p = node && (node.dirPath || node.fsPath);
      if (!p) return;
      const ok = await vscode.window.showWarningMessage(
        `删除 “${path.basename(p)}”？此操作移到回收站。`, { modal: true }, '删除');
      if (ok !== '删除') return;
      try { await vscode.workspace.fs.delete(vscode.Uri.file(p), { recursive: true, useTrash: true }); }
      catch (e) { vscode.window.showErrorMessage('删除失败：' + e.message); return; }
      provider.invalidatePath(p);
      provider.refreshPath(path.dirname(p));
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(() => provider.refresh()),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('animeArmory.repoRoot') ||
          e.affectsConfiguration('animeArmory.useExternalWorks') ||
          e.affectsConfiguration('animeArmory.showSkills') ||
          e.affectsConfiguration('animeArmory.maxItemsPerDirectory')) {
        provider.refresh();
      }
    })
  );
  context.subscriptions.push(
    vscode.workspace.onDidChangeWorkspaceFolders(() => directoryWatcher.syncRoot()),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('animeArmory.repoRoot') ||
          e.affectsConfiguration('animeArmory.useExternalWorks') ||
          e.affectsConfiguration('animeArmory.maxWatchedDirectories')) {
        directoryWatcher.syncRoot();
      }
    })
  );
}
function deactivate() {}
module.exports = { activate, deactivate };
