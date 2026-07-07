#!/usr/bin/env node
// Shared release guard for public demo bundles.
//
// It has two jobs:
// 1) omit local/private account material by path (.env, credentials, tokens, keys);
// 2) block packaging when a normal text file contains a secret-looking value.
//
// The path omission is intentionally conservative for demos. Content findings
// are fatal because they cannot be made safe by filename filtering.
const fs = require('fs');
const path = require('path');

const MAX_TEXT_SCAN_BYTES = 2 * 1024 * 1024;

const SKIP_DIR_NAMES = new Set([
  '.aws',
  '.azure',
  '.cache',
  '.claude',
  '.codex',
  '.config',
  '.continue',
  '.cursor',
  '.docker',
  '.git',
  '.gcloud',
  '.gnupg',
  '.hg',
  '.kube',
  '.mypy_cache',
  '.npm',
  '.pytest_cache',
  '.ssh',
  '.svn',
  '.venv',
  '__pycache__',
  '_voicecache',
  'dist',
  'env',
  'node_modules',
  'target',
  'venv',
]);

const RELEASE_OMIT_DIR_NAMES = new Set([
  '_clipcache',
  '_downloads',
  '_work',
  'image_qc',
  'local_sdxl_cache',
  'local_train',
  'lora',
  'lora_cloud_packages',
  'reference_enhanced',
  'video_qc',
  'video_raw_with_audio',
  'video_repair_backups',
  '废料',
  '候选',
]);

const SENSITIVE_EXACT_NAMES = new Set([
  '.env',
  '.envrc',
  '.netrc',
  '.npmrc',
  '.pypirc',
  'account',
  'accounts',
  'accounts.json',
  'auth',
  'auth.json',
  'client_secret.json',
  'cookie',
  'cookies',
  'cookies.json',
  'credential',
  'credentials',
  'credentials.json',
  'id_ed25519',
  'id_rsa',
  'login',
  'logins',
  'password',
  'passwords',
  'private_key',
  'private_key.pem',
  'secret',
  'secrets',
  'secrets.json',
  'service_account.json',
  'session',
  'sessions',
  'token',
  'tokens',
]);

const SENSITIVE_EXTENSIONS = new Set([
  '.jks',
  '.key',
  '.keystore',
  '.mobileprovision',
  '.p12',
  '.pem',
  '.pfx',
  '.provisionprofile',
]);

const MEDIA_EXTENSIONS = new Set([
  '.aac',
  '.avi',
  '.bin',
  '.bmp',
  '.dmg',
  '.exe',
  '.flac',
  '.gif',
  '.ico',
  '.jpg',
  '.jpeg',
  '.m4a',
  '.mov',
  '.mp3',
  '.mp4',
  '.ogg',
  '.otf',
  '.pdf',
  '.png',
  '.psd',
  '.safetensors',
  '.ttf',
  '.wav',
  '.webm',
  '.webp',
  '.zip',
]);

const SENSITIVE_SEGMENT_RE =
  /(^|[._ -])(api[_-]?key|apikey|auth|bearer|client[_-]?secret|cookie|credential|credentials|login|password|passwd|private[_-]?key|refresh[_-]?token|secret|secrets|session|token|tokens)([._ -]|$)/i;

const RELEASE_OMIT_FILE_RE = /\.prelimit-\d{8}[-_]\d{4}\.[^.]+$/i;

