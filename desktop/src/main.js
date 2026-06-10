// Electron main process — window + IPC for file system and the integrated terminal (node-pty).
// MVP scope: open a folder, read/write files, run a real shell. No second source of truth:
// the renderer only ever reads/writes the user's actual files on disk.
const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const url = require('url');
const { spawn } = require('child_process');

// skills 目录解析（让打包版也能用看板/命令面板）。优先级：
//   1) 环境变量 ARSENAL_SKILLS_DIR  2) 用户持久化设置(userData/settings.json)
//   3) 从 hint(作品根/打开的文件夹) 向上找 <dir>/skills/n2d-review-ui/scripts/board.py（作品本就在仓库内）
//   4) dev 相对路径 <app>/../../skills
function settingsPath() { return path.join(app.getPath('userData'), 'settings.json'); }
function loadSettings() { try { return JSON.parse(fs.readFileSync(settingsPath(), 'utf8')); } catch (_) { return {}; } }
function saveSettings(s) { try { fs.mkdirSync(path.dirname(settingsPath()), { recursive: true }); fs.writeFileSync(settingsPath(), JSON.stringify(s, null, 2)); } catch (_) {} }
function isSkillsDir(dir) { try { return !!dir && fs.existsSync(path.join(dir, 'n2d-review-ui', 'scripts', 'board.py')); } catch (_) { return false; } }
function resolveSkillsDir(hint) {
  if (isSkillsDir(process.env.ARSENAL_SKILLS_DIR)) return process.env.ARSENAL_SKILLS_DIR;
  const saved = loadSettings().skillsDir;
  if (isSkillsDir(saved)) return saved;
  let d = hint ? path.resolve(hint) : null;
  for (let i = 0; d && i < 10; i++) {
    if (isSkillsDir(path.join(d, 'skills'))) return path.join(d, 'skills');
    const parent = path.dirname(d);
    if (parent === d) break;
    d = parent;
  }
  const dev = path.join(__dirname, '..', '..', 'skills');
  return isSkillsDir(dev) ? dev : null;
}

let pty = null;
try {
  pty = require('node-pty');
} catch (err) {
  // node-pty 是原生模块；未 rebuild 时这里会失败。终端会提示用户跑 npm run rebuild。
  console.error('[main] node-pty 不可用（先 `npm run rebuild`）：', err.message);
}

let win = null;
const ptys = new Map();

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 820,
    backgroundColor: '#1e1e1e',
    title: 'anime-arsenal',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // MVP：本地工具加载本地文件（Monaco 的 file:// 资源 / 用户素材）。产品化前再收紧。
      webSecurity: false,
    },
  });
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  // 看板 iframe 的「点 Clip 跳深画布」走 window.open(file://…review_ui_第N集.html#clip=…)：
  // 不弹新 OS 窗口，转交 renderer 在 app 内开标签。
  win.webContents.setWindowOpenHandler(({ url: u }) => {
    if (u.startsWith('file:') && u.includes('review_ui_')) {
      win.webContents.send('deeplink:open', u);
      return { action: 'deny' };
    }
    if (u.startsWith('file:')) {
      return { action: 'allow', overrideBrowserWindowOptions: { backgroundColor: '#1e1e1e', webPreferences: { webSecurity: false } } };
    }
    return { action: 'deny' };
  });
}

app.whenReady().then(createWindow);

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('window-all-closed', () => {
  ptys.forEach((p) => { try { p.kill(); } catch (_) {} });
  ptys.clear();
  if (process.platform !== 'darwin') app.quit();
});

// ── 文件系统 ──
ipcMain.handle('dialog:openFolder', async () => {
  const res = await dialog.showOpenDialog(win, { properties: ['openDirectory'] });
  return res.canceled ? null : res.filePaths[0];
});

ipcMain.handle('fs:readDir', async (_e, dir) => {
  const ents = await fs.promises.readdir(dir, { withFileTypes: true });
  return ents
    .filter((d) => !d.name.startsWith('.') || d.name === '.claude') // 略过隐藏目录，保留 .claude
    .map((d) => ({ name: d.name, path: path.join(dir, d.name), isDir: d.isDirectory() }))
    .sort((a, b) => (a.isDir === b.isDir ? a.name.localeCompare(b.name, 'zh') : a.isDir ? -1 : 1));
});

