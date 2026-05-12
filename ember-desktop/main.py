"""Entry point for the Ember Mug desktop app."""
import sys

from PyQt6.QtWidgets import QApplication

from mug_backend import MugBackend
from settings_manager import SettingsManager
from full_window import FullWindow
from toolbar_window import ToolbarWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Ember Mug")
    app.setQuitOnLastWindowClosed(False)  # Toolbar shouldn't kill the app

    settings = SettingsManager()
    backend = MugBackend(settings.mug_address)

    full_win = FullWindow(backend, settings)
    toolbar_win = ToolbarWindow(backend, settings)

    # ── Toggle between full and toolbar views ────────────────────────────────
    def show_toolbar():
        full_win.hide()
        toolbar_win.show()

    def show_full():
        toolbar_win.hide()
        full_win.show()

    full_win.switch_to_toolbar.connect(show_toolbar)
    toolbar_win.show_full.connect(show_full)

    # ── Clean shutdown ───────────────────────────────────────────────────────
    def on_quit():
        backend.stop()

    app.aboutToQuit.connect(on_quit)

    # ── Start ────────────────────────────────────────────────────────────────
    backend.start()

    if settings.auto_connect and settings.mug_address:
        backend.connect_to_mug(settings.mug_address)

    full_win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