const SECRET_CONTENT_PATTERNS = [
  { name: 'private-key-block', re: /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/ },
  { name: 'openai-api-key', re: /\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b/ },
  { name: 'anthropic-api-key', re: /\bsk-ant-[A-Za-z0-9_-]{20,}\b/ },
  { name: 'github-token', re: /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b/ },
  { name: 'aws-access-key', re: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: 'google-api-key', re: /\bAIza[0-9A-Za-z_-]{30,}\b/ },
  { name: 'huggingface-token', re: /\bhf_[A-Za-z0-9]{20,}\b/ },
  { name: 'slack-token', re: /\bxox[baprs]-[0-9A-Za-z-]{20,}\b/ },
  {
    name: 'secret-assignment',
    re: /\b(api[_-]?key|apikey|authorization|bearer|client[_-]?secret|password|passwd|pwd|refresh[_-]?token|secret|session|token)\b\s*[:=]\s*['"]?[A-Za-z0-9_./+=:@%~,-]{12,}/i,
  },
];

function toPosix(p) {
  return p.split(path.sep).join('/');
}

function relativePath(root, target) {
  const rel = path.relative(path.resolve(root), path.resolve(target));
  return rel === '' ? '' : toPosix(rel);
}

function sensitivePathReason(src, root) {
  const rel = root ? relativePath(root, src) : toPosix(src);
  if (!rel || rel.startsWith('..')) return null;
  const parts = rel.split('/').filter(Boolean);
  for (const part of parts) {
    const lower = part.toLowerCase();
    if (RELEASE_OMIT_DIR_NAMES.has(part) || RELEASE_OMIT_DIR_NAMES.has(lower)) {
      return `generated release-omitted directory: ${part}`;
    }
    if (SKIP_DIR_NAMES.has(lower)) return `private/cache directory: ${part}`;
    if (SENSITIVE_EXACT_NAMES.has(lower)) return `sensitive name: ${part}`;
    if (/^\.env(\.|$)/i.test(part)) return `environment file: ${part}`;
    if (/^known_hosts(\.|$)/i.test(part)) return `ssh known_hosts file: ${part}`;
    if (/^license\.(key|pem|p12|pfx)$/i.test(part)) return `license key file: ${part}`;
    if (SENSITIVE_EXTENSIONS.has(path.extname(lower))) return `sensitive extension: ${part}`;
    if (SENSITIVE_SEGMENT_RE.test(part)) return `sensitive name segment: ${part}`;
  }
  const name = parts[parts.length - 1] || '';
  if (RELEASE_OMIT_FILE_RE.test(name)) return `generated release-omitted file: ${name}`;
  return null;
}

function shouldBundlePath(src, options = {}) {
  const root = typeof options === 'string' ? options : options.root;
  let st;
  try {
    st = fs.lstatSync(src);
  } catch (_e) {
    return false;
  }
  if (st.isSymbolicLink()) return false;
  return !sensitivePathReason(src, root || src);
}

function isLikelyText(buf) {
  if (buf.length === 0) return true;
  let nul = 0;
  const limit = Math.min(buf.length, 8192);
  for (let i = 0; i < limit; i += 1) {
    if (buf[i] === 0) nul += 1;
  }
  return nul === 0;
}

function scanFileForSecrets(file, root) {
  const ext = path.extname(file).toLowerCase();
  if (MEDIA_EXTENSIONS.has(ext)) return [];

  const st = fs.statSync(file);
  if (!st.isFile() || st.size === 0) return [];

  const fd = fs.openSync(file, 'r');
  try {
    const len = Math.min(st.size, MAX_TEXT_SCAN_BYTES);
    const buf = Buffer.alloc(len);
    fs.readSync(fd, buf, 0, len, 0);
    if (!isLikelyText(buf)) return [];

    const text = buf.toString('utf8');
    const findings = [];
    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      for (const pat of SECRET_CONTENT_PATTERNS) {
        pat.re.lastIndex = 0;
        if (pat.re.test(line)) {
          findings.push({
            type: 'secret_content',
            pattern: pat.name,
            path: relativePath(root, file),
            line: i + 1,
          });
        }
      }
    }
    return findings;
  } finally {
    fs.closeSync(fd);
  }
}

