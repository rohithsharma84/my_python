"""Minimal frameless floating toolbar — always on top, draggable."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QWidget,
)

import icons as ic
from settings_manager import SettingsManager


_BG = "#1a1a2e"
_BORDER = "#3a3a55"
_TEXT = "#e2e8f0"
_MUTED = "#888aaa"
_ACCENT = "#00AAFF"
_GREEN_BG = "#1a4d1a"
_GREEN_FG = "#44dd44"
_ORANGE_BG = "#4d2000"
_ORANGE_FG = "#ff8833"
_BLUE_BG = "#001a4d"
_BLUE_FG = "#4488ff"
_DIVIDER = "#3a3a55"

_ICON_SIZE = 24

_TOOL_STYLE = f"""
QWidget {{
    background-color: {_BG};
    color: {_TEXT};
    font-family: 'Segoe UI', Arial;
    font-size: 12px;
}}
QPushButton {{
    background: transparent;
    color: {_TEXT};
    border: none;
    padding: 0 4px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton:hover {{ color: {_ACCENT}; }}
QLabel {{ background: transparent; color: {_TEXT}; }}
"""


def _c_to_display(celsius: float, unit: str) -> float:
    return celsius * 9 / 5 + 32 if unit == "F" else celsius


def _display_to_c(display: float, unit: str) -> float:
    return (display - 32) * 5 / 9 if unit == "F" else display


def _fmt_temp(celsius: float, unit: str) -> str:
    return f"{_c_to_display(celsius, unit):.0f}°{unit}"


class _Divider(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(1)
        self.setStyleSheet(f"background-color: {_DIVIDER};")
        self.setMinimumHeight(20)


class _IconLabel(QLabel):
    """Label that shows a QPixmap icon."""
    def __init__(self, size: int = _ICON_SIZE):
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)

    def set_icon(self, pixmap):
        self.setPixmap(
            pixmap.scaled(self._size, self._size,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
        )


class ToolbarWindow(QWidget):
    show_full = pyqtSignal()

    def __init__(self, backend, settings: SettingsManager):
        super().__init__()
        self._backend = backend
        self._settings = settings
        self._drag_pos: QPoint | None = None
        self._locked = False
        self._target_temp_c: float = 57.0
        self._last_data = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(_TOOL_STYLE)

        self._build_ui()
        self._connect_signals()
        self._restore_position()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(6)

        def _sep():
            layout.addWidget(_Divider())

        # Bluetooth status
        self._bt_icon = _IconLabel()
        layout.addWidget(self._bt_icon)
        self._bt_icon.set_icon(ic.bluetooth_icon(_ICON_SIZE, False))

        _sep()

        # Battery
        self._bat_icon = _IconLabel()
        layout.addWidget(self._bat_icon)
        self._bat_label = QLabel("—")
        layout.addWidget(self._bat_label)
        self._charge_label = QLabel("")
        self._charge_label.setStyleSheet("color: #FFD700; font-size: 11px;")
        layout.addWidget(self._charge_label)

        _sep()

        # Target temperature with +/- controls
        self._tgt_icon = _IconLabel()
        self._tgt_icon.set_icon(ic.temp_icon(_ICON_SIZE))
        layout.addWidget(self._tgt_icon)

        self._tgt_minus = QPushButton("−")
        self._tgt_minus.setFixedWidth(22)
        self._tgt_minus.setEnabled(False)
        layout.addWidget(self._tgt_minus)

        self._tgt_label = QLabel("—")
        self._tgt_label.setStyleSheet("padding: 0 4px; font-weight: bold;")
        layout.addWidget(self._tgt_label)

        self._tgt_plus = QPushButton("+")
        self._tgt_plus.setFixedWidth(22)
        self._tgt_plus.setEnabled(False)
        layout.addWidget(self._tgt_plus)

        _sep()

        # Current temperature
        self._cur_icon = _IconLabel()
        self._cur_icon.set_icon(ic.temp_icon(_ICON_SIZE))
        layout.addWidget(self._cur_icon)

        self._cur_label = QLabel("—")
        self._cur_label.setStyleSheet(
            f"color: {_TEXT}; border-radius: 3px; padding: 1px 6px; font-weight: bold;"
        )
        layout.addWidget(self._cur_label)

        _sep()

        # Liquid state
        self._state_icon = _IconLabel()
        layout.addWidget(self._state_icon)
        self._state_label = QLabel("—")
        layout.addWidget(self._state_label)

        _sep()

        # Liquid level
        self._level_icon = _IconLabel()
        layout.addWidget(self._level_icon)
        self._level_label = QLabel("—")
        layout.addWidget(self._level_label)

        _sep()

        # Expand to full view
        expand_btn = QPushButton("⊞")
        expand_btn.setToolTip("Switch to full view")
        expand_btn.setFixedWidth(24)
        expand_btn.clicked.connect(self.show_full)
        layout.addWidget(expand_btn)

        # Set background via stylesheet (the widget itself is not transparent)
        self.setStyleSheet(
            _TOOL_STYLE +
            f"ToolbarWindow {{ background-color: {_BG}; border: 1px solid {_BORDER}; border-radius: 6px; }}"
        )

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self):
        self._backend.connected.connect(self._on_connected)
        self._backend.data_updated.connect(self._on_data)
        self._tgt_minus.clicked.connect(lambda: self._adjust_target(-1))
        self._tgt_plus.clicked.connect(lambda: self._adjust_target(+1))

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_connected(self, connected: bool):
        self._bt_icon.set_icon(ic.bluetooth_icon(_ICON_SIZE, connected))
        self._tgt_minus.setEnabled(connected)
        self._tgt_plus.setEnabled(connected)
        if not connected:
            self._cur_label.setText("—")
            self._cur_label.setStyleSheet("color: #888; border-radius: 3px; padding: 1px 6px;")

    def _on_data(self, data):
        self._last_data = data
        unit = self._settings.temp_unit

        # Battery
        bat = data.battery
        if bat is not None:
            self._bat_icon.set_icon(ic.battery_icon(_ICON_SIZE, bat.percent, bat.on_charging_base))
            self._bat_label.setText(f"{int(bat.percent)}%")
            self._charge_label.setText("⚡" if bat.on_charging_base else "")
        else:
            self._bat_label.setText("—")
            self._charge_label.setText("")

        # Target temp
        self._target_temp_c = data.target_temp
        self._tgt_label.setText(_fmt_temp(data.target_temp, unit))

        # Current temp with colour feedback
        cur_disp = _c_to_display(data.current_temp, unit)
        tgt_disp = _c_to_display(data.target_temp, unit)
        diff = cur_disp - tgt_disp
        if abs(diff) <= 2:
            bg, fg = _GREEN_BG, _GREEN_FG
        elif diff > 2:
            bg, fg = _ORANGE_BG, _ORANGE_FG
        else:
            bg, fg = _BLUE_BG, _BLUE_FG
        self._cur_label.setText(_fmt_temp(data.current_temp, unit))
        self._cur_label.setStyleSheet(
            f"color: {fg}; background-color: {bg}; border-radius: 3px; padding: 1px 6px; font-weight: bold;"
        )

        # Liquid state
        state_int = int(data.liquid_state) if data.liquid_state is not None else -1
        if state_int >= 0:
            self._state_icon.set_icon(ic.liquid_state_icon(_ICON_SIZE, state_int))
            self._state_label.setText(ic.STATE_LABELS.get(state_int, "?"))
        else:
            self._state_label.setText("—")

        # Liquid level
        level = data.liquid_level if data.liquid_level is not None else 0
        level_pct = level / 30 * 100
        self._level_icon.set_icon(ic.liquid_level_icon(_ICON_SIZE, level_pct))
        self._level_label.setText(f"{int(level_pct)}%")

    def _adjust_target(self, delta: int):
        unit = self._settings.temp_unit
        new_display = _c_to_display(self._target_temp_c, unit) + delta
        new_c = max(10.0, min(62.5, _display_to_c(new_display, unit)))
        self._target_temp_c = new_c
        self._tgt_label.setText(_fmt_temp(new_c, unit))
        self._backend.set_target_temp(new_c)

    # ── Drag to reposition ────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._locked:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and not self._locked:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            pos = self.pos()
            self._settings.toolbar_position = {"x": pos.x(), "y": pos.y()}

    # ── Context menu ──────────────────────────────────────────────────────────

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {_BG}; color: {_TEXT}; border: 1px solid {_BORDER}; }}"
            f"QMenu::item:selected {{ background-color: {_BORDER}; }}"
        )
        full_action = menu.addAction("Full View")
        menu.addSeparator()
        lock_action = menu.addAction("Lock Position" if not self._locked else "Unlock Position")
        menu.addSeparator()
        quit_action = menu.addAction("Quit")

        action = menu.exec(event.globalPos())
        if action == full_action:
            self.show_full.emit()
        elif action == lock_action:
            self._locked = not self._locked
        elif action == quit_action:
            QApplication.quit()

    # ── Position persistence ──────────────────────────────────────────────────

    def _restore_position(self):
        pos = self._settings.toolbar_position
        if pos:
            self.move(pos.get("x", 100), pos.get("y", 100))
        else:
            # Default: bottom-right of primary screen
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.adjustSize()
                self.move(geo.right() - self.width() - 20,
                          geo.bottom() - self.height() - 40)

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(_BG)))
        p.setPen(QPen(QColor(_BORDER), 1))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
        p.end()
