# Work Plan: Phase 3 - Add Minimal Blackbox Tests and Smoke Coverage

## 0) Orientation
- Master index: [2026-04-10-search-providers-modularization-index.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-search-providers-modularization-index.md)
- Depends on:
  - [2026-04-10-phase-1-modular-skeleton.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-phase-1-modular-skeleton.md)
  - [2026-04-10-phase-2-add-search-providers.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-phase-2-add-search-providers.md)
- This phase owns only the smallest high-signal test set. Do not turn it into a broad test backlog.

## 1) Outcome
- Goal: protect the business-critical filtering contract and the new provider normalization boundary with a compact automated suite.
- Success criteria:
  - Criteria logic is covered by blackbox tests using only public inputs and outputs.
  - Provider normalization is covered with fixture-based tests, not live API calls.
  - A simple smoke check proves the entrypoint fails gracefully without credentials.

## 2) Scope
- In scope:
  - Add `pytest` tests for criteria behavior.
  - Add one provider normalization test module covering Google/Tavily/Brave adapters with mocked responses.
  - Add one smoke test or equivalent command-level check for startup behavior.
- Out of scope:
  - Live network tests.
  - Full DB integration suite.
  - Snapshot tests for Telegram message formatting.
- Assumptions / open questions:
  - If `pytest` is not yet in the environment, the phase may add a minimal test dependency note or `requirements-dev.txt`, but should avoid a large tooling migration.

## 3) Change surface + safety
- Entry points:
  - `lena_bot/filters/criteria.py`
  - `lena_bot/providers/*.py`
  - `main.py` or `lena_bot/run.py`
- Files/modules to create or update:
  - `tests/test_criteria_blackbox.py`
  - `tests/test_provider_normalization.py`
  - optional `tests/test_smoke_startup.py`
  - optional `tests/fixtures/*.json`
  - optional `requirements-dev.txt` or test dependency note if needed
- Invariants/contracts to preserve:
  - Criteria tests assert only the public contract: status and reason for a given input blob.
  - Provider tests assert only normalized output shape, not internal request plumbing beyond what is necessary.
  - Smoke checks must not hit the network.
- Main risks + mitigation:
  - Risk: tests become brittle against harmless refactors.
  - Mitigation: keep them blackbox and contract-level.
  - Risk: too few cases miss critical regressions.
  - Mitigation: choose cases that mirror the exclusion and `MAYBE_*` logic from the PRD.

## 4) Implementation steps
1. Add `tests/` and choose the smallest test runner setup that works in this repo.
2. Write `tests/test_criteria_blackbox.py` with a compact matrix covering at least:
   - `EXCLUDED/apartment`
   - `EXCLUDED/rental`
   - `EXCLUDED/city_disallowed`
   - `EXCLUDED/surface<90`
   - `EXCLUDED/bedrooms<3`
   - `MAYBE_CITY`
   - `MAYBE_SURFACE`
   - `MAYBE_BEDROOMS`
   - `MAYBE_TERRAIN`
   - `OK`
3. Write `tests/test_provider_normalization.py` using mocked JSON fixtures for Google, Tavily, and Brave to assert that each adapter returns the same `SearchResult` contract.
4. Add one no-network smoke test or command-level assertion that startup with missing credentials exits with a clear message rather than a traceback.
5. Keep the suite fast; if a test does not protect a contract boundary, drop it.

## 5) Validation
- Fast gate:
  - `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py $(find tests -name '*.py' | sort)` -> expected: pass.
- Task-specific checks:
  - `python3 -m pytest tests/test_criteria_blackbox.py -q` -> expected: pass.
  - `python3 -m pytest tests/test_provider_normalization.py -q` -> expected: pass.
  - `python3 -m pytest tests -q` -> expected: pass.
- Pareto blackbox/contract tests:
  - Criteria blackbox tests are mandatory because they protect the main business value across refactors.
  - Provider normalization tests are mandatory because all three providers must obey one shared contract.
- Rollback:
  - Revert only `tests/` and any test-only dependency files added in this phase.
  - Rollback verification: runtime modules still compile and the app starts as before.

## DOD
- The repo has a minimal but meaningful automated regression net.
- The highest-risk business rules are covered by blackbox tests.
- Provider adapters can be refactored later without losing output-shape protection.

## Final verdict
Ready for implementation: yes
