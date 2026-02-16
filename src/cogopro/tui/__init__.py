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
    app = COGOProApp()
    app.run()