ipcMain.handle('fs:readFile', async (_e, p) => fs.promises.readFile(p, 'utf8'));

ipcMain.handle('fs:writeFile', async (_e, p, content) => {
  await fs.promises.writeFile(p, content, 'utf8');
  return true;
});

// monaco-editor 的 min/vs 目录（file URL），renderer 用 AMD loader 加载，免打包。
ipcMain.handle('app:vsPath', async () => {
  const vs = path.join(__dirname, '..', 'node_modules', 'monaco-editor', 'min', 'vs');
  return url.pathToFileURL(vs).toString();
});

// ── 集成终端（node-pty） ──
ipcMain.handle('pty:create', (_e, opts) => {
  if (!pty) throw new Error('node-pty 未安装/未 rebuild：先在 desktop/ 跑 `npm install && npm run rebuild`');
  const { cwd, cols, rows } = opts || {};
  const shell = process.env.SHELL || (process.platform === 'win32' ? 'powershell.exe' : '/bin/zsh');
  const id = Date.now().toString(36) + Math.random().toString(16).slice(2);
  // 继承用户环境，但保证 UTF-8 locale：从 Finder/双击启动时 env 常无 LANG，zsh 会按 C locale
  // 把中文 cwd/输出的多字节字符拆坏（乱码）。任一 locale 变量已是 UTF-8 就不动，否则注入。
  const env = { ...process.env };
  const hasUtf8 = ['LC_ALL', 'LC_CTYPE', 'LANG'].some((k) => /utf-?8/i.test(env[k] || ''));
  if (!hasUtf8) { env.LANG = 'en_US.UTF-8'; env.LC_CTYPE = 'en_US.UTF-8'; }
  const proc = pty.spawn(shell, [], {
    name: 'xterm-256color',
    cols: cols || 80,
    rows: rows || 24,
    cwd: cwd || process.env.HOME || process.cwd(),
    env, // conda activate / 跑 skills 都能用，且 UTF-8 不乱码
  });
  proc.onData((data) => { if (win && !win.isDestroyed()) win.webContents.send('pty:data:' + id, data); });
  proc.onExit(() => { ptys.delete(id); if (win && !win.isDestroyed()) win.webContents.send('pty:exit:' + id); });
  ptys.set(id, proc);
  return id;
});

ipcMain.on('pty:input', (_e, id, data) => { const p = ptys.get(id); if (p) p.write(data); });
ipcMain.on('pty:resize', (_e, id, cols, rows) => { const p = ptys.get(id); if (p) { try { p.resize(cols, rows); } catch (_) {} } });
ipcMain.on('pty:dispose', (_e, id) => { const p = ptys.get(id); if (p) { try { p.kill(); } catch (_) {} ptys.delete(id); } });

// ── 生产看板（n2d-review-ui/board.py）──
// 扫描打开的文件夹（含自身，≤2 层）里带 _进度.md 的作品根。
ipcMain.handle('board:findWorks', async (_e, root) => {
  const SKIP = new Set(['node_modules', '生产数据', '出图', '出视频', '合成', '脚本', '设定库', '废料']);
  const found = [];
  async function scan(dir, depth) {
    let ents;
    try { ents = await fs.promises.readdir(dir, { withFileTypes: true }); } catch (_) { return; }
    if (ents.some((d) => d.isFile() && d.name === '_进度.md')) found.push(dir);
    if (depth <= 0) return;
    for (const d of ents) {
      if (d.isDirectory() && !d.name.startsWith('.') && !SKIP.has(d.name)) await scan(path.join(dir, d.name), depth - 1);
    }
  }
  await scan(root, 2);
  return found;
});

const SKILLS_NOT_FOUND = '找不到 skills 目录：命令面板「⚙️ 设置 skills 目录」，或设环境变量 ARSENAL_SKILLS_DIR';

