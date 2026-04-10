# -*- coding: utf-8 -*-
"""
Compatibility entrypoint.

The implementation was moved to the `lena_bot` package.
This file is intentionally kept as a thin wrapper to preserve
the historical execution path:

    python3 bot_maison_best_v2_export_safe.py
"""

from lena_bot.run import run


if __name__ == "__main__":
    run()
