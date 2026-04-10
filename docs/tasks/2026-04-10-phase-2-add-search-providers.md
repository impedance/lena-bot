# Work Plan: Phase 2 - Add Tavily and Brave Providers Behind a Shared Search Interface

## 0) Orientation
- Master index: [2026-04-10-search-providers-modularization-index.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-search-providers-modularization-index.md)
- Depends on: [2026-04-10-phase-1-modular-skeleton.md](/home/spec/work/lena-bot/docs/tasks/2026-04-10-phase-1-modular-skeleton.md)
- This phase owns provider abstraction and search result normalization.

## 1) Outcome
- Goal: support Google CSE plus two additional providers, `Tavily` and `Brave`, through one internal search contract.
- Success criteria:
  - Each provider returns a normalized list of internal search result objects.
  - The run loop can choose a provider sequence without branching business logic by provider.
  - Missing provider credentials disable only that provider, not the whole run.

## 2) Scope
- In scope:
  - Define provider contract and normalized search result shape.
  - Add Google, Tavily, and Brave provider modules.
  - Add provider selection/fallback logic in the run orchestrator.
  - Add provider-specific config/env vars.
- Out of scope:
  - Provider quality scoring or query optimization.
  - Running multiple providers in parallel.
  - Provider-specific result ranking beyond minimal normalization.
- Assumptions / open questions:
  - Use provider order as a config value, for example `google_cse,tavily,brave`.
  - The same business query string can be reused across providers initially, with only the provider request shape adapted.

## 3) Change surface + safety
- Entry points:
  - `lena_bot/run.py`
  - `lena_bot/providers/*.py`
- Files/modules to create or update:
  - `lena_bot/models.py`
  - `lena_bot/config.py`
  - `lena_bot/providers/base.py`
  - `lena_bot/providers/google_cse.py`
  - `lena_bot/providers/tavily.py`
  - `lena_bot/providers/brave.py`
  - `lena_bot/run.py`
- Invariants/contracts to preserve:
  - Downstream filtering consumes only normalized fields: `url`, `title`, `snippet`, `display_domain`, provider metadata.
  - Provider failures do not crash the whole run if at least one enabled provider remains usable.
  - Existing Google behavior stays available.
- Main risks + mitigation:
  - Risk: each provider returns different field names and pagination semantics.
  - Mitigation: define one `SearchResult` dataclass and per-provider adapters.
  - Risk: provider fallback duplicates the same result repeatedly.
  - Mitigation: normalize URL before DB insert and keep current dedupe path intact.
  - Risk: adding provider branches bloats the run loop again.
  - Mitigation: keep provider modules responsible for request/response handling; the orchestrator only iterates providers.

## 4) Implementation steps
1. Add a `SearchResult` dataclass to `lena_bot/models.py` with the minimum shared fields required by current filtering and persistence.
2. Create `lena_bot/providers/base.py` with a small provider interface, such as `search(query: str, start_index: int = 1) -> list[SearchResult]` and capability metadata if needed.
3. Refactor the existing Google code into that interface without changing its current pagination behavior.
4. Add `TAVILY_API_KEY` and Brave credentials/config entries to `lena_bot/config.py`.
5. Implement `lena_bot/providers/tavily.py`:
   - map internal query string to Tavily request body;
   - set `include_domains` where a site-group chunk can be translated directly;
   - normalize returned URL, title, content/snippet, and source domain.
6. Implement `lena_bot/providers/brave.py`:
   - map internal query string to Brave web search request;
   - normalize returned URL, title, description, and source domain;
   - keep pagination limited to the same conceptual first/second page flow as the current Google logic.
7. In `lena_bot/run.py`, add provider selection and ordered fallback:
   - read configured provider order;
   - skip providers with missing credentials;
   - keep current insert/filter/export flow provider-agnostic.
8. Add lightweight runtime logging per provider so future quota debugging can tell which provider returned new rows.

## 5) Validation
- Fast gate:
  - `python3 -m py_compile $(find lena_bot -name '*.py' | sort) main.py` -> expected: pass.
- Task-specific checks:
  - Run a local dry path with only Google credentials configured -> expected: same control flow as before.
  - Run a local dry path with Google disabled and one secondary provider configured -> expected: run continues and returns normalized rows without import/runtime errors.
  - Confirm DB inserts still populate `source_domain`, `query_group`, `query_level`, `criteria_status`, and URL fields.
- Pareto blackbox/contract tests:
  - Defer durable automated coverage to Phase 3, but keep provider response shaping simple enough to mock there.
- Rollback:
  - Revert only provider modules and config/run changes from this phase; keep Phase 1 modular skeleton intact.
  - Rollback verification: Google-only path still compiles and starts cleanly.

## DOD
- Three providers exist behind one shared contract.
- The orchestrator is provider-agnostic for filtering/persistence/output.
- Missing keys for Tavily or Brave do not break Google-only operation.

## Final verdict
Ready for implementation: yes