// 跑 board.py --write，返回生成的 board.html 的 file URL。
ipcMain.handle('board:generate', async (_e, workRoot) => {
  const skills = resolveSkillsDir(workRoot);
  if (!skills) return { ok: false, error: SKILLS_NOT_FOUND };
  const script = path.join(skills, 'n2d-review-ui', 'scripts', 'board.py');
  return new Promise((resolve) => {
    const py = process.env.PYTHON || 'python3';
    const proc = spawn(py, [script, workRoot, '--write'], { cwd: path.dirname(skills) });
    let err = '';
    proc.stderr.on('data', (d) => { err += d.toString(); });
    proc.on('error', (e) => resolve({ ok: false, error: e.message }));
    proc.on('close', (code) => {
      const html = path.join(workRoot, '生产数据', 'board.html');
      if (code === 0 && fs.existsSync(html)) resolve({ ok: true, url: url.pathToFileURL(html).toString() });
      else resolve({ ok: false, error: (err.trim() || `board.py 退出码 ${code}`) });
    });
  });
});

// 文件监听：作品的 _进度.md / 脚本 / 生产数据 变化 → 通知 renderer 重生成（避开 board 自身输出，防死循环）。
const boardWatchers = new Map();
ipcMain.handle('board:watch', (_e, workRoot) => {
  if (boardWatchers.has(workRoot)) return workRoot;
  let timer = null;
  const fire = (_event, filename) => {
    if (filename && /^board\.(html|json)/.test(path.basename(String(filename)))) return; // 别被自己触发
    clearTimeout(timer);
    timer = setTimeout(() => { if (win && !win.isDestroyed()) win.webContents.send('board:changed', workRoot); }, 700);
  };
  const ws = [];
  for (const t of [path.join(workRoot, '_进度.md'), path.join(workRoot, '脚本'), path.join(workRoot, '生产数据')]) {
    try { ws.push(fs.watch(t, { recursive: true }, fire)); } catch (_) {}
  }
  boardWatchers.set(workRoot, ws);
  return workRoot;
});
ipcMain.on('board:unwatch', (_e, workRoot) => {
  const ws = boardWatchers.get(workRoot);
  if (ws) { ws.forEach((w) => { try { w.close(); } catch (_) {} }); boardWatchers.delete(workRoot); }
});

// 命令面板用：跑 board.py 出最新 board.json 并返回（含 summary.first_action.cmd / 各集 frontier.cmd）。
ipcMain.handle('board:manifest', async (_e, workRoot) => {
  const skills = resolveSkillsDir(workRoot);
  if (skills) {
    const script = path.join(skills, 'n2d-review-ui', 'scripts', 'board.py');
    await new Promise((resolve) => {
      const py = process.env.PYTHON || 'python3';
      const proc = spawn(py, [script, workRoot, '--write'], { cwd: path.dirname(skills) });
      proc.on('error', () => resolve());
      proc.on('close', () => resolve());
    });
  }
  try { return JSON.parse(fs.readFileSync(path.join(workRoot, '生产数据', 'board.json'), 'utf8')); }
  catch (e) { return { error: skills ? e.message : SKILLS_NOT_FOUND }; }
});

// 命令面板构造绝对路径命令用：按 hint(作品根/打开的文件夹) 解析 skills，找不到返回 null。
ipcMain.handle('app:skillsDir', async (_e, hint) => resolveSkillsDir(hint));

// 手动指定 skills 目录（打包版/仓库外运行的兜底）。
ipcMain.handle('config:setSkillsDir', async () => {
  const res = await dialog.showOpenDialog(win, { properties: ['openDirectory'], title: '选择 skills 目录（含 n2d-review-ui/scripts/board.py）' });
  if (res.canceled || !res.filePaths[0]) return { ok: false };
  const dir = res.filePaths[0];
  if (!isSkillsDir(dir)) return { ok: false, error: '该目录不像 skills（缺 n2d-review-ui/scripts/board.py）' };
  const s = loadSettings(); s.skillsDir = dir; saveSettings(s);
  return { ok: true, skillsDir: dir };
});
ipcMain.handle('config:get', async () => ({ skillsDir: resolveSkillsDir(null), savedSkillsDir: loadSettings().skillsDir || '' }));

