# Quality Improvements Plan - ROI First

> Goal: improve reliability and maintainability of the bot with the smallest changes that materially reduce regression risk.
>
> Date: 2026-04-10

## 0. Orientation

- Current repo state is already post-modularization:
  - runtime entrypoint: [main.py](/home/spec/work/lena-bot/main.py)
  - compatibility wrapper: [bot_maison_best_v2_export_safe.py](/home/spec/work/lena-bot/bot_maison_best_v2_export_safe.py)
  - main orchestration: [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py)
  - business-critical filtering: [lena_bot/filters/criteria.py](/home/spec/work/lena-bot/lena_bot/filters/criteria.py)
  - URL heuristics: [lena_bot/utils/url_tools.py](/home/spec/work/lena-bot/lena_bot/utils/url_tools.py)
- This plan replaces the earlier generic quality wishlist with a repo-specific sequence based on actual risk.
- Main principle: protect business behavior first, then simplify change surface, then add selective typing where it pays off.

## 1. Outcome

- Goal:
  - reduce the chance of silently shipping bad listing decisions;
  - make small future changes in `run.py` safer;
  - improve local developer ergonomics without a large tooling migration.
- Success criteria:
  - the repo has a small automated regression net for filtering and URL heuristics;
  - the runtime startup path is checked without network calls;
  - `run.py` is slightly less monolithic in the highest-friction areas;
  - basic repo hygiene exists for local work;
  - typing is introduced only on the most error-prone boundaries, not as a repo-wide strict mandate.

## 2. Scope

### In scope

- Add minimal project metadata and local tooling:
  - `pyproject.toml`
  - `.env.example`
  - `.gitignore` cleanup
- Add the smallest useful automated tests:
  - blackbox tests for `criteria_check()`
  - targeted tests for `url_tools`
  - one no-network startup smoke test
- Extract a few high-value helpers out of `lena_bot/run.py` without changing behavior.
- Add selective type hints to stable and high-value boundaries only.

### Out of scope

- Full repo-wide `mypy --strict`
- Large `pipeline.py` rewrite in one pass
- Full DB integration suite
- Live API tests against Google, Tavily, or Brave
- Query strategy redesign
- Ranking/prioritization redesign

## 3. Why This Order

- The highest product risk is wrong inclusion/exclusion logic, not missing static types.
- The most business-critical code is:
  - [criteria.py](/home/spec/work/lena-bot/lena_bot/filters/criteria.py)
  - [url_tools.py](/home/spec/work/lena-bot/lena_bot/utils/url_tools.py)
  - [run.py](/home/spec/work/lena-bot/lena_bot/run.py)
- `mypy` would help around dict shapes and signatures, but it will not protect:
  - ordering of exclusion checks;
  - `STRICT` vs `FALLBACK` behavior;
  - only sending `STRICT + OK` rows to Telegram;
  - URL normalization and catalog-expansion heuristics.
- Because of that, tests and a small structural cleanup have better ROI than strict typing as the first major investment.

## 4. Priority Plan

| Priority | Change | Why now | Effort | Risk |
|---|---|---|---|---|
| 1 | Repo hygiene + `pyproject.toml` | fast unblocker for all next steps | 20-40 min | Low |
| 2 | Blackbox tests for filtering | protects core business value | 45-90 min | Low |
| 3 | Targeted tests for URL heuristics | protects brittle helper logic | 45-90 min | Low |
| 4 | No-network startup smoke test | protects operator experience | 20-40 min | Low |
| 5 | Small `run.py` extraction | lowers future refactor cost | 1.5-3 h | Medium |
| 6 | Selective typing on boundaries | catches dict/signature mistakes cheaply | 1-2 h | Low |
| 7 | Optional broader typing / provider tests | only after 1-6 are green | Later | Low |

## 5. Phase Details

### Phase 1 - Repo Hygiene and Tooling

#### Outcome

- Local development becomes reproducible and less noisy.
- Baseline linting catches the most common real bugs (bare except, undefined names, complexity hotspots).

#### Files to create or update

- `pyproject.toml`
- `.env.example`
- `.gitignore`

#### Required changes

1. Add minimal `pyproject.toml` with:
   - project name/version
   - runtime dependency: `requests`
   - optional dev dependencies: `pytest`, `ruff`
