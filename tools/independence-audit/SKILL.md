# independence-audit

Repo maintenance tool for checking that each skill series and top-level standalone skill remains independently distributable.

Use when changing:

- series dispatch docs such as `AGENTS.md`, `README.md`, or `skills/README.md`
- any `skills/<series>/_lib/` module
- scripts that reference another series
- executable files inside `skills/<standalone-skill>/`
- optional handoff contracts between series

Run:

```bash
python3 tools/independence-audit/scripts/check_independence.py               # strict-docs by default
python3 tools/independence-audit/scripts/check_independence.py --lenient-docs # code-level only (escape hatch)
python3 tools/independence-audit/scripts/check_novel_n2d_zero_coupling.py
```

Rules:

- `ad`, `mv`, `n2d`, `novel`, and `song` must not import or path-load another series' implementation.
- `skills/common` and active `common/*.py` references are forbidden. Per-series vendored `_lib` modules are the boundary.
- A top-level standalone skill may describe ideas learned from a series, but its `.py` and `.sh` files must not import, path-load, or invoke any series implementation.
- **Cross-series prose inside a per-series doc fails by default** (strict-docs); a `skills/<line>/**.md` must not name another line, its root label, or its skills. Use `--lenient-docs` to drop only this prose gate (code-level independence still enforced).
- Cross-series interaction is allowed only as optional file/data handoff, and must remain absence-safe.
- novel and n2d are stricter: no handoff contract, source export, source watch, shared ledger, or cross-route wording is allowed.
- Known handoffs outside novel/n2d include song to mv media input.
