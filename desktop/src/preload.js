// Bridge a minimal, safe API to the renderer (contextIsolation on, nodeIntegration off).
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  openFolder: () => ipcRenderer.invoke('dialog:openFolder'),
  readDir: (p) => ipcRenderer.invoke('fs:readDir', p),
  readFile: (p) => ipcRenderer.invoke('fs:readFile', p),
  writeFile: (p, content) => ipcRenderer.invoke('fs:writeFile', p, content),
  vsPath: () => ipcRenderer.invoke('app:vsPath'),
  term: {
    create: (opts) => ipcRenderer.invoke('pty:create', opts),
    write: (id, data) => ipcRenderer.send('pty:input', id, data),
    resize: (id, cols, rows) => ipcRenderer.send('pty:resize', id, cols, rows),
    dispose: (id) => ipcRenderer.send('pty:dispose', id),
    onData: (id, cb) => {
      const ch = 'pty:data:' + id;
      const handler = (_e, d) => cb(d);
      ipcRenderer.on(ch, handler);
      return () => ipcRenderer.removeListener(ch, handler);
    },
    onExit: (id, cb) => {
      const ch = 'pty:exit:' + id;
      const handler = () => cb();
      ipcRenderer.on(ch, handler);
      return () => ipcRenderer.removeListener(ch, handler);
    },
  },
  skillsDir: (hint) => ipcRenderer.invoke('app:skillsDir', hint),
  initFolder: () => ipcRenderer.invoke('app:initFolder'),
  config: { setSkillsDir: () => ipcRenderer.invoke('config:setSkillsDir'), get: () => ipcRenderer.invoke('config:get') },
  env: { probe: () => ipcRenderer.invoke('env:probe') },
  log: { append: (entry) => ipcRenderer.invoke('log:append', entry), path: () => ipcRenderer.invoke('log:path') },
  search: { run: (root, query) => ipcRenderer.invoke('search:run', root, query) },
  git: { status: (root) => ipcRenderer.invoke('git:status', root) },
  onDeeplink: (cb) => {
    const handler = (_e, u) => cb(u);
    ipcRenderer.on('deeplink:open', handler);
    return () => ipcRenderer.removeListener('deeplink:open', handler);
  },
  board: {
    findWorks: (root) => ipcRenderer.invoke('board:findWorks', root),
    generate: (workRoot) => ipcRenderer.invoke('board:generate', workRoot),
    manifest: (workRoot) => ipcRenderer.invoke('board:manifest', workRoot),
    watch: (workRoot) => ipcRenderer.invoke('board:watch', workRoot),
    unwatch: (workRoot) => ipcRenderer.send('board:unwatch', workRoot),
    onChanged: (cb) => {
      const handler = (_e, wr) => cb(wr);
      ipcRenderer.on('board:changed', handler);
      return () => ipcRenderer.removeListener('board:changed', handler);
    },
  },
});
