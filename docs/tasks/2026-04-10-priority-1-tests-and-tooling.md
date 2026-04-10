# Priority 1 - Tests and Tooling

Master index: [2026-04-10-top5-quality-improvements.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-top5-quality-improvements.md)

## In scope

- Expand the existing regression tests where coverage is still thin.
- Add minimal `pyproject.toml` and targeted Ruff config.
- Add `.env.example`.
- Expand `.gitignore` for local Python artifacts and generated exports.

## Out of scope

- Refactoring `run.py`
- Logging migration
- Exception-scope cleanup
- Typing beyond what is needed to keep the repo green

## Files to update

- [tests/test_criteria_blackbox.py](/home/spec/work/lena-bot/tests/test_criteria_blackbox.py)
- [tests/test_url_pipeline.py](/home/spec/work/lena-bot/tests/test_url_pipeline.py)
- [tests/test_smoke_startup.py](/home/spec/work/lena-bot/tests/test_smoke_startup.py)
- `pyproject.toml`
- `.env.example`
- `.gitignore`

## Required changes

1. Keep tests blackbox and contract-oriented.
2. Add one `FALLBACK` test proving city logic is relaxed relative to `STRICT`.
3. Extend URL helper coverage only for:
   - `domain_of()`
   - `city_presence()`
   - `is_known_direct_url()`
4. Keep startup smoke local and deterministic.
5. Do not add live-network tests for `resolve_direct_url_soft()` or `expand_catalog_page()`.
6. Add minimal `pyproject.toml` with:
   - runtime dependency: `requests`
   - dev dependencies: `pytest`, `ruff`
7. Add Ruff config with this targeted rule family set:
   - `E`
   - `F`
   - `B`
   - `BLE`
   - `C90`
   - `PLR`
   - `T20`
   - `SIM`
   - `UP`
   - `RUF`
8. Do not fix every Ruff finding in this task.
   Stop condition:
   add config, confirm the repo runs, and leave cleanup findings for Priority 2 and Priority 3.
9. Add `.env.example` covering variables from [config.py](/home/spec/work/lena-bot/lena_bot/config.py).
10. Expand `.gitignore` for:
   - `__pycache__/`
   - `*.pyc`
   - `.pytest_cache/`
   - `.ruff_cache/`
   - local CSV exports

## Validation

- `python3 -m pytest tests/test_criteria_blackbox.py tests/test_url_pipeline.py tests/test_smoke_startup.py -q`
- `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py bot_maison_best_v2_export_safe.py`
- `ruff check .`

## Handoff notes for the next task

- Record the main Ruff findings by category only.
- Do not start cleanup work in this PR.

## DOD

- Missing regression cases are added.
- `pyproject.toml` exists and Ruff runs.
- `.env.example` exists.
- `.gitignore` covers local Python/tooling noise.
- Repo still passes the listed validation commands.

## Final verdict

Ready for implementation: yes