function scanTree(root, options = {}) {
  const resolvedRoot = path.resolve(root);
  const report = {
    root: resolvedRoot,
    blocked: [],
    omitted: [],
    scannedFiles: 0,
  };

  function walk(current) {
    let st;
    try {
      st = fs.lstatSync(current);
    } catch (e) {
      report.blocked.push({
        type: 'read_error',
        path: relativePath(resolvedRoot, current),
        message: e.message,
      });
      return;
    }

    if (st.isSymbolicLink()) {
      if (options.includeOmitted !== false) {
        report.omitted.push({
          type: 'omitted_path',
          path: relativePath(resolvedRoot, current),
          reason: 'symbolic link',
        });
      }
      return;
    }

    const reason = sensitivePathReason(current, resolvedRoot);
    if (reason) {
      if (options.includeOmitted !== false) {
        report.omitted.push({
          type: 'omitted_path',
          path: relativePath(resolvedRoot, current),
          reason,
        });
      }
      return;
    }

    if (st.isDirectory()) {
      for (const name of fs.readdirSync(current).sort()) {
        walk(path.join(current, name));
      }
      return;
    }

    if (st.isFile()) {
      report.scannedFiles += 1;
      report.blocked.push(...scanFileForSecrets(current, resolvedRoot));
    }
  }

  if (!fs.existsSync(resolvedRoot)) {
    report.blocked.push({
      type: 'missing_root',
      path: resolvedRoot,
      message: 'path does not exist',
    });
    return report;
  }
  walk(resolvedRoot);
  return report;
}

function formatReport(report) {
  const lines = [];
  if (report.blocked.length > 0) {
    lines.push(`[release-safety] BLOCKED: ${report.blocked.length} secret-like finding(s) under ${report.root}`);
    for (const f of report.blocked.slice(0, 50)) {
      if (f.type === 'secret_content') {
        lines.push(`  - ${f.path}:${f.line} (${f.pattern})`);
      } else {
        lines.push(`  - ${f.path || report.root} (${f.type}: ${f.message || 'blocked'})`);
      }
    }
    if (report.blocked.length > 50) lines.push(`  ... ${report.blocked.length - 50} more`);
  }

  if (report.omitted.length > 0) {
    lines.push(`[release-safety] omitted ${report.omitted.length} private/cache/generated path(s):`);
    for (const f of report.omitted.slice(0, 50)) {
      lines.push(`  - ${f.path || '.'} (${f.reason})`);
    }
    if (report.omitted.length > 50) lines.push(`  ... ${report.omitted.length - 50} more`);
  }

  if (report.blocked.length === 0) {
    lines.push(`[release-safety] OK: scanned ${report.scannedFiles} file(s) under ${report.root}`);
  }
  return lines.join('\n');
}

function assertClean(report) {
  if (report.blocked.length > 0) {
    const err = new Error(formatReport(report));
    err.report = report;
    throw err;
  }
}

function copyDirSafe(src, dst, options = {}) {
  const sourceRoot = path.resolve(src);
  const pre = scanTree(sourceRoot);
  assertClean(pre);

  fs.rmSync(dst, { recursive: true, force: true });
  fs.cpSync(sourceRoot, dst, {
    recursive: true,
    filter: (candidate) => shouldBundlePath(candidate, { root: sourceRoot }),
  });

  const post = scanTree(dst, { includeOmitted: false });
  assertClean(post);
  return { pre, post };
}

function usage() {
  console.error('Usage: node tools/release-safety/demo_safety.cjs scan <path> [--json]');
  console.error('   or: node tools/release-safety/demo_safety.cjs copy <src> <dst> [--json]');
}

function main(argv) {
  const [cmd, a, b] = argv;
  const json = argv.includes('--json');
  if (!cmd || !a || (cmd === 'copy' && !b)) {
    usage();
    process.exit(2);
  }

  try {
    if (cmd === 'scan') {
      const report = scanTree(a);
      if (json) console.log(JSON.stringify(report, null, 2));
      else console.log(formatReport(report));
      process.exit(report.blocked.length === 0 ? 0 : 1);
    }

    if (cmd === 'copy') {
      const result = copyDirSafe(a, b);
      if (json) console.log(JSON.stringify(result, null, 2));
      else {
        console.log(formatReport(result.pre));
        console.log(`[release-safety] copied safe demo tree: ${path.resolve(a)} -> ${path.resolve(b)}`);
      }
      process.exit(0);
    }

    usage();
    process.exit(2);
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main(process.argv.slice(2));
}

module.exports = {
  copyDirSafe,
  formatReport,
  scanTree,
  shouldBundlePath,
  sensitivePathReason,
};
