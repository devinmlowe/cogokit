"""COGOpro interactive terminal user interface (TUI).

Requires the ``textual`` package::

    pip install cogopro[tui]
"""

from __future__ import annotations


def run() -> None:
    """Launch the COGOpro TUI application."""
    try:
        from cogopro.tui.app import COGOProApp
    except ImportError as exc:
        raise SystemExit(
            "The TUI requires the 'textual' package.\n"
            "Install it with: pip install cogopro[tui]"
        ) from exc

    # Load config before creating the app so it can read units/theme/keybindings
    from cogopro.config import load_config

    load_config()

    app = COGOProApp()
    app.run()
