# Quality Improvements Index

> Goal: improve reliability and maintainability of the bot with the smallest changes that materially reduce regression risk.
>
> Date: 2026-04-10

## Purpose

This file is the master index for the quality-improvement workstream.

Do not implement from this file directly.
Implement from the priority files below, in order, one file per PR.

## Source of Truth

- Runtime entrypoint: [main.py](/home/spec/work/lena-bot/main.py)
- Main orchestration: [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py)
- Filtering rules: [lena_bot/filters/criteria.py](/home/spec/work/lena-bot/lena_bot/filters/criteria.py)
- URL heuristics: [lena_bot/utils/url_tools.py](/home/spec/work/lena-bot/lena_bot/utils/url_tools.py)
- DB boundary: [lena_bot/storage/db.py](/home/spec/work/lena-bot/lena_bot/storage/db.py)
- Tests:
  - [tests/test_criteria_blackbox.py](/home/spec/work/lena-bot/tests/test_criteria_blackbox.py)
  - [tests/test_url_pipeline.py](/home/spec/work/lena-bot/tests/test_url_pipeline.py)
  - [tests/test_smoke_startup.py](/home/spec/work/lena-bot/tests/test_smoke_startup.py)
  - [tests/test_run_contracts.py](/home/spec/work/lena-bot/tests/test_run_contracts.py)

## Execution Order

1. [Priority 1 - Tests and Tooling](/home/spec/work/lena-bot/docs/tasks/2026-04-10-priority-1-tests-and-tooling.md)
2. [Priority 2 - Runtime Cleanup](/home/spec/work/lena-bot/docs/tasks/2026-04-10-priority-2-runtime-cleanup.md)
3. [Priority 3 - Run Refactor and Typing](/home/spec/work/lena-bot/docs/tasks/2026-04-10-priority-3-run-refactor-and-typing.md)

## Cross-Phase Invariants

- `criteria_check()` decision order must not drift silently.
- `STRICT` must remain stricter than `FALLBACK`.
- Only `STRICT + OK` rows are eligible for Telegram.
- `listings.url` remains the dedupe key unless explicitly changed in a separate task.
- Missing provider credentials must disable providers cleanly.
- No phase should introduce live-network tests.

## PR Rule

- One priority file = one PR.
- Do not start the next file until the previous one is merged or explicitly approved to overlap.

## DOD for the Whole Workstream

- Core filtering behavior is protected by automated tests.
- URL heuristics have targeted regression coverage.
- Startup failure behavior is tested without network calls.
- High-risk silent-failure paths are narrowed or explicitly documented.
- Runtime output uses structured logging in the main flow.
- `run.py` is easier to maintain without a disruptive rewrite.
- Typing exists where it reduces real mistakes, not as a checkbox exercise.

## Final verdict

Ready for implementation: yes
