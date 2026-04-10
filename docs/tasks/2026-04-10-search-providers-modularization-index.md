# Work Plan: Search Providers + Modularization + Minimal Tests (Index)

## 0) Orientation
- Repo context as of 2026-04-10: the working codebase is effectively a single production script, `bot_maison_best_v2_export_safe.py`, plus runtime artifacts (`annonces_metropole_lille.sqlite`, CSV export, `prd.md`).
- No repo-local `AGENTS.md`, `README.md`, or existing `docs/tasks/` plan template exists in the current worktree, so this index and the sibling phase files use the fallback planning contract.
- Dependency order:
  - Phase 1: [2026-04-10-phase-1-modular-skeleton.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-phase-1-modular-skeleton.md)
  - Phase 2: [2026-04-10-phase-2-add-search-providers.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-phase-2-add-search-providers.md)
  - Phase 3: [2026-04-10-phase-3-minimal-tests-and-smoke.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-phase-3-minimal-tests-and-smoke.md)

## 1) Outcome
- Goal: evolve the current single-file bot into a small modular codebase that supports Google CSE plus two additional search providers, while preserving current filtering behavior and adding a minimal high-signal test set.
- Success criteria:
  - The runtime entrypoint still produces the same core outputs: DB inserts, CSV export, Telegram send, and `STRICT` filtering behavior.
  - Search is provider-based rather than hardwired to Google CSE.
  - Two additional providers are added behind the same normalized interface.
  - Minimal blackbox tests cover filtering behavior and one provider-shape contract.
  - The new structure is simple enough that future provider additions do not require editing the main orchestration flow.

## 2) Scope
- In scope:
  - Modularize the current script into a small package layout.
  - Add two new providers: `tavily` and `brave`.
  - Preserve current Google CSE support.
  - Add the smallest useful automated checks.
- Out of scope:
  - Query optimization or quota strategy redesign.
  - New ranking logic or price extraction.
  - UI/admin panel work.
  - Schema redesign beyond what the provider integration strictly needs.
- Assumptions / open questions:
  - Assume `Tavily` and `Brave Search API` are the two additional providers.
  - Assume provider usage is sequential/fallback, not parallel fan-out in this task.
  - If credentials are missing in local env, implementation still must degrade cleanly and tests must not require live API calls.

## 3) Change surface + safety
- Entry points:
  - Current runtime entrypoint: [bot_maison_best_v2_export_safe.py](/home/spec/work/lena-bot/bot_maison_best_v2_export_safe.py)
  - New likely runtime entrypoint: `main.py` or `lena_bot/run.py`
- Files/modules expected after the work:
  - `lena_bot/config.py`
  - `lena_bot/models.py`
  - `lena_bot/filters/criteria.py`
  - `lena_bot/storage/db.py`
  - `lena_bot/utils/url_tools.py`
  - `lena_bot/providers/base.py`
  - `lena_bot/providers/google_cse.py`
  - `lena_bot/providers/tavily.py`
  - `lena_bot/providers/brave.py`
  - `lena_bot/outputs/csv_export.py`
  - `lena_bot/outputs/telegram.py`
  - `lena_bot/run.py`
  - `tests/test_criteria_blackbox.py`
  - `tests/test_provider_normalization.py`
  - optional `tests/test_run_smoke.py`
- Invariants/contracts to preserve:
  - Current `criteria_check()` outcome mapping must not drift silently.
  - `listings.url` remains the dedupe key unless a later task explicitly changes it.
  - Only `STRICT + OK` rows are sent to Telegram.
  - CSV output keeps the current business-relevant columns.
- Main risks + mitigation:
  - Risk: refactor breaks runtime behavior.
  - Mitigation: move code with thin wrappers first, then switch imports, then add provider abstraction.
  - Risk: provider result shapes differ.
  - Mitigation: normalize to one internal `SearchResult` dataclass before filtering.
  - Risk: live API tests become flaky.
  - Mitigation: use fixture responses and mock HTTP for provider tests.

## 4) Implementation steps
1. Execute Phase 1 to create the package skeleton and move current logic with behavior parity.
2. Execute Phase 2 to add `Tavily` and `Brave` providers behind a shared normalized contract.
3. Execute Phase 3 to add minimal blackbox and provider normalization tests plus a no-network smoke check.
4. After all phases, run the final smoke command against the new entrypoint with missing credentials handled predictably.

## 5) Validation
- Fast gate:
  - `python3 -m py_compile bot_maison_best_v2_export_safe.py` -> expected: current baseline script is syntactically valid before starting.
- Task-specific checks:
  - After refactor, `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py` -> expected: pass.
  - After tests land, `python3 -m pytest tests -q` -> expected: pass.
- Pareto blackbox/contract tests:
  - Blackbox criteria tests protect the main business behavior cheaper than broad unit-by-unit tests.
  - Provider normalization tests protect the new abstraction boundary with minimal mocking.
- Rollback:
  - If a phase destabilizes the codebase, revert only the files listed in that phase plan and keep the runtime baseline script untouched until the new entrypoint is proven.
  - Rollback verification: `python3 -m py_compile bot_maison_best_v2_export_safe.py`.

## DOD
- Phase files are individually implementable by different agents without hidden dependencies.
- The modular code path is the primary path; the old single-file script is either kept as a thin compatibility wrapper or retired intentionally.
- Google, Tavily, and Brave all map into one internal result shape.
- Minimal tests cover criteria behavior and provider contracts.

## Final verdict
Ready for implementation: yes
