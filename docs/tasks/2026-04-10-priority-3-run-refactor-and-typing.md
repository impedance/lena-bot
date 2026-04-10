# Priority 3 - Run Refactor and Typing

Master index: [2026-04-10-top5-quality-improvements.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-top5-quality-improvements.md)
Depends on: [2026-04-10-priority-2-runtime-cleanup.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-priority-2-runtime-cleanup.md)

## In scope

- Extract a few high-value helpers from [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py).
- Add selective typing on stable boundaries.
- Reduce stringly-typed domain values where payoff is highest.

## Out of scope

- Large `pipeline.py` rewrite
- Full repo-wide strict typing
- Provider redesign
- Ranking/query redesign
- DB schema changes

## Files to update

- [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py)
- [lena_bot/models.py](/home/spec/work/lena-bot/lena_bot/models.py)
- [lena_bot/storage/db.py](/home/spec/work/lena-bot/lena_bot/storage/db.py)
- [lena_bot/outputs/csv_export.py](/home/spec/work/lena-bot/lena_bot/outputs/csv_export.py)
- [lena_bot/outputs/telegram.py](/home/spec/work/lena-bot/lena_bot/outputs/telegram.py)
- optionally new `lena_bot/types.py`

## Required changes

1. Do not create a large `pipeline.py`.
2. Extract only small helpers with obvious boundaries, for example:
   - provider enablement/building
   - Telegram message formatting
   - listing row construction
   - one small result-handling helper if it can be extracted without broad control-flow churn
3. Preserve current control flow and data model.
4. Add missing parameter and return annotations to pure and stable functions first.
5. If introducing `ListingRow`, keep it limited to the boundary shared by:
   - `run.py`
   - `db.py`
   - `csv_export.py`
   - Telegram formatting
6. Replace stringly-typed domain values with `Enum` or `Literal` where payoff is highest:
   - criteria statuses
   - query levels
   - optionally URL statuses if they are widely shared
7. Do not require `mypy --strict`.
8. Do not change:
   - DB schema
   - provider request semantics
   - the rule that only `STRICT + OK` rows go to Telegram
9. Do not widen scope into general cleanup.
   Stop condition:
   finish once `run.py` is easier to navigate and the key domain strings are typed.

## Validation

- `python3 -m pytest tests -q`
- `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py`
- optional: `mypy lena_bot` only if config was intentionally added in this PR

## DOD

- `run.py` has a few clear helper boundaries.
- Shared row and domain status boundaries are better typed.
- No behavior regressions are introduced.
- Repo passes the listed validation commands.

## Final verdict

Ready for implementation: yes
