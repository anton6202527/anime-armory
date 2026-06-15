# independence-audit

Repo maintenance tool for checking that each skill series remains independently distributable.

Use when changing:

- series dispatch docs such as `AGENTS.md`, `README.md`, or `skills/README.md`
- any `skills/<series>/_lib/` module
- scripts that reference another series
- optional handoff contracts between series

Run:

```bash
python3 tools/independence-audit/scripts/check_independence.py
```

Rules:

- `ad`, `mv`, `n2d`, `novel`, and `song` must not import or path-load another series' implementation.
- `skills/common` and active `common/*.py` references are forbidden. Per-series vendored `_lib` modules are the boundary.
- Cross-series interaction is allowed only as optional file/data handoff, and must remain absence-safe.
- Known handoffs are novel to n2d source export, song to mv media input, and n2d-feedback genre ledger read by novel-score.
