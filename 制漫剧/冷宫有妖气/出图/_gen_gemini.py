#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Gemini 图像模型（默认 nano banana = gemini-2.5-flash-image）直接打 REST API 生图存 PNG。
用法:  python3 _gen_gemini.py <输出PNG路径> <正向prompt> [参考图1 参考图2 ...]
key 读 ~/.gemini/.apikey（不打印）。模型可用环境变量 GEMINI_IMAGE_MODEL 覆盖。
"""
import sys, os, json, base64, urllib.request, urllib.error

KEY = open(os.path.expanduser("~/.gemini/.apikey")).read().strip()
MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
ASPECT = os.environ.get("GEMINI_ASPECT", "9:16")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"


def _post(body):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=180)), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()[:400]}"
    except Exception as e:
        return None, str(e)


def _parts_from(prompt, refs):
    parts = [{"text": prompt}]
    for r in refs:
        ext = os.path.splitext(r)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        data = base64.b64encode(open(r, "rb").read()).decode()
        parts.append({"inlineData": {"mimeType": mime, "data": data}})
    return parts


def _extract(d, out):
    for cand in d.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
                open(out, "wb").write(base64.b64decode(inline["data"]))
                return True
    return False


def gen(out, prompt, refs):
    base = {"contents": [{"parts": _parts_from(prompt, refs)}]}
    # ① 带 imageConfig 宽高比
    body = dict(base, generationConfig={"responseModalities": ["IMAGE"],
                                         "imageConfig": {"aspectRatio": ASPECT}})
    d, err = _post(body)
    if err and ("imageConfig" in err or "aspectRatio" in err or "Unknown name" in err):
        # ② 回退：去掉 imageConfig
        d, err = _post(dict(base, generationConfig={"responseModalities": ["IMAGE"]}))
    if err:
        print("FAIL", err); return False
    if _extract(d, out):
        print("OK", out); return True
    print("NO_IMAGE", json.dumps(d)[:300]); return False


if __name__ == "__main__":
    out, prompt = sys.argv[1], sys.argv[2]
    refs = sys.argv[3:]
    sys.exit(0 if gen(out, prompt, refs) else 1)