// 启动即打开的文件夹：`electron . <folder>` 或 INIT_FOLDER=<folder>（VS Code 的 `code <dir>` 体验）。
function initialFolder() {
  const args = process.argv.slice(app.isPackaged ? 1 : 2);
  for (const a of args) {
    if (a && !a.startsWith('-') && a !== '.') {
      try { if (fs.statSync(a).isDirectory()) return path.resolve(a); } catch (_) {}
    }
  }
  const env = process.env.INIT_FOLDER;
  if (env) { try { if (fs.statSync(env).isDirectory()) return path.resolve(env); } catch (_) {} }
  return null;
}
ipcMain.handle('app:initFolder', async () => initialFolder());

// ── 命令执行日志（命令面板跑/填的命令落 jsonl，留审计） ──
const LOG_PATH = path.join(app.getPath('userData'), 'command_log.jsonl');
ipcMain.handle('log:append', async (_e, entry) => {
  try {
    await fs.promises.mkdir(path.dirname(LOG_PATH), { recursive: true });
    await fs.promises.appendFile(LOG_PATH, JSON.stringify({ ts: new Date().toISOString(), ...(entry || {}) }) + '\n', 'utf8');
  } catch (_) {}
  return LOG_PATH;
});
ipcMain.handle('log:path', async () => LOG_PATH);

// ── 全局搜索：优先 ripgrep（快·尊重 .gitignore），缺则 node 兜底遍历 ──
const SEARCH_SKIP_DIRS = new Set(['node_modules', '.git', '出图', '出视频', '合成', '废料', '_voicecache', '_clipcache', 'dist', 'out']);
const SEARCH_SKIP_EXT = new Set(['.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mov', '.wav', '.mp3', '.aiff', '.safetensors', '.bin', '.docx', '.zip', '.pdf']);
const SEARCH_CAP = 400;

function nodeSearch(root, query) {
  const out = [];
  const q = query.toLowerCase();
  let scanned = 0;
  async function walk(dir, depth) {
    if (out.length >= SEARCH_CAP || scanned > 20000 || depth > 9) return;
    let ents; try { ents = await fs.promises.readdir(dir, { withFileTypes: true }); } catch (_) { return; }
    for (const e of ents) {
      if (out.length >= SEARCH_CAP) return;
      if (e.name.startsWith('.') && e.name !== '.claude') continue;
      const fp = path.join(dir, e.name);
      if (e.isDirectory()) { if (!SEARCH_SKIP_DIRS.has(e.name)) await walk(fp, depth + 1); continue; }
      if (SEARCH_SKIP_EXT.has(path.extname(e.name).toLowerCase())) continue;
      scanned++;
      try {
        const st = await fs.promises.stat(fp);
        if (st.size > 2 * 1024 * 1024) continue;
        const lines = (await fs.promises.readFile(fp, 'utf8')).split('\n');
        for (let i = 0; i < lines.length; i++) {
          if (lines[i].toLowerCase().includes(q)) {
            out.push({ file: fp, line: i + 1, text: lines[i].trim().slice(0, 200) });
            if (out.length >= SEARCH_CAP) return;
          }
        }
      } catch (_) {}
    }
  }
  return walk(root, 0).then(() => out);
}

ipcMain.handle('search:run', async (_e, root, query) => {
  if (!root || !query || !query.trim()) return { engine: '', results: [] };
  const rgOut = await new Promise((resolve) => {
    const args = ['--line-number', '--no-heading', '--color', 'never', '--max-columns', '300', '-S',
      '-g', '!**/{node_modules,.git,出图,出视频,合成,废料,dist,out}/**', '-g', '!*.{png,jpg,jpeg,mp4,mov,wav,mp3,aiff,safetensors,bin,docx,zip,pdf}',
      '-e', query, root];
    const p = spawn('rg', args, { cwd: root });
    let out = '';
    p.stdout.on('data', (d) => { out += d.toString(); if (out.length > 400000) { try { p.kill(); } catch (_) {} } });
    p.on('error', () => resolve(null));
    p.on('close', () => resolve(out));
  });
  if (rgOut !== null) {
    const results = [];
    for (const line of rgOut.split('\n')) {
      const m = line.match(/^(.*?):(\d+):(.*)$/);
      if (m) { results.push({ file: m[1], line: +m[2], text: m[3].slice(0, 200) }); if (results.length >= SEARCH_CAP) break; }
    }
    return { engine: 'ripgrep', results };
  }
  return { engine: 'node', results: await nodeSearch(root, query) };
});

