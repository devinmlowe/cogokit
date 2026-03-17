"""cogokit interactive terminal user interface (TUI).

Requires the ``textual`` package::

    pip install cogokit[tui]
"""

from __future__ import annotations


def run() -> None:
    """Launch the cogokit TUI application."""
    try:
        from cogokit.tui.app import CogoKitApp
    except ImportError as exc:
        raise SystemExit(
            "The TUI requires the 'textual' package.\n"
            "Install it with: pip install cogokit[tui]"
        ) from exc

    # Load config before creating the app so it can read units/theme/keybindings
    from cogokit.config import load_config

    load_config()

    app = CogoKitApp()
    app.run()
