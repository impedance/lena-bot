# Priority 2 - Runtime Cleanup

Master index: [2026-04-10-top5-quality-improvements.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-top5-quality-improvements.md)
Depends on: [2026-04-10-priority-1-tests-and-tooling.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-priority-1-tests-and-tooling.md)

## In scope

- Narrow broad exception handling in the highest-risk runtime paths.
- Replace runtime `print()` calls with `logging` in the main flow.

## Out of scope

- Structural refactor of `run.py` beyond small extraction needed to support cleanup
- Typing migration
- DB schema changes
- Provider behavior changes

## Files to update

- [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py)
- [lena_bot/utils/url_tools.py](/home/spec/work/lena-bot/lena_bot/utils/url_tools.py)
- [lena_bot/filters/criteria.py](/home/spec/work/lena-bot/lena_bot/filters/criteria.py)
- optionally [lena_bot/outputs/telegram.py](/home/spec/work/lena-bot/lena_bot/outputs/telegram.py)

## Required changes

1. Replace broad `except Exception` with narrower exception types where practical.
2. If a broad catch remains intentional, add a short comment explaining why and keep the fallback explicit.
3. Replace scattered runtime `print()` calls with module-level `logging`.
4. Preserve current operator-facing message meaning.
5. Keep logger setup minimal:
   - standard library only
   - no framework
   - no external dependency
6. Do not fix unrelated Ruff warnings in this PR.
   Stop condition:
   fix only `BLE`, relevant `B`, and `T20` findings in touched files.
7. Do not change:
   - provider request semantics
   - DB schema
   - the rule that only `STRICT + OK` rows go to Telegram

## Validation

- `ruff check lena_bot`
- `python3 -m pytest tests -q`
- `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py`

## Handoff notes for the next task

- Record the remaining complexity hotspots in [lena_bot/run.py](/home/spec/work/lena-bot/lena_bot/run.py).
- Do not start broad helper extraction in this PR unless required to make exception scopes clear.

## DOD

- High-risk broad exception sites are narrowed or explicitly documented.
- Runtime `print()` calls in the main flow are replaced with logging.
- Behavior remains unchanged from a user/operator perspective.
- Repo passes the listed validation commands.

## Final verdict

Ready for implementation: yes
