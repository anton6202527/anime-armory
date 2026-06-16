#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_novel.py — 把用户拖进来的小说文件/链接纳管到 `写小说/<书名>/`。

目标：
  - 自动推断书名，建立作品根；
  - 本地 txt/md/docx 统一抽取成 `原作.txt`；
  - URL 只抓公版来源，或用户显式声明有权使用的通用来源；
  - 目标已存在时可提示：取消 / 新建版本 / 覆盖 / 使用现有。

用法：
    python3 skills/novel/scripts/import_novel.py "<路径或URL>"
    python3 skills/novel/scripts/import_novel.py "<路径或URL>" --on-exists new-version
    python3 skills/novel/scripts/import_novel.py "<路径或URL>" --on-exists overwrite --force
"""
import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import date
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
SKILLS_DIR = os.path.dirname(SKILL_DIR)
REPO_ROOT = os.path.dirname(SKILLS_DIR)

def load_script_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_contract = load_script_module(
    "_novel_craft_contract",
    os.path.join(SKILLS_DIR, "novel-craft", "scripts", "contract.py"),
)
_derive_common = load_script_module(
    "_novel_craft_derive_common",
    os.path.join(SKILLS_DIR, "novel-craft", "scripts", "derive_common.py"),
)
fetch_novel = load_script_module(
    "_novel_fetch_fetch_novel",
    os.path.join(SKILLS_DIR, "novel-fetch", "scripts", "fetch_novel.py"),
)

base_meta = _contract.base_meta
parse_outputs = _contract.parse_outputs
rights_metadata = _contract.rights_metadata
write_settings = _derive_common.write_settings


TEXT_EXTS = {".txt", ".md"}
DOCX_EXTS = {".docx"}
IMPORT_EXTS = TEXT_EXTS | DOCX_EXTS
DIRECT_URL_EXTS = TEXT_EXTS | DOCX_EXTS
GENERIC_TITLE_STEMS = {
    "", "book", "novel", "story", "text", "document", "download",
    "原作", "小说", "正文", "未命名", "untitled",
}
TITLE_SUFFIX_RE = re.compile(
    r"([_\-\s]*(全本|全集|完本|完结|精校|校对版|小说|正文|txt|docx|md))+$",
    re.I,
)


class ImportErrorWithCode(RuntimeError):
    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def clean_input(value):
    return (value or "").strip().strip("\"'")


def is_http_url(value):
    return urlparse(value).scheme in {"http", "https"}


def is_file_url(value):
    return urlparse(value).scheme == "file"


def local_path_from_input(value):
    value = clean_input(value)
    if is_file_url(value):
        return unquote(urlparse(value).path)
    return os.path.abspath(os.path.expanduser(value))


def strip_known_suffixes(stem):
    current = stem
    while True:
        nxt = TITLE_SUFFIX_RE.sub("", current).strip(" ._-")
        if nxt == current:
            return nxt
        current = nxt


def sanitize_title(raw):
    raw = html.unescape(unquote(str(raw or ""))).strip()
    raw = raw.strip("\"'“”‘’")
    raw = re.sub(r"[?#].*$", "", raw)
    raw = raw.replace("\\", "/")
    if "/" in raw:
        raw = raw.rstrip("/").rsplit("/", 1)[-1]
    stem, ext = os.path.splitext(raw)
    if ext.lower() in IMPORT_EXTS | {".html", ".htm", ".epub"}:
        raw = stem
    raw = strip_known_suffixes(raw)
    raw = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "-", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" ._-")
    return raw[:80] or "未命名小说"


def is_generic_title(title):
    normalized = re.sub(r"[\s_\-]+", "", (title or "").lower())
    if normalized in GENERIC_TITLE_STEMS:
        return True
    return bool(re.fullmatch(r"\d+", normalized or ""))


def title_from_url_path(url):
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path:
        return "未命名小说"
    return sanitize_title(path.rsplit("/", 1)[-1])


def plausible_content_title(line):
    line = line.strip().lstrip("#").strip()
    if not line or len(line) > 40:
        return None
    if re.match(r"^第\s*[0-9零一二三四五六七八九十百千两]+\s*[章回节卷]", line):
        return None
    if re.search(r"(作者|更新时间|目录|简介|版权|copyright)", line, re.I):
        return None
    if len(re.findall(r"[，。！？,.!?;；:：]", line)) > 2:
        return None
    return sanitize_title(line)


def infer_title_from_text(text, fallback, *, prefer_content=False):
    fallback = sanitize_title(fallback)
    use_content = prefer_content or is_generic_title(fallback)
    if not use_content:
        return fallback
    for raw in (text or "").splitlines()[:30]:
        candidate = plausible_content_title(raw)
        if candidate:
            return candidate
    return fallback


def extract_html_title(text):
    if not text:
        return None
    m = re.search(
        r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"']([^\"']+)[\"']",
        text,
        re.I,
    )
    if not m:
        m = re.search(
            r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+property=[\"']og:title[\"']",
            text,
            re.I,
        )
    if not m:
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if not m:
        return None
    title = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip()
    parts = re.split(r"\s+[|｜]\s+|\s+[-—–]\s+", title, maxsplit=1)
    if len(parts) == 2 and re.search(
        r"(Project Gutenberg|Wikisource|维基文库|小说|阅读|书库|book|site)",
        parts[1],
        re.I,
    ):
        title = parts[0]
    return sanitize_title(title)


def decode_bytes(raw, preferred=None):
    encodings = []
    if preferred:
        encodings.append(preferred)
    encodings.extend(["utf-8-sig", "utf-8", "gb18030", "big5"])
    seen = set()
    for enc in encodings:
        if enc in seen:
            continue
        seen.add(enc)
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def read_local_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    text, encoding = decode_bytes(raw)
    return text, encoding, hashlib.sha256(raw).hexdigest()


def docx_to_text(path):
    with zipfile.ZipFile(path) as zf:
        data = zf.read("word/document.xml")
    root = ET.fromstring(data)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for para in root.iter(ns + "p"):
        chunks = []
        for node in para.iter():
            if node.tag == ns + "t" and node.text:
                chunks.append(node.text)
            elif node.tag == ns + "tab":
                chunks.append("\t")
            elif node.tag == ns + "br":
                chunks.append("\n")
        line = "".join(chunks).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs).strip() + "\n"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_directory_source(path):
    if not os.path.isdir(path):
        return path
    candidates = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        depth = os.path.relpath(root, path).count(os.sep)
        if depth > 1:
            dirs[:] = []
            continue
        for name in files:
            if name.startswith("."):
                continue
            if os.path.splitext(name)[1].lower() in IMPORT_EXTS:
                candidates.append(os.path.join(root, name))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ImportErrorWithCode(f"目录里没有发现可导入的 .txt/.md/.docx：{path}")
    shown = "\n".join(f"  - {p}" for p in candidates[:10])
    raise ImportErrorWithCode(
        "目录里发现多个候选小说文件，请指定其中一个：\n" + shown,
        code=3,
    )


def http_get_text(url, cache=None):
    cache = cache if cache is not None else {}
    if url in cache:
        return cache[url]
    req = Request(url, headers={"User-Agent": "novel-import/1.0"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read()
        preferred = resp.headers.get_content_charset()
    text, _ = decode_bytes(raw, preferred=preferred)
    cache[url] = text
    return text


def http_get_bytes(url):
    req = Request(url, headers={"User-Agent": "novel-import/1.0"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read()
        preferred = resp.headers.get_content_charset()
        content_type = resp.headers.get("Content-Type", "")
    return raw, preferred, content_type


def fetch_public_or_authorized(url, source_mode, *, i_have_rights):
    if fetch_novel.is_paywalled(url):
        raise ImportErrorWithCode(
            "拒抓：该 URL 命中已知付费墙/反爬来源；请改用公版来源或本地合法文件。"
        )
    source_type = source_mode if source_mode != "auto" else fetch_novel.detect_source(url)
    if source_type == "generic" and not i_have_rights:
        raise ImportErrorWithCode(
            "通用 URL 需要先声明你有权使用：确认后加 --i-have-rights，"
            "或换 Project Gutenberg / Wikisource 等公版来源。",
            code=3,
        )

    cache = {}
    title_candidate = None
    try:
        title_candidate = extract_html_title(http_get_text(url, cache=cache))
    except Exception:
        title_candidate = None

    if source_type == "gutenberg":
        chapters = fetch_novel.fetch_gutenberg(url, get=lambda u: http_get_text(u, cache=cache))
    elif source_type == "wikisource":
        chapters = fetch_novel.fetch_wikisource(url, get=lambda u: http_get_text(u, cache=cache))
    elif source_type == "generic":
        chapters = fetch_novel.fetch_generic(url, get=lambda u: http_get_text(u, cache=cache))
    else:
        raise ImportErrorWithCode(f"未知 URL source：{source_type}")

    chapters = [c for c in chapters if c.get("body")]
    if not chapters:
        raise ImportErrorWithCode("未抓到任何正文。请检查 URL 是否为章节目录页。")
    text = fetch_novel.assemble_text(chapters)
    return {
        "text": text,
        "encoding": "network",
        "source_type": source_type,
        "source_display": url,
        "source_url": url,
        "source_path": "",
        "title_candidate": title_candidate,
        "chapters": len(chapters),
        "original_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "docx_bytes": None,
        "original_filename": "",
    }


def collect_url_payload(url, args):
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()
    fetch_source = getattr(args, "fetch_source", "auto")
    source_type = fetch_source if fetch_source != "auto" else fetch_novel.detect_source(url)
    if source_type == "generic" and not args.i_have_rights:
        raise ImportErrorWithCode(
            "通用 URL 需要先声明你有权使用：确认后加 --i-have-rights。",
            code=3,
        )
    if fetch_novel.is_paywalled(url):
        raise ImportErrorWithCode(
            "拒抓：该 URL 命中已知付费墙/反爬来源；请改用公版来源或本地合法文件。"
        )

    if ext in DIRECT_URL_EXTS:
        raw, preferred, content_type = http_get_bytes(url)
        if ext in DOCX_EXTS:
            tmp_name = "_import_download.docx"
            text = ""
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
                    f.write(raw)
                    tmp_name = f.name
                text = docx_to_text(tmp_name)
            finally:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
            docx_bytes = raw
            encoding = "docx"
            direct_type = "url_docx"
        else:
            text, encoding = decode_bytes(raw, preferred=preferred)
            docx_bytes = None
            direct_type = "url_txt" if ext == ".txt" else "url_markdown"
        return {
            "text": text,
            "encoding": encoding,
            "source_type": direct_type,
            "source_display": url,
            "source_url": url,
            "source_path": "",
            "title_candidate": extract_html_title(text) if "html" in content_type else None,
            "chapters": 0,
            "original_sha256": hashlib.sha256(raw).hexdigest(),
            "docx_bytes": docx_bytes,
            "original_filename": sanitize_title(parsed.path.rsplit("/", 1)[-1]),
        }

    return fetch_public_or_authorized(url, fetch_source, i_have_rights=args.i_have_rights)


def collect_local_payload(source):
    path = resolve_directory_source(local_path_from_input(source))
    if not os.path.exists(path):
        raise ImportErrorWithCode(f"找不到文件：{path}")
    ext = os.path.splitext(path)[1].lower()
    if ext not in IMPORT_EXTS:
        raise ImportErrorWithCode(f"暂只支持 .txt/.md/.docx：{path}")
    if ext in DOCX_EXTS:
        text = docx_to_text(path)
        encoding = "docx"
        source_type = "local_docx"
        with open(path, "rb") as f:
            docx_bytes = f.read()
        source_hash = hashlib.sha256(docx_bytes).hexdigest()
    else:
        text, encoding, source_hash = read_local_text(path)
        source_type = "local_txt" if ext == ".txt" else "local_markdown"
        docx_bytes = None
    return {
        "text": text,
        "encoding": encoding,
        "source_type": source_type,
        "source_display": path,
        "source_url": "",
        "source_path": os.path.abspath(path),
        "title_candidate": None,
        "chapters": 0,
        "original_sha256": source_hash,
        "docx_bytes": docx_bytes,
        "original_filename": os.path.basename(path),
    }


def collect_payload(source, args):
    source = clean_input(source)
    if is_http_url(source):
        return collect_url_payload(source, args)
    return collect_local_payload(source)


def next_available_root(base_root):
    if not os.path.exists(base_root):
        return base_root
    i = 2
    while True:
        candidate = f"{base_root}-{i}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


def prompt_existing(root, title, input_func=input):
    print(f"[exists] 作品已存在：{root}", file=sys.stderr)
    print("请选择：", file=sys.stderr)
    print(f"  n = 新建版本（如 {title}-2）", file=sys.stderr)
    print("  o = 覆盖旧目录", file=sys.stderr)
    print("  u = 使用现有目录，不改文件", file=sys.stderr)
    print("  a = 取消", file=sys.stderr)
    while True:
        answer = input_func("选择 [n/o/u/a]: ").strip().lower()
        if answer in {"n", "new"}:
            return "new-version"
        if answer in {"o", "overwrite"}:
            confirm = input_func("确认覆盖请输入 覆盖: ").strip()
            if confirm == "覆盖":
                return "overwrite"
            print("未确认覆盖。", file=sys.stderr)
            continue
        if answer in {"u", "use"}:
            return "use-existing"
        if answer in {"a", "abort", ""}:
            return "abort"
        print("请输入 n/o/u/a。", file=sys.stderr)


def resolve_target_root(title, out_root, on_exists, *, force=False, input_func=input):
    root = os.path.abspath(os.path.join(out_root, sanitize_title(title)))
    if not os.path.exists(root):
        return root, "create"

    choice = on_exists
    if choice == "ask":
        if not sys.stdin.isatty():
            raise ImportErrorWithCode(
                f"作品已存在：{root}\n"
                "非交互环境不会自动覆盖。请显式选择："
                " --on-exists new-version / --on-exists use-existing / "
                "--on-exists overwrite --force",
                code=3,
            )
        choice = prompt_existing(root, title, input_func=input_func)

    if choice == "abort":
        raise ImportErrorWithCode(f"作品已存在，已取消：{root}", code=3)
    if choice == "new-version":
        return next_available_root(root), "new-version"
    if choice == "use-existing":
        return root, "use-existing"
    if choice == "overwrite":
        if not force and not sys.stdin.isatty():
            raise ImportErrorWithCode(
                "覆盖已有作品必须加 --force，避免脚本在非交互环境误删。", code=3
            )
        return root, "overwrite"
    raise ImportErrorWithCode(f"未知 --on-exists：{on_exists}")


def rights_status_for(source_type, i_have_rights):
    if source_type in {"gutenberg", "wikisource"}:
        return "public-domain"
    if i_have_rights:
        return "user-declared"
    return "unknown"


def write_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write((text or "").rstrip() + "\n")


def write_json(path, payload):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def maybe_write_docx(path, text, prov):
    try:
        fetch_novel.write_docx(path, text, prov)
        return True
    except ImportError:
        return False


def build_manifest(title, payload, rights_status, *, rights_declared,
                   rights_jurisdiction=None, distribution_regions=None):
    chars = len((payload["text"] or "").replace("\n", ""))
    rights = rights_metadata(
        rights_status,
        source_type=payload["source_type"],
        source_url=payload.get("source_url") or payload.get("source_display", ""),
        rights_declared=rights_declared,
        rights_jurisdiction=rights_jurisdiction,
        distribution_regions=distribution_regions,
    )
    return {
        "schema_version": 1,
        "kind": "novel_source_manifest",
        "title": title,
        "source_url": payload.get("source_url", ""),
        "source_path": payload.get("source_path", ""),
        "source_type": payload["source_type"],
        "imported_at": date.today().isoformat(),
        "chapters": payload.get("chapters", 0),
        "chars": chars,
        **rights,
        "requires_user_rights": rights.get("requires_user_rights") or payload["source_type"] == "generic",
        "encoding": payload.get("encoding", ""),
        "original_filename": payload.get("original_filename", ""),
        "original_sha256": payload.get("original_sha256", ""),
    }


def build_progress(title, payload, rights_status):
    rights_mark = "x" if rights_status in {"public-domain", "user-declared", "original"} else " "
    return f"""# 进度 — 《{title}》（导入源书）