2. Add Ruff configuration with targeted rule set:
   ```toml
   [tool.ruff]
   line-length = 99
   target-version = "py312"

   [tool.ruff.lint]
   select = [
       "E", "F",       # pycodestyle + pyflakes (syntax, undefined names, unused imports)
       "B",            # bugbear — bare except, mutable defaults, silent exception swallowing
       "SIM",          # simplify — redundant if/else, duplicated conditions
       "I",            # isort — import ordering
       "UP",           # pyupgrade — modern Python patterns
       "RUF",          # ruff-specific — duplicate strings, unused variables
       "C901",         # complexity — flag overly complex functions
       "PLR0911",      # too many returns
       "PLR0912",      # too many branches
       "PLR0915",      # too many statements
   ]
   ignore = [
       "E501",         # line-length handled by formatter
   ]
   ```
   Rationale for rule selection (based on current codebase audit):
   - `B` catches ~10 occurrences of bare `except Exception: pass` that silently swallow errors in production (url_tools, criteria, run.py)
   - `C901` + `PLR*` flag `run.py` (~250 lines, 6+ nesting levels) as the primary refactoring candidate
   - `E` + `F` are the baseline — undefined names, unused imports, broken syntax
   - `SIM` catches redundant patterns in criteria parsing logic
   - `RUF` catches duplicated `User-Agent` strings and dead code
   - Do NOT add `D` (docstrings), `ANN` (type checking), `SLF` (private access), or `ARG` (unused arguments) in this phase — too noisy, defer to later phases
   - Do not add `mypy` config in this phase.
   - Do not add pre-commit in this phase unless already required by the repo.
3. Expand `.gitignore` beyond the current `.env`-only state:
   - `__pycache__/`
   - `*.pyc`
   - `.pytest_cache/`
   - `.ruff_cache/`
   - local CSV exports
4. Add `.env.example` covering current env variables used in [config.py](/home/spec/work/lena-bot/lena_bot/config.py).

#### Validation

- `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py bot_maison_best_v2_export_safe.py`
- `ruff check .`
- Review `ruff check` output for `B` (bare except) and `C901` (complexity) hotspots — these are intentional signals for future refactoring, not blockers for Phase 1

### Phase 2 - Blackbox Tests for Filtering

#### Outcome

- The main business decision logic is protected against accidental drift.

#### Files to create

- `tests/test_criteria_blackbox.py`

#### Required changes

1. Add tests only against public input/output of `criteria_check(url, title, snippet, level)`.
2. Cover the minimum high-signal matrix:
   - `EXCLUDED / exclude_keyword`
   - `EXCLUDED / rental`
   - `EXCLUDED / apartment`
   - `EXCLUDED / not_house`
   - `EXCLUDED / city_disallowed`
   - `EXCLUDED / surface<90`
   - `EXCLUDED / bedrooms<3`
   - `MAYBE_CITY`
   - `MAYBE_SURFACE`
   - `MAYBE_BEDROOMS`
   - `MAYBE_TERRAIN`
   - `OK`
   - one `FALLBACK` case proving city logic is relaxed relative to `STRICT`
3. Assert both status and reason where the reason is part of the contract.

#### Validation

- `python3 -m pytest tests/test_criteria_blackbox.py -q`

### Phase 3 - Targeted Tests for URL Heuristics

#### Outcome

- The most brittle helper logic is protected without testing every helper exhaustively.

#### Files to create

- `tests/test_url_tools.py`

#### Required changes

1. Cover only the highest-risk helpers from [url_tools.py](/home/spec/work/lena-bot/lena_bot/utils/url_tools.py):
   - `normalize_url()`
   - `domain_of()`
   - `city_presence()`
   - `is_known_direct_url()`
   - `is_catalog_url()`
   - `extract_direct_url_from_query()`
2. Do not add live-network tests for:
   - `resolve_direct_url_soft()`
   - `expand_catalog_page()`
3. Keep tests fixture-light and deterministic.

#### Validation

- `python3 -m pytest tests/test_url_tools.py -q`

### Phase 4 - No-Network Startup Smoke

#### Outcome

- Startup failures remain operator-friendly and deterministic.

#### Files to create

- `tests/test_startup_smoke.py`

#### Required changes

1. Add one smoke test for `main.py` or `lena_bot.run.run`.
2. Verify missing Telegram configuration fails with a clear `SystemExit` message.
3. Do not perform any real network requests in this test.
4. If necessary, monkeypatch provider enablement so the test stays local and stable.

