import importlib

import pytest

run_module = importlib.import_module("lena_bot.run")


def test_startup_without_telegram_credentials_exits_cleanly(monkeypatch):
    monkeypatch.setattr(run_module, "TG_TOKEN", "")
    monkeypatch.setattr(run_module, "TG_CHAT", "")

    with pytest.raises(SystemExit) as exc:
        run_module.run()

    assert "TELEGRAM_BOT_TOKEN" in str(exc.value)
    assert "TELEGRAM_CHAT_ID" in str(exc.value)