// ── git 面板：分支 + 改动文件列表 ──
function git(root, args) {
  return new Promise((resolve) => {
    const p = spawn('git', ['-C', root, ...args]);
    let out = '', err = '';
    p.stdout.on('data', (d) => { out += d.toString(); });
    p.stderr.on('data', (d) => { err += d.toString(); });
    p.on('error', () => resolve({ code: -1, out: '', err: 'git 不可用' }));
    p.on('close', (code) => resolve({ code, out, err }));
  });
}
ipcMain.handle('git:status', async (_e, root) => {
  if (!root) return { isRepo: false };
  const top = await git(root, ['rev-parse', '--show-toplevel']);
  if (top.code !== 0) return { isRepo: false };
  const toplevel = top.out.trim();
  const br = await git(root, ['rev-parse', '--abbrev-ref', 'HEAD']);
  const st = await git(root, ['status', '--porcelain']);
  const files = st.out.split('\n').filter(Boolean).map((l) => ({ status: l.slice(0, 2).trim() || '??', file: l.slice(3) }));
  return { isRepo: true, toplevel, branch: br.out.trim(), files };
});

// ── 环境探测：重 AI 步骤在本机跑不跑得起来 ──
// 通过登录 shell 跑（-lc，sources profile），让探测看到的 PATH/conda 与集成终端一致。
function shLogin(cmd) {
  return new Promise((resolve) => {
    const shell = process.env.SHELL || '/bin/zsh';
    const p = spawn(shell, ['-lc', cmd]);
    let out = '';
    p.stdout.on('data', (d) => { out += d.toString(); });
    p.stderr.on('data', () => {});
    p.on('error', () => resolve(''));
    p.on('close', () => resolve(out));
  });
}

// CLAUDE.md 点名的重 AI conda 环境（生成音频/音乐/换脸）。不硬编码任何私有后端 IP（项目私有）。
const KNOWN_ENVS = ['cosyvoice', 'acestep', 'fish-speech', 'facefusion'];

ipcMain.handle('env:probe', async () => {
  const script = [
    'for t in python3 ffmpeg ffprobe conda git claude; do echo "TOOL|$t|$(command -v $t 2>/dev/null)"; done',
    'echo "PYV|$(python3 --version 2>&1 | head -1)"',
    'echo "FFV|$(ffmpeg -version 2>/dev/null | head -1)"',
    'if command -v conda >/dev/null 2>&1; then echo "ENVS_START"; conda env list 2>/dev/null; echo "ENVS_END"; fi',
  ].join('\n');
  const out = await shLogin(script);
  const tools = {};
  let pyv = '', ffv = '', inEnvs = false;
  const envs = [];
  for (const line of out.split('\n')) {
    if (line.startsWith('TOOL|')) { const parts = line.split('|'); tools[parts[1]] = { ok: !!parts[2], path: parts[2] || '' }; }
    else if (line.startsWith('PYV|')) pyv = line.slice(4).trim();
    else if (line.startsWith('FFV|')) ffv = line.slice(4).trim();
    else if (line.trim() === 'ENVS_START') inEnvs = true;
    else if (line.trim() === 'ENVS_END') inEnvs = false;
    else if (inEnvs) { const t = line.trim(); if (t && !t.startsWith('#')) { const name = t.split(/\s+/)[0]; if (name) envs.push(name); } }
  }
  if (tools.python3) tools.python3.version = pyv;
  if (tools.ffmpeg) tools.ffmpeg.version = ffv;
  const known = {};
  for (const e of KNOWN_ENVS) known[e] = envs.includes(e);
  return { tools, conda: { available: !!(tools.conda && tools.conda.ok), envs, known }, knownList: KNOWN_ENVS };
});
