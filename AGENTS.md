# Repository Guidelines

## Project Structure & Module Organization
- `bots_fonctionnels/` contains the Python bot scripts (e.g., `bot_maison3.py`, `bot_maisonRabotaetV1.py`).
- `annonces_metropole_lille.sqlite` is the local SQLite database used to store seen listings.
- `export_csv.py` is a utility script for exporting data (see file for usage).
- Runtime CSV outputs are created in the repo root with names like `nouvelles_annonces_YYYY-MM-DD_HHMMSS.csv`.

## Build, Test, and Development Commands
This repository does not define a build system or test runner.
- Run a bot directly with Python:
  - `python bots_fonctionnels/bot_maison3.py`
  - `python bots_fonctionnels/bot_maisonRabotaetV1.py`
- Environment variables required at runtime:
  - `GOOGLE_API_KEY`, `GOOGLE_CSE_ID` for Google Custom Search.
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` for Telegram notifications.

## Coding Style & Naming Conventions
- Language: Python.
- Indentation: 4 spaces (consistent with current scripts).
- File naming: lowercase with underscores (e.g., `bot_maison3.py`).
- Prefer descriptive constant names for configuration (e.g., `DOMAINS`, `BUDGET`).
- No formatter or linter is configured in this repo; keep diffs minimal and consistent.

## Testing Guidelines
- No automated tests are present.
- When changing query logic or parsing, perform a manual dry run and validate:
  - No duplicate inserts in `annonces_metropole_lille.sqlite`.
  - CSV output structure and Telegram message formatting.

## Commit & Pull Request Guidelines
- There is no Git history yet, so no established commit-message convention.
- Suggested convention: short, imperative summaries (e.g., “Add price extraction to listing resolver”).
- PRs (if used) should include:
  - A brief summary of changes.
  - Any environment variables required to reproduce.
  - Sample output (CSV filename or Telegram message snippet).

## Security & Configuration Tips
- Do not hardcode API keys or chat IDs.
- Treat the SQLite DB and CSV outputs as local artifacts; avoid committing them if they contain sensitive data.

## Agent-Specific Instructions
- Always respond to the repository owner in Russian.
