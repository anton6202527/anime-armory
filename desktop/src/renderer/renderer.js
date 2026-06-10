/* Renderer: file tree + Monaco tabs + integrated resizable terminal. No bundler.
 * Monaco is loaded via its AMD loader from local node_modules; xterm via UMD globals. */
(async function () {
  const $ = (s) => document.querySelector(s);
  const api = window.api;

  let rootPath = null;
  let editor = null;
  let monacoReady = false;
  let activePath = null;
  const openTabs = new Map(); // path -> { model, tabEl, dirty }

  // ───────────────────────── Monaco ─────────────────────────
  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = src; s.onload = res; s.onerror = () => rej(new Error('load fail: ' + src));
      document.head.appendChild(s);
    });
  }

  async function initMonaco() {
    const vs = await api.vsPath(); // file:///.../monaco-editor/min/vs
    // 空 worker stub：避免 file:// worker 跨域坑。基础语法高亮（Monarch）在主线程跑，照样有色；
    // 高级 IntelliSense（补全/校验）走 worker，MVP 暂不需要，后续接打包再开。
    window.MonacoEnvironment = { getWorkerUrl: () => 'data:text/javascript;charset=utf-8,' };
    await loadScript(vs + '/loader.js');
    window.require.config({ paths: { vs } });
    await new Promise((res) => window.require(['vs/editor/editor.main'], res));
    editor = window.monaco.editor.create($('#editor'), {
      theme: 'vs-dark', automaticLayout: true, fontSize: 13,
      minimap: { enabled: false }, scrollBeyondLastLine: false, renderWhitespace: 'selection',
    });
    editor.onDidChangeModelContent(() => markDirty(activePath, true));
    editor.addCommand(window.monaco.KeyMod.CtrlCmd | window.monaco.KeyCode.KeyS, saveActive);
    monacoReady = true;
  }

  const LANG = {
    md: 'markdown', markdown: 'markdown', json: 'json', js: 'javascript', mjs: 'javascript',
    ts: 'typescript', py: 'python', sh: 'shell', bash: 'shell', html: 'html', css: 'css',
    yml: 'yaml', yaml: 'yaml', xml: 'xml', srt: 'plaintext', txt: 'plaintext',
  };
  const langFromPath = (p) => LANG[(p.split('.').pop() || '').toLowerCase()] || 'plaintext';
  const baseName = (p) => p.split('/').pop();

  // ───────────────────────── file tree ─────────────────────────
  async function openRoot(p) {
    rootPath = p;
    $('#rootName').textContent = baseName(p);
    $('#statusCwd').textContent = p;
    const tree = $('#tree');
    tree.innerHTML = '';
    tree.appendChild(await dirChildren(p, 0));
  }

  async function dirChildren(dir, depth) {
    const wrap = document.createElement('div');
    let ents = [];
    try { ents = await api.readDir(dir); } catch (e) { /* permission etc. */ }
    for (const e of ents) wrap.appendChild(nodeEl(e, depth));
    return wrap;
  }

  function nodeEl(entry, depth) {
    const row = document.createElement('div');
    row.className = 'node' + (entry.isDir ? ' dir' : '');
    row.style.paddingLeft = 8 + depth * 14 + 'px';
    row.dataset.path = entry.path;
    const setLabel = (open) => { row.textContent = (entry.isDir ? (open ? '▾ ' : '▸ ') : '   ') + entry.name; };
    setLabel(false);
    let expanded = false, childWrap = null;
    row.addEventListener('click', async (ev) => {
      ev.stopPropagation();
      if (entry.isDir) {
        expanded = !expanded; setLabel(expanded);
        if (expanded) {
          if (!childWrap) { childWrap = await dirChildren(entry.path, depth + 1); row.after(childWrap); }
          else childWrap.style.display = '';
        } else if (childWrap) childWrap.style.display = 'none';
      } else {
        openFile(entry.path);
      }
    });
    return row;
  }

  // ───────────────────────── tabs / editor（file 标签 + deep 深画布标签） ─────────────────────────
  async function openFile(p) {
    if (!monacoReady) return;
    if (!openTabs.has(p)) {
      let content = '';
      try { content = await api.readFile(p); } catch (e) { content = '// 无法读取：' + e.message; }
      const uri = window.monaco.Uri.file(p);
      const model = window.monaco.editor.getModel(uri) || window.monaco.editor.createModel(content, langFromPath(p), uri);
      openTabs.set(p, { kind: 'file', model, tabEl: addTab(p, baseName(p)), dirty: false });
    }
    activate(p);
  }

  // 看板深链：在 app 内开一个深画布标签（iframe 加载 review_ui_第N集.html#clip=…）
  function openDeep(url) {
    const htmlPath = url.split('#')[0];
    const fname = decodeURIComponent(htmlPath.split('/').pop() || '');
    const m = fname.match(/review_ui_(.+)\.html/);
    const label = (m ? m[1] : '深画布') + ' 深画布';
    if (!openTabs.has(htmlPath)) openTabs.set(htmlPath, { kind: 'deep', url, tabEl: addTab(htmlPath, label) });
    else openTabs.get(htmlPath).url = url; // 同集不同 Clip：更新到新 #clip
    activate(htmlPath);
  }

  function addTab(id, label) {
    const tab = document.createElement('div');
    tab.className = 'tab';
    tab.innerHTML = `<span class="name">${escapeHtml(label)}</span><button class="x" title="关闭">✕</button>`;
    tab.addEventListener('click', (e) => { if (!e.target.classList.contains('x')) activate(id); });
    tab.querySelector('.x').addEventListener('click', (e) => { e.stopPropagation(); closeTab(id); });
    $('#tabs').appendChild(tab);
    return tab;
  }

  function activate(id) {
    const rec = openTabs.get(id);
    if (!rec) return;
    if (rec.kind === 'file') {
      activePath = id;
      $('#deepFrame').classList.add('hidden');
      $('#editor').classList.remove('hidden');
      editor.setModel(rec.model);
      editor.layout();
      editor.focus();
      $('#statusCwd').textContent = id;
    } else {
      activePath = null;
      $('#deepFrame').src = rec.url; // 含 #clip：同 doc 改 hash → review_ui 内 focusFromHash 定位；异 doc → 重载
      $('#editor').classList.add('hidden');
      $('#deepFrame').classList.remove('hidden');
      $('#statusCwd').textContent = decodeURIComponent((rec.url.split('/').pop() || ''));
    }
    for (const [tid, r] of openTabs) r.tabEl.classList.toggle('active', tid === id);
    document.querySelectorAll('.node').forEach((n) => n.classList.toggle('active', n.dataset.path === id));
  }

  function closeTab(id) {
    const rec = openTabs.get(id);
    if (!rec) return;
    const wasActive = rec.tabEl.classList.contains('active');
    rec.tabEl.remove();
    if (rec.kind === 'file') rec.model.dispose();
    openTabs.delete(id);
    if (wasActive) {
      const next = [...openTabs.keys()].pop();
      if (next) activate(next);
      else { activePath = null; editor.setModel(null); $('#deepFrame').classList.add('hidden'); $('#editor').classList.remove('hidden'); }
    }
  }

  function markDirty(p, dirty) {
    const rec = openTabs.get(p);
    if (!rec || rec.kind !== 'file' || rec.dirty === dirty) return;
    rec.dirty = dirty;
    const nameEl = rec.tabEl.querySelector('.name');
    nameEl.innerHTML = (dirty ? '<span class="dot">●</span> ' : '') + escapeHtml(baseName(p));
  }

  async function saveActive() {
    if (!activePath) return;
    const rec = openTabs.get(activePath);
    try {
      await api.writeFile(activePath, rec.model.getValue());
      markDirty(activePath, false);
      flashSave('已保存 ' + baseName(activePath));
    } catch (e) {
      flashSave('保存失败：' + e.message);
    }
  }

  let saveTimer;
  function flashSave(msg) {
    const el = $('#statusSave'); el.textContent = msg;
    clearTimeout(saveTimer); saveTimer = setTimeout(() => (el.textContent = ''), 2500);
  }
  const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // ───────────────────────── terminal ─────────────────────────
  const TerminalCtor = window.Terminal || (window.xterm && window.xterm.Terminal);
  const FitCtor = (window.FitAddon && window.FitAddon.FitAddon) || window.FitAddon;
  let term = null, fit = null, termId = null, offData = null, offExit = null;

  async function startTerminal() {
    if (!TerminalCtor) { console.error('xterm 未加载'); return; }
    // 重开前拆掉旧 pty 的 data/exit 监听，否则每次「重开」都会泄漏一个 IPC 监听器
    if (term) { try { offData && offData(); offExit && offExit(); } catch (_) {} if (termId) api.term.dispose(termId); term.dispose(); }
    term = new TerminalCtor({ fontSize: 12, cursorBlink: true, theme: { background: '#1e1e1e', foreground: '#cccccc' } });
    fit = FitCtor ? new FitCtor() : null;
    if (fit) term.loadAddon(fit);
    term.open($('#terminal'));
    fitTerm();
    try {
      termId = await api.term.create({ cwd: rootPath || undefined, cols: term.cols, rows: term.rows });
    } catch (e) {
      term.writeln('\x1b[31m终端启动失败：' + e.message + '\x1b[0m');
      term.writeln('在 desktop/ 跑：npm install && npm run rebuild');
      return;
    }
    offData = api.term.onData(termId, (d) => term.write(d));
    offExit = api.term.onExit(termId, () => term.writeln('\r\n\x1b[90m[进程已退出，＋重开 新建]\x1b[0m'));
    term.onData((d) => api.term.write(termId, d));
    $('#statusShell').textContent = 'zsh';
  }

  function fitTerm() {
    if (!fit || !term) return;
    try { fit.fit(); if (termId) api.term.resize(termId, term.cols, term.rows); } catch (_) {}
  }

  // ───────────────────────── resizable terminal gutter ─────────────────────────
  function initGutter() {
    const panel = $('#panel'), mainpane = $('#mainpane');
    let dragging = false;
    $('#gutter').addEventListener('mousedown', (e) => { dragging = true; document.body.style.cursor = 'row-resize'; e.preventDefault(); });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const rect = mainpane.getBoundingClientRect();
      let h = rect.bottom - e.clientY;
      h = Math.max(80, Math.min(rect.height - 120, h)); // 往上拉大 / 往下拉小
      panel.style.height = h + 'px';
      fitTerm();
    });
    window.addEventListener('mouseup', () => { if (dragging) { dragging = false; document.body.style.cursor = ''; fitTerm(); } });
  }

  // ───────────────────────── 生产看板面板（命令行+画布同窗联动） ─────────────────────────
  let boardOpen = false, boardWork = null, autoRefresh = false, offBoardChange = null;

  async function refreshWorkList() {
    const sel = $('#boardWork');
    sel.innerHTML = '';
    const works = rootPath ? await api.board.findWorks(rootPath) : [];
    if (!works.length) {
      const o = document.createElement('option'); o.value = ''; o.textContent = '(无带 _进度.md 的作品)';
      sel.appendChild(o); boardWork = null; return;
    }
    for (const w of works) {
      const o = document.createElement('option'); o.value = w; o.textContent = w.split('/').pop();
      sel.appendChild(o);
    }
    // 尽量沿用当前选择
    boardWork = works.includes(boardWork) ? boardWork : works[0];
    sel.value = boardWork;
  }

  async function generateBoard() {
    if (!boardWork) { $('#boardStatus').textContent = '先选作品'; return; }
    $('#boardStatus').textContent = '生成中…';
    const r = await api.board.generate(boardWork);
    if (r.ok) { $('#boardFrame').src = r.url + '?t=' + Date.now(); $('#boardStatus').textContent = ''; }
    else { $('#boardStatus').textContent = '失败：' + r.error; }
  }

  async function toggleBoard() {
    boardOpen = !boardOpen;
    $('#boardPane').style.display = boardOpen ? 'flex' : 'none';
    $('#vgutter').style.display = boardOpen ? 'block' : 'none';
    $('#actBoard').classList.toggle('on', boardOpen);
    if (boardOpen) { await refreshWorkList(); if (boardWork) await generateBoard(); }
    if (editor) editor.layout();
  }

  async function setAutoRefresh(on) {
    autoRefresh = on;
    if (!boardWork) return;
    if (on) {
      await api.board.watch(boardWork);
      if (!offBoardChange) offBoardChange = api.board.onChanged((wr) => { if (autoRefresh && wr === boardWork) generateBoard(); });
    } else {
      api.board.unwatch(boardWork);
    }
  }

  function initVGutter() {
    const pane = $('#boardPane');
    let dragging = false;
    $('#vgutter').addEventListener('mousedown', (e) => { dragging = true; document.body.style.cursor = 'col-resize'; e.preventDefault(); });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const row = $('#editorRow').getBoundingClientRect();
      let w = row.right - e.clientX;
      w = Math.max(280, Math.min(row.width - 200, w));
      pane.style.width = w + 'px';
    });
    window.addEventListener('mouseup', () => { if (dragging) { dragging = false; document.body.style.cursor = ''; if (editor) editor.layout(); } });
  }

  $('#actBoard').addEventListener('click', toggleBoard);
  $('#boardWork').addEventListener('change', async (e) => {
    if (autoRefresh && boardWork) api.board.unwatch(boardWork);
    boardWork = e.target.value || null;
    await generateBoard();
    if (autoRefresh) await setAutoRefresh(true);
  });
  $('#boardRefresh').addEventListener('click', generateBoard);
  $('#boardAuto').addEventListener('change', (e) => setAutoRefresh(e.target.checked));

  // ───────────────────────── 命令面板：一键跑下一步 skill ─────────────────────────
  let skillsDir = '', logPath = '';
  let palItems = [], palSel = 0;

  async function runInTerminal(text, enter) {
    if (!termId) await startTerminal();
    if (termId) api.term.write(termId, text + (enter ? '\r' : ''));
  }

  function buildPaletteItems(work, m) {
    const items = [];
    const fa = m && m.summary && m.summary.first_action;
    const sbEp = ((m && m.episodes) || []).find((e) => e.has_storyboard);
    // 下一步（多为 Claude /n2d-* 步或付费步）→ 填入终端，不自动回车
    if (fa && fa.cmd) {
      items.push({ title: `▶ 下一步：${fa.episode} ${fa.label || ''}（${fa.skill || ''}）`, sub: '填入终端 · 在 Claude Code 会话里执行： ' + fa.cmd, cmd: fa.cmd, run: false });
    }
    if (skillsDir) {
      // 确定性安全脚本 → 直接在终端跑
      const q = (rel) => `python3 "${skillsDir}/${rel}"`;
      items.push({ title: '🔄 刷新看板（board.py）', sub: work, cmd: `${q('n2d-review-ui/scripts/board.py')} "${work}" --write`, run: true });
      if (sbEp) {
        items.push({ title: `📊 机器评分 ${sbEp.episode}（score --run-checks）`, sub: '机检/一致性/视觉 → score_*.json（驱动看板 QA 描边）', cmd: `${q('n2d-score/scripts/score.py')} "${work}" ${sbEp.episode} --run-checks --threshold 85`, run: true });
        items.push({ title: `🚦 image 闸门检查 ${sbEp.episode}（gate --stage image）`, sub: '出图前确定性自检（只读）', cmd: `${q('n2d-review/scripts/gate.py')} "${work}" ${sbEp.episode} --stage image`, run: true });
      }
    } else {
      items.push({ title: '⚙️ 设置 skills 目录…', sub: '找不到 skills（打包版/仓库外运行需指定）——点此选择含 n2d-review-ui/scripts/board.py 的目录', openSkillsConfig: true, run: false });
    }
    for (const e of ((m && m.episodes) || [])) {
      if (e.frontier && e.frontier.cmd && (!fa || e.episode !== fa.episode)) {
        items.push({ title: `· ${e.episode} 下一步：${e.frontier.label || ''}`, sub: '填入终端（' + (e.frontier.skill || '') + '）： ' + e.frontier.cmd, cmd: e.frontier.cmd, run: false });
      }
    }
    items.push({ title: '📜 命令日志（编辑器打开）', sub: logPath, openLog: true, run: false });
    return items;
  }

  function renderPalette(filter) {
    const list = $('#palList');
    const f = (filter || '').toLowerCase();
    const shown = palItems.filter((it) => !f || (it.title + ' ' + it.sub).toLowerCase().includes(f));
    palSel = Math.max(0, Math.min(palSel, shown.length - 1));
    list._shown = shown;
    if (!shown.length) { list.innerHTML = '<div class="pal-item"><div class="pi-empty">无匹配命令（先「打开」含 _进度.md 的作品）</div></div>'; return; }
    list.innerHTML = shown.map((it, i) =>
      `<div class="pal-item ${it.run ? 'run' : 'prefill'} ${i === palSel ? 'sel' : ''}" data-i="${i}"><div class="pi-title">${escapeHtml(it.title)}</div><div class="pi-sub">${escapeHtml(it.sub)}</div></div>`).join('');
    [...list.querySelectorAll('.pal-item')].forEach((el) => {
      el.addEventListener('mousemove', () => { palSel = +el.dataset.i; highlightPalette(); });
      el.addEventListener('click', () => choosePalette(+el.dataset.i));
    });
  }
  function highlightPalette() {
    [...$('#palList').querySelectorAll('.pal-item')].forEach((el, i) => el.classList.toggle('sel', i === palSel));
  }
  async function choosePalette(i) {
    const it = ($('#palList')._shown || [])[i];
    if (!it) return;
    closePalette();
    if (it.openSkillsConfig) {
      const r = await api.config.setSkillsDir();
      if (r && r.ok) { skillsDir = await api.skillsDir(boardWork || rootPath || null); flashSave('已设 skills 目录：' + r.skillsDir); }
      else if (r && r.error) flashSave(r.error);
      return;
    }
    if (it.openLog) { if (logPath) openFile(logPath); return; }
    runInTerminal(it.cmd, it.run);
    api.log.append({ work: boardWork, tier: it.run ? 'run' : 'prefill', cmd: it.cmd });
    flashSave(it.run ? '已在终端运行：' + it.cmd : '已填入终端，回车执行：' + it.cmd);
  }
  function closePalette() { $('#palette').classList.add('hidden'); }

  async function openPalette() {
    let work = boardWork;
    if (!work && rootPath) { const ws = await api.board.findWorks(rootPath); work = ws[0] || null; boardWork = work; }
    skillsDir = await api.skillsDir(work || rootPath || null);
    palItems = [];
    if (work) {
      const m = await api.board.manifest(work);
      palItems = buildPaletteItems(work, (m && !m.error) ? m : {});
    } else if (!skillsDir) {
      palItems = [{ title: '⚙️ 设置 skills 目录…', sub: '找不到 skills——点此选择含 n2d-review-ui/scripts/board.py 的目录', openSkillsConfig: true, run: false }];
    }
    palSel = 0;
    $('#palette').classList.remove('hidden');
    const inp = $('#palInput'); inp.value = ''; renderPalette(''); inp.focus();
  }

  $('#actPalette').addEventListener('click', openPalette);
  $('#palInput').addEventListener('input', (e) => { palSel = 0; renderPalette(e.target.value); });
  $('#palInput').addEventListener('keydown', (e) => {
    const n = ($('#palList')._shown || []).length;
    if (e.key === 'ArrowDown') { e.preventDefault(); palSel = Math.min(n - 1, palSel + 1); highlightPalette(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); palSel = Math.max(0, palSel - 1); highlightPalette(); }
    else if (e.key === 'Enter') { e.preventDefault(); choosePalette(palSel); }
    else if (e.key === 'Escape') { e.preventDefault(); closePalette(); }
  });
  $('#palette').addEventListener('mousedown', (e) => { if (e.target.id === 'palette') closePalette(); });
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'p' || e.key === 'P')) { e.preventDefault(); openPalette(); }
  });

  // ───────────────────────── 状态栏：环境可用性探测 ─────────────────────────
  let envData = null;

  async function probeEnv() {
    const el = $('#statusEnv');
    el.textContent = '环境 ⏳'; el.className = '';
    const r = await api.env.probe();
    envData = r;
    const py = !!(r.tools.python3 && r.tools.python3.ok);
    const ff = !!(r.tools.ffmpeg && r.tools.ffmpeg.ok);
    const known = r.conda.known || {};
    const kn = Object.keys(known).length, kok = Object.values(known).filter(Boolean).length;
    el.textContent = `环境 py${py ? '✓' : '✗'} ffmpeg${ff ? '✓' : '✗'} conda ${r.conda.available ? kok + '/' + kn : '✗'}`;
    el.className = (!py || !ff) ? 'bad' : ((!r.conda.available || kok < kn) ? 'warn' : '');
    if (!$('#envPop').classList.contains('hidden')) renderEnvPop();
  }

  function renderEnvPop() {
    const r = envData; if (!r) return;
    const tool = (name, label) => {
      const t = r.tools[name] || {};
      return `<div class="erow"><span>${label} <span class="${t.ok ? 'ok' : 'no'}">${t.ok ? '✓' : '✗'}</span></span><span class="p">${escapeHtml(t.version || t.path || '未找到')}</span></div>`;
    };
    const envRow = (name) => `<div class="erow"><span>${escapeHtml(name)} <span class="${r.conda.known[name] ? 'ok' : 'no'}">${r.conda.known[name] ? '✓ 已装' : '✗ 缺'}</span></span></div>`;
    const allKnown = (r.knownList || []).every((e) => r.conda.known[e]);
    $('#envPop').innerHTML =
      '<h4>基础工具</h4>' +
      tool('python3', 'python3') + tool('ffmpeg', 'ffmpeg') + tool('ffprobe', 'ffprobe') + tool('conda', 'conda') + tool('git', 'git') + tool('claude', 'claude') +
      '<h4>重 AI conda 环境</h4>' +
      (r.conda.available ? (r.knownList || []).map(envRow).join('') : '<div class="erow"><span class="no">未检测到 conda——重 AI 步骤(配音克隆/作曲/换脸)跑不起来</span></div>') +
      (r.conda.available && r.conda.envs && r.conda.envs.length ? `<div class="note">已装 conda 环境：${escapeHtml(r.conda.envs.join(', '))}</div>` : '') +
      (r.conda.available && !allKnown ? '<div class="note">缺的环境对应的重 AI 步骤本机跑不起来：配音可先用 macOS say 应急，出图前再换真实配音重跑。</div>' : '') +
      '<div class="acts"><button class="mini" id="envRescan">重新探测</button><button class="mini" id="envTermProbe">终端详细探测</button></div>';
    $('#envRescan').onclick = () => probeEnv();
    $('#envTermProbe').onclick = () => { runInTerminal('conda env list 2>/dev/null; python3 --version; ffmpeg -version 2>/dev/null | head -1', true); $('#envPop').classList.add('hidden'); };
  }

  $('#statusEnv').addEventListener('click', (e) => {
    e.stopPropagation();
    const pop = $('#envPop');
    if (pop.classList.contains('hidden')) { renderEnvPop(); pop.classList.remove('hidden'); }
    else pop.classList.add('hidden');
  });
  document.addEventListener('click', (e) => {
    if (!$('#envPop').classList.contains('hidden') && !e.target.closest('#envPop') && e.target.id !== 'statusEnv') $('#envPop').classList.add('hidden');
  });

  // ───────────────────────── 侧栏视图：资源管理器 / 全局搜索 / git ─────────────────────────
  function switchSidebar(name) {
    $('#viewExplorer').classList.toggle('hidden', name !== 'explorer');
    $('#viewSearch').classList.toggle('hidden', name !== 'search');
    $('#viewGit').classList.toggle('hidden', name !== 'git');
    $('#actExplorer').classList.toggle('on', name === 'explorer');
    $('#actSearch').classList.toggle('on', name === 'search');
    $('#actGit').classList.toggle('on', name === 'git');
    if (name === 'search') $('#searchInput').focus();
    if (name === 'git') refreshGit();
  }

  async function openFileAt(p, line) {
    await openFile(p);
    if (editor && line) { try { editor.revealLineInCenter(line); editor.setPosition({ lineNumber: line, column: 1 }); editor.focus(); } catch (_) {} }
  }

  async function runSearch() {
    const q = $('#searchInput').value.trim();
    const meta = $('#searchMeta'), list = $('#searchResults');
    if (!rootPath) { meta.textContent = '先打开文件夹'; list.innerHTML = ''; return; }
    if (!q) { meta.textContent = ''; list.innerHTML = ''; return; }
    meta.textContent = '搜索中…';
    const r = await api.search.run(rootPath, q);
    const res = r.results || [];
    meta.textContent = `${res.length}${res.length >= 400 ? '+' : ''} 条 · ${r.engine || ''}`;
    list.innerHTML = res.map((it, i) => {
      const rel = it.file.startsWith(rootPath) ? it.file.slice(rootPath.length + 1) : it.file;
      return `<div class="res" data-i="${i}"><div class="loc">${escapeHtml(rel)}:${it.line}</div><div class="tx">${escapeHtml(it.text)}</div></div>`;
    }).join('');
    [...list.querySelectorAll('.res')].forEach((el) => el.addEventListener('click', () => { const it = res[+el.dataset.i]; openFileAt(it.file, it.line); }));
  }

  async function refreshGit() {
    const list = $('#gitList');
    if (!rootPath) { $('#gitBranch').textContent = '先打开文件夹'; list.innerHTML = ''; return; }
    const r = await api.git.status(rootPath);
    if (!r.isRepo) { $('#gitBranch').textContent = '非 git 仓库'; list.innerHTML = ''; return; }
    $('#gitBranch').textContent = '⑂ ' + (r.branch || '');
    if (!r.files.length) { list.innerHTML = '<div class="side-sub">工作区干净</div>'; return; }
    list.innerHTML = r.files.map((f, i) => {
      const tone = f.status.includes('D') ? 'del' : (f.status.includes('A') || f.status.includes('?')) ? 'add' : 'mod';
      return `<div class="gitrow" data-i="${i}"><span class="st ${tone}">${escapeHtml(f.status)}</span><span class="fn">${escapeHtml(f.file)}</span></div>`;
    }).join('');
    [...list.querySelectorAll('.gitrow')].forEach((el) => el.addEventListener('click', () => {
      const f = r.files[+el.dataset.i];
      openFile(f.file.startsWith('/') ? f.file : (r.toplevel + '/' + f.file));
    }));
  }

  $('#actExplorer').addEventListener('click', () => switchSidebar('explorer'));
  $('#actSearch').addEventListener('click', () => switchSidebar('search'));
  $('#actGit').addEventListener('click', () => switchSidebar('git'));
  $('#searchInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') runSearch(); });
  $('#gitRefresh').addEventListener('click', refreshGit);
  $('#gitCommitBtn').addEventListener('click', () => {
    const msg = $('#gitMsg').value.trim();
    if (!msg || !rootPath) { flashSave('请填提交信息'); return; }
    runInTerminal(`git -C "${rootPath}" add -A && git -C "${rootPath}" commit -m ${JSON.stringify(msg)}`, true);
    $('#gitMsg').value = '';
  });
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'f' || e.key === 'F')) { e.preventDefault(); switchSidebar('search'); }
  });

  // ───────────────────────── boot ─────────────────────────
  $('#openBtn').addEventListener('click', async () => {
    const p = await api.openFolder();
    if (p) { await openRoot(p); startTerminal(); if (boardOpen) { await refreshWorkList(); if (boardWork) await generateBoard(); } }
  });
  $('#newTermBtn').addEventListener('click', () => startTerminal());
  window.addEventListener('resize', fitTerm);

  await initMonaco();
  initGutter();
  initVGutter();
  logPath = await api.log.path();
  api.onDeeplink((u) => openDeep(u)); // 看板深链 → app 内开深画布标签
  const init = await api.initFolder(); // electron . <folder> / INIT_FOLDER：启动即打开
  if (init) await openRoot(init);
  await startTerminal(); // cwd = 已打开的根（否则 HOME）
  probeEnv(); // 非阻塞：登录 shell 探测会花几百毫秒，就绪后更新状态栏
})();