## 当前状态
- [x] 项目骨架
- [x] 原作导入（`原作.txt` + `小说/source_manifest.json`）
- [{rights_mark}] 权利复核（当前：{rights_status}）
- [ ] 选择下一步：评分 / 审稿 / 改写 / 精简 / 续写 / 漫剧改编

## 导入记录
- 来源：{payload.get('source_display', '')}
- 类型：{payload.get('source_type', '')}
- 字数：{len((payload.get('text') or '').replace(chr(10), ''))}

> 这是源书纳管项目，不是原创/派生写作阶段。后续一旦进入 rewrite/condense/continue/n2d，
> 对应 skill 会建立自己的阶段契约或生产进度。
"""


def write_project(root, title, payload, outputs, rights_status, *, replace=False,
                  rights_declared=False, rights_jurisdiction=None, distribution_regions=None):
    target = root
    tmp = None
    if replace and os.path.exists(root):
        tmp = f"{root}.tmp-import-{os.getpid()}"
        if os.path.exists(tmp):
            shutil.rmtree(tmp)
        target = tmp

    for sub in ("小说", "素材", "设定", "章节", "审稿", "导出", "合规"):
        os.makedirs(os.path.join(target, sub), exist_ok=True)

    text = payload["text"]
    prov = {
        "source_url": payload.get("source_url") or payload.get("source_path") or payload.get("source_display", ""),
        "fetched": date.today().isoformat(),
        "chapters": payload.get("chapters", 0),
        "chars": len((text or "").replace("\n", "")),
        "copyright": rights_status,
    }

    write_text(os.path.join(target, "原作.txt"), text)
    write_text(os.path.join(target, "小说", f"{title}.txt"), text)
    if payload.get("docx_bytes"):
        with open(os.path.join(target, "小说", f"{title}.docx"), "wb") as f:
            f.write(payload["docx_bytes"])
    else:
        maybe_write_docx(os.path.join(target, "小说", f"{title}.docx"), text, prov)

    manifest = build_manifest(
        title,
        payload,
        rights_status,
        rights_declared=rights_declared,
        rights_jurisdiction=rights_jurisdiction,
        distribution_regions=distribution_regions,
    )
    write_json(os.path.join(target, "小说", "source_manifest.json"), manifest)

    meta = base_meta("import", outputs=outputs, rights_status=rights_status, title=title)
    meta.update({key: manifest[key] for key in (
        "rights_status",
        "rights_jurisdiction",
        "rights_basis",
        "source_license_url",
        "rights_covered_regions",
        "distribution_regions",
        "requires_user_rights",
        "requires_region_rights_review",
        "rights_declared",
    )})
    meta.update({
        "source_title": title,
        "source": "原作.txt",
        "source_novel": payload.get("source_display", ""),
        "source_type": payload["source_type"],
        "rights_declared_at": date.today().isoformat() if rights_declared else None,
        "imported_at": date.today().isoformat(),
        "text_chars": manifest["chars"],
        "source_manifest": "小说/source_manifest.json",
        "original_sha256": payload.get("original_sha256", ""),
    })
    write_json(os.path.join(target, "_meta.json"), meta)

    write_settings(target, {
        "目标平台": "跨平台（导入源书；后续再选）",
        "权利来源": rights_status,
        "权利辖区": manifest.get("rights_jurisdiction", ""),
        "发行地区": ",".join(manifest.get("distribution_regions") or []) or "未定",
        "输出格式": ",".join(outputs),
        "导入来源": payload.get("source_display", ""),
        "源类型": payload["source_type"],
        "AI使用披露": "未使用AI文本（仅导入源书；后续改写/续写另行披露）",
        "下一步": "评分 / 审稿 / 改写 / 精简 / 续写 / 漫剧改编",
    }, note="拖入小说后自动建档；同项目后续沉默沿用这些选择点。")
    write_text(os.path.join(target, "_进度.md"), build_progress(title, payload, rights_status))

    if tmp:
        shutil.rmtree(root)
        os.replace(tmp, root)


def infer_title(source, payload, args):
    if args.title:
        return sanitize_title(args.title)
    if payload.get("title_candidate") and not is_generic_title(payload["title_candidate"]):
        fallback = payload["title_candidate"]
    elif is_http_url(source):
        fallback = title_from_url_path(source)
    else:
        fallback = os.path.splitext(payload.get("original_filename") or os.path.basename(source))[0]
    return infer_title_from_text(
        payload.get("text", ""),
        fallback,
        prefer_content=args.prefer_content_title,
    )


def import_novel(source, args, *, input_func=input):
    payload = collect_payload(source, args)
    title = infer_title(clean_input(source), payload, args)
    outputs = parse_outputs(args.outputs)
    out_root = os.path.abspath(args.out_root)
    target_root, action = resolve_target_root(
        title,
        out_root,
        args.on_exists,
        force=args.force,
        input_func=input_func,
    )

    rights_status = rights_status_for(payload["source_type"], args.i_have_rights)
    rights_declared = bool(args.i_have_rights)

    result = {
        "title": title,
        "target_root": target_root,
        "action": action,
        "source_type": payload["source_type"],
        "rights_status": rights_status,
        "chars": len((payload.get("text") or "").replace("\n", "")),
    }
    if args.dry_run or action == "use-existing":
        return result

    write_project(
        target_root,
        title,
        payload,
        outputs,
        rights_status,
        replace=(action == "overwrite"),
        rights_declared=rights_declared,
        rights_jurisdiction=args.rights_jurisdiction,
        distribution_regions=args.distribution_regions,
    )
    return result


def build_arg_parser():
    ap = argparse.ArgumentParser(description="拖入小说路径/URL → 写小说/<书名>/ 源书项目")
    ap.add_argument("source", help="本地 .txt/.md/.docx、目录、file://、http(s) URL")
    ap.add_argument("--title", default=None, help="手动指定书名；缺省从文件名/URL/正文首行推断")
    ap.add_argument("--out-root", default="写小说", help="作品根父目录；缺省 写小说")
    ap.add_argument("--on-exists", default="ask",
                    choices=["ask", "abort", "new-version", "overwrite", "use-existing"],
                    help="同名作品已存在时的处理方式；缺省交互询问")
    ap.add_argument("--force", action="store_true", help="允许非交互 overwrite")
    ap.add_argument("--i-have-rights", action="store_true",
                    help="声明你对本地/通用 URL 源文本有使用权；会写入 _meta/_设置")
    ap.add_argument("--rights-jurisdiction", default=None,
                    help="公版/授权依据适用辖区，如 US/CN/GLOBAL；缺省按来源推断")
    ap.add_argument("--distribution-regions", default=None,
                    help="计划发行/交付地区，逗号分隔，如 CN,US；公版跨区时必须复核")
    ap.add_argument("--source", dest="fetch_source", default="auto",
                    choices=["auto", "gutenberg", "wikisource", "generic"],
                    help="URL 抓取来源类型；缺省 auto")
    ap.add_argument("--outputs", default="txt,docx,outline")
    ap.add_argument("--prefer-content-title", action="store_true",
                    help="即使文件名可用，也优先尝试正文首行作为书名")
    ap.add_argument("--dry-run", action="store_true", help="只输出计划，不写文件")
    return ap


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        result = import_novel(args.source, args)
    except ValueError as e:
        print(f"[err] {e}", file=sys.stderr)
        return 2
    except ImportErrorWithCode as e:
        print(f"[err] {e}", file=sys.stderr)
        return e.code

    print(f"[ok] {result['action']}: {result['title']}")
    print(f"     作品根：{result['target_root']}")
    print(f"     来源类型：{result['source_type']} / 权利：{result['rights_status']}")
    print(f"     字数：{result['chars']}")
    if result["action"] == "use-existing":
        print("     未改文件。")
    else:
        print("     已写：原作.txt、小说/source_manifest.json、_meta.json、_设置.md、_进度.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
