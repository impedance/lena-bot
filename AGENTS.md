# AGENTS.md

## Purpose

This repository is a small Python bot that:

- builds search queries for real-estate providers;
- normalizes provider results;
- filters listings by business criteria;
- stores deduplicated rows in SQLite;
- sends `STRICT + OK` results to Telegram.

## Core Principle

Documentation is an index into the code, not a duplicate of the code.

That means:

- docs should point to entrypoints, modules, contracts, and invariants;
- docs should not retell implementation line-by-line;
- when docs and code diverge, code and tests are the source of truth;
- keep docs short and link readers to the exact files they need.

## Where To Look

- Entrypoint: [main.py](/home/spec/work/lena-bot/main.py)
- Main orchestration: [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py)
- Environment and query config: [lena_bot/config.py](/home/spec/work/lena-bot/lena_bot/config.py)
- Domain models: [lena_bot/models.py](/home/spec/work/lena-bot/lena_bot/models.py)
- Business filtering: [lena_bot/filters/criteria.py](/home/spec/work/lena-bot/lena_bot/filters/criteria.py)
- URL normalization and catalog heuristics: [lena_bot/utils/url_tools.py](/home/spec/work/lena-bot/lena_bot/utils/url_tools.py)
- Provider abstraction: [lena_bot/providers/base.py](/home/spec/work/lena-bot/lena_bot/providers/base.py)
- Provider implementations:
  - [lena_bot/providers/google_cse.py](/home/spec/work/lena-bot/lena_bot/providers/google_cse.py)
  - [lena_bot/providers/tavily.py](/home/spec/work/lena-bot/lena_bot/providers/tavily.py)
  - [lena_bot/providers/brave.py](/home/spec/work/lena-bot/lena_bot/providers/brave.py)
- Persistence: [lena_bot/storage/db.py](/home/spec/work/lena-bot/lena_bot/storage/db.py)
- Outputs:
  - [lena_bot/outputs/csv_export.py](/home/spec/work/lena-bot/lena_bot/outputs/csv_export.py)
  - [lena_bot/outputs/telegram.py](/home/spec/work/lena-bot/lena_bot/outputs/telegram.py)
- Current task plans: [docs/tasks](/home/spec/work/lena-bot/docs/tasks)
- Product intent: [prd.md](/home/spec/work/lena-bot/prd.md)

## Behavioral Invariants

- `criteria_check()` decision order is part of the contract.
- `STRICT` must remain stricter than `FALLBACK`.
- Only `STRICT + OK` rows are eligible for Telegram.
- `listings.url` is the dedupe key unless explicitly changed in a separate task.
- Missing provider credentials should disable providers cleanly.

## Testing Map

- Filtering contracts: [tests/test_criteria_blackbox.py](/home/spec/work/lena-bot/tests/test_criteria_blackbox.py)
- URL pipeline contracts: [tests/test_url_pipeline.py](/home/spec/work/lena-bot/tests/test_url_pipeline.py)
- Startup smoke: [tests/test_smoke_startup.py](/home/spec/work/lena-bot/tests/test_smoke_startup.py)
- Run orchestration contracts: [tests/test_run_contracts.py](/home/spec/work/lena-bot/tests/test_run_contracts.py)
- Provider normalization contracts: [tests/test_provider_normalization.py](/home/spec/work/lena-bot/tests/test_provider_normalization.py)

## Documentation Rules

- Prefer adding a short pointer in `docs/tasks/*.md` over writing long prose.
- When documenting a change, include:
  - user-visible goal;
  - touched modules;
  - invariants that must not regress;
  - validation commands.
- Do not create narrative docs that duplicate the logic in `run.py`, providers, filters, or URL helpers.
- If a concept is stable and important, encode it in tests or types before expanding docs.