#### Validation

- `python3 -m pytest tests/test_startup_smoke.py -q`

### Phase 5 - Small Extraction from `run.py`

#### Outcome

- The highest-friction orchestration file becomes easier to read and change, without a big rewrite.

#### Files to update

- [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py)
- optionally `lena_bot/outputs/telegram.py`

#### Required changes

1. Do not create a large `pipeline.py` in this phase.
2. Extract only small helpers with obvious boundaries, for example:
   - `build_enabled_providers()`
   - Telegram message formatting
   - row-construction helper for inserted listings
3. Preserve current control flow and data model.
4. Do not change:
   - DB schema
   - provider request semantics
   - the rule that only `STRICT + OK` rows go to Telegram
5. Keep nested search/catalog logic in place if extracting it would require broad behavioral changes.

#### Validation

- `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py`
- `python3 -m pytest tests -q`

### Phase 6 - Selective Typing, Not Strict Typing

#### Outcome

- The code gets type help where it is most useful, without paying the cost of a full strict migration.

#### Files to update

- [lena_bot/models.py](/home/spec/work/lena-bot/lena_bot/models.py)
- [lena_bot/storage/db.py](/home/spec/work/lena-bot/lena_bot/storage/db.py)
- [lena_bot/outputs/csv_export.py](/home/spec/work/lena-bot/lena_bot/outputs/csv_export.py)
- [lena_bot/outputs/telegram.py](/home/spec/work/lena-bot/lena_bot/outputs/telegram.py)
- optionally new `lena_bot/types.py`

#### Required changes

1. Add missing parameter and return annotations to pure and stable functions first.
2. If introducing `ListingRow`, use it only on the boundary shared by:
   - `run.py`
   - `db.py`
   - `csv_export.py`
   - Telegram formatting
3. Keep `CriteriaResult` and `SearchResult` strongly typed.
4. Do not require `mypy --strict`.
5. If adding `mypy`, use a non-strict baseline and only after tests already exist.

#### Validation

- `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py`
- optional: `mypy lena_bot` only if config was added intentionally in this phase

## 6. Invariants to Protect

- `criteria_check()` decision order must not drift silently.
- `STRICT` remains stricter than `FALLBACK`.
- `listings.url` remains the dedupe key unless changed in a separate task.
- Only `STRICT + OK` rows are eligible for Telegram sending.
- CSV output must remain business-usable.
- Missing provider credentials must disable providers cleanly, not crash imports.

## 7. Risks and Mitigation

- Risk: tests lock in accidental current behavior.
  - Mitigation: only assert behavior that matches the PRD and operator expectations.
- Risk: small `run.py` extraction accidentally changes orchestration.
  - Mitigation: add tests first and keep extraction narrow.
- Risk: typing effort expands into a full migration.
  - Mitigation: explicitly stop at boundary typing unless a later task approves more.

## 8. Fast Wins

- The best quick wins for this repo are:
  - `.gitignore` cleanup
  - `.env.example`
  - `pyproject.toml` with `ruff` and `pytest`
  - blackbox tests for `criteria_check`
- These deliver more practical value right now than a repo-wide strict typing pass.

## 9. Suggested Execution Order

1. Phase 1: hygiene and tooling
2. Phase 2: filtering tests
3. Phase 3: URL helper tests
4. Phase 4: startup smoke test
5. Phase 5: small `run.py` extraction
6. Phase 6: selective typing

## Rollback

- If Phase 1 causes tooling noise or conflicts:
  - revert only `pyproject.toml`, `.env.example`, and `.gitignore` changes from this task.
- If Phases 2-4 cause instability:
  - revert only `tests/` files added by this task.
- If Phase 5 changes behavior unexpectedly:
  - revert only the helper extractions in [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py) and any paired formatting helper changes.
- If Phase 6 expands too far or creates typing churn:
  - revert only the selective typing files or annotations added in that phase.
- Rollback verification:
  - `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py bot_maison_best_v2_export_safe.py`

## DOD

- The repo has a minimal reproducible local dev setup.
- Core filtering behavior is protected by automated tests.
- URL heuristics have targeted regression coverage.
- Startup failure behavior is tested without network calls.
- `run.py` is somewhat easier to maintain without a disruptive rewrite.
- Typing exists where it reduces real mistakes, not as a checkbox exercise.

## Final verdict

Ready for implementation: yes
