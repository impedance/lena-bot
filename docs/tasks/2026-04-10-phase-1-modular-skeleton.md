# Work Plan: Phase 1 - Extract Modular Skeleton Without Changing Behavior

## 0) Orientation
- Master index: [2026-04-10-search-providers-modularization-index.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-search-providers-modularization-index.md)
- This phase owns the structural refactor only. Do not add Tavily/Brave logic here.
- Current source of truth is [bot_maison_best_v2_export_safe.py](/home/spec/work/lena-bot/bot_maison_best_v2_export_safe.py).

## 1) Outcome
- Goal: split the monolithic script into a small package while keeping current Google-only behavior functionally equivalent.
- Success criteria:
  - New package layout exists and imports cleanly.
  - The orchestration path still reaches DB setup, search loop, CSV export, and Telegram send.
  - Existing constants and rules move out of the monolith without semantic drift.

## 2) Scope
- In scope:
  - Create the package directory and `__init__.py` files.
  - Extract config/constants, dataclasses, filters, DB helpers, URL helpers, and output helpers.
  - Leave provider logic Google-only for now, but isolate it so Phase 2 can extend it.
  - Add a thin top-level entrypoint.
- Out of scope:
  - New providers.
  - Query strategy changes.
  - Test additions beyond temporary compile/smoke checks needed during refactor.
- Assumptions / open questions:
  - Keep current file names and env var names unless a rename clearly simplifies the boundary and does not break runtime behavior.

## 3) Change surface + safety
- Entry points:
  - Current: [bot_maison_best_v2_export_safe.py](/home/spec/work/lena-bot/bot_maison_best_v2_export_safe.py)
  - New primary entrypoint: `main.py` or `lena_bot/run.py`
- Files/modules to create or update:
  - `lena_bot/__init__.py`
  - `lena_bot/config.py`
  - `lena_bot/models.py`
  - `lena_bot/filters/__init__.py`
  - `lena_bot/filters/criteria.py`
  - `lena_bot/storage/__init__.py`
  - `lena_bot/storage/db.py`
  - `lena_bot/utils/__init__.py`
  - `lena_bot/utils/url_tools.py`
  - `lena_bot/outputs/__init__.py`
  - `lena_bot/outputs/csv_export.py`
  - `lena_bot/outputs/telegram.py`
  - `lena_bot/providers/__init__.py`
  - `lena_bot/providers/google_cse.py`
  - `lena_bot/run.py`
  - `main.py`
  - optional compatibility wrapper in [bot_maison_best_v2_export_safe.py](/home/spec/work/lena-bot/bot_maison_best_v2_export_safe.py)
- Invariants/contracts to preserve:
  - `criteria_check()` decision order must remain identical.
  - `insert_listing()` still uses `INSERT OR IGNORE` by URL.
  - Telegram still sends only `STRICT` + `OK` items.
  - CSV column order remains business-compatible.
- Main risks + mitigation:
  - Risk: subtle copy/paste drift in regexes or word lists.
  - Mitigation: move these blocks verbatim before any cleanup.
  - Risk: circular imports after extraction.
  - Mitigation: centralize only pure dataclasses and config in shared modules.

## 4) Implementation steps
1. Create the package skeleton under `lena_bot/` with empty `__init__.py` files.
2. Move constant/env/config sections into `lena_bot/config.py`; expose them as module constants or a small config object.
3. Move `CriteriaResult` and any provider/result dataclasses into `lena_bot/models.py`.
4. Move URL and catalog helpers into `lena_bot/utils/url_tools.py` without changing signatures unless import cleanup requires it.
5. Move DB helpers into `lena_bot/storage/db.py` and keep the current schema unchanged.
6. Move CSV and Telegram helpers into `lena_bot/outputs/` modules.
7. Move Google search helpers and the current run loop pieces into `lena_bot/providers/google_cse.py` and `lena_bot/run.py`.
8. Replace the old monolith body with either:
   - a thin compatibility wrapper calling the new `run()`; or
   - a clear deprecation note plus import-forwarder if you intentionally retire direct execution.
9. Run compile checks after each extraction step rather than after the whole refactor.

## 5) Validation
- Fast gate:
  - `python3 -m py_compile bot_maison_best_v2_export_safe.py` -> expected: baseline passes before edits.
- Task-specific checks:
  - `find lena_bot -name '*.py' | sort` -> expected: package files exist.
  - `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py bot_maison_best_v2_export_safe.py` -> expected: pass.
  - `python3 main.py` with missing env vars -> expected: exits with a clear missing-credentials message, not a traceback.
- Pareto blackbox/contract tests:
  - None required in this phase if compile/smoke checks pass; Phase 3 will add durable tests.
- Rollback:
  - Revert newly created `lena_bot/` files and restore [bot_maison_best_v2_export_safe.py](/home/spec/work/lena-bot/bot_maison_best_v2_export_safe.py) to the pre-refactor state.
  - Rollback verification: `python3 -m py_compile bot_maison_best_v2_export_safe.py`.

## DOD
- The codebase has a small modular package with the same business logic.
- The runtime path is no longer trapped in one 800-line file.
- Phase 2 can add providers without reopening unrelated modules.

## Final verdict
Ready for implementation: yes
