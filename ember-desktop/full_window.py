"""Full-state QMainWindow: status display, pairing, settings."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import icons as ic
from settings_manager import SettingsManager

# Temperature bounds for Ember Mug 2 (in Celsius)
_TEMP_MIN_C = 10.0
_TEMP_MAX_C = 62.5

_DARK = "#1e1e2e"
_CARD = "#252537"
_BORDER = "#3a3a55"
_TEXT = "#e2e8f0"
_MUTED = "#888aaa"
_ACCENT = "#00AAFF"
_GREEN = "#22c55e"
_ORANGE = "#f97316"
_BLUE = "#3b82f6"
_RED = "#ef4444"

_BASE_STYLE = f"""
QMainWindow, QWidget {{ background-color: {_DARK}; color: {_TEXT}; font-family: 'Segoe UI', Arial; }}
QGroupBox {{
    background-color: {_CARD};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 10px 10px 10px;
    font-weight: bold;
    color: {_TEXT};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {_ACCENT}; }}
QLabel {{ color: {_TEXT}; background: transparent; }}
QPushButton {{
    background-color: {_CARD};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 5px;
    padding: 5px 14px;
    font-size: 12px;
}}
QPushButton:hover {{ background-color: {_BORDER}; }}
QPushButton:disabled {{ color: {_MUTED}; }}
QPushButton[toggle_checkbox="true"] {{
    background: transparent;
    border: none;
    color: {_TEXT};
    font-size: 12px;
    padding: 2px 4px;
    text-align: left;
}}
QPushButton[toggle_checkbox="true"]:hover {{ color: {_ACCENT}; background: transparent; }}
QPushButton[toggle_unit="true"] {{
    font-size: 13px;
    font-weight: bold;
    padding: 4px 14px;
    border-radius: 5px;
    border: 2px solid {_BORDER};
    color: {_MUTED};
    background-color: {_CARD};
}}
QPushButton[toggle_unit="true"]:checked {{
    border: 2px solid {_ACCENT};
    color: #000000;
    background-color: {_ACCENT};
}}
"""


def _c_to_display(celsius: float, unit: str) -> float:
    return celsius * 9 / 5 + 32 if unit == "F" else celsius


def _display_to_c(display: float, unit: str) -> float:
    return (display - 32) * 5 / 9 if unit == "F" else display


def _fmt_temp(celsius: float, unit: str) -> str:
    val = _c_to_display(celsius, unit)
    return f"{val:.0f}°{unit}"


class _StatusRow(QWidget):
    """A single labelled row inside the status card."""

    def __init__(self, label: str, icon_size: int = 28):
        super().__init__()
        self._icon_size = icon_size
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(icon_size, icon_size)
        layout.addWidget(self._icon_label)

        self._key_label = QLabel(label)
        self._key_label.setFixedWidth(90)
        self._key_label.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        layout.addWidget(self._key_label)

        self._value_widget = QWidget()
        self._value_layout = QHBoxLayout(self._value_widget)
        self._value_layout.setContentsMargins(0, 0, 0, 0)
        self._value_layout.setSpacing(4)
        layout.addWidget(self._value_widget, stretch=1)

    def set_icon(self, pixmap):
        self._icon_label.setPixmap(
            pixmap.scaled(self._icon_size, self._icon_size,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
        )

    def set_value_widget(self, widget: QWidget):
        while self._value_layout.count():
            item = self._value_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._value_layout.addWidget(widget)
        self._value_layout.addStretch()

    def set_value_text(self, text: str, color: str = _TEXT, bg: str = "transparent"):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; background-color: {bg}; "
            "border-radius: 4px; padding: 1px 6px; font-size: 14px; font-weight: bold;"
        )
        self.set_value_widget(lbl)


class FullWindow(QMainWindow):
    switch_to_toolbar = pyqtSignal()

    def __init__(self, backend, settings: SettingsManager):
        super().__init__()
        self._backend = backend
        self._settings = settings
        self._last_data = None
        self._target_temp_c: float = 57.0   # default until mug reports its own

        self.setWindowTitle("Ember Mug")
        self.setMinimumWidth(400)
        self.setStyleSheet(_BASE_STYLE)

        self._build_ui()
        self._connect_signals()
        self._refresh_ui_connected(False)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(10)

        vbox.addWidget(self._build_header())
        vbox.addWidget(self._build_status_group())
        vbox.addWidget(self._build_device_group())
        vbox.addWidget(self._build_controls_group())
        vbox.addWidget(self._build_settings_group())

        toolbar_btn = QPushButton("Switch to Toolbar  →")
        toolbar_btn.setStyleSheet(
            f"background-color: {_ACCENT}; color: #000; font-weight: bold; padding: 7px;"
        )
        toolbar_btn.clicked.connect(self.switch_to_toolbar)
        vbox.addWidget(toolbar_btn)
        vbox.addStretch()

    def _build_header(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)

        title = QLabel("☕  Ember Mug")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        h.addWidget(title)
        h.addStretch()

        self._bt_icon_label = QLabel()
        self._bt_icon_label.setFixedSize(24, 24)
        h.addWidget(self._bt_icon_label)

        self._conn_label = QLabel("Disconnected")
        self._conn_label.setStyleSheet(f"color: {_MUTED}; font-size: 12px;")
        h.addWidget(self._conn_label)

        return w

    def _build_status_group(self) -> QGroupBox:
        grp = QGroupBox("Live Status")
        vbox = QVBoxLayout(grp)
        vbox.setSpacing(4)

        # Battery row
        self._bat_row = _StatusRow("Battery")
        vbox.addWidget(self._bat_row)

        # Target temp row (with +/- buttons)
        self._tgt_row = _StatusRow("Target Temp")
        self._tgt_minus = QPushButton("−")
        self._tgt_minus.setFixedWidth(28)
        self._tgt_minus.setStyleSheet("padding: 2px 0px;")
        self._tgt_label = QLabel("—")
        self._tgt_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 0 6px;")
        self._tgt_plus = QPushButton("+")
        self._tgt_plus.setFixedWidth(28)
        self._tgt_plus.setStyleSheet("padding: 2px 0px;")
        tgt_widget = QWidget()
        th = QHBoxLayout(tgt_widget)
        th.setContentsMargins(0, 0, 0, 0)
        th.setSpacing(4)
        th.addWidget(self._tgt_minus)
        th.addWidget(self._tgt_label)
        th.addWidget(self._tgt_plus)
        th.addStretch()
        self._tgt_row.set_value_widget(tgt_widget)
        vbox.addWidget(self._tgt_row)

        # Current temp row
        self._cur_row = _StatusRow("Current Temp")
        vbox.addWidget(self._cur_row)

        # Liquid state row
        self._state_row = _StatusRow("Liquid State")
        vbox.addWidget(self._state_row)

        # Liquid level row
        self._level_row = _StatusRow("Liquid Level")
        vbox.addWidget(self._level_row)

        return grp

    def _build_device_group(self) -> QGroupBox:
        grp = QGroupBox("Device Info")
        grid = QGridLayout(grp)
        grid.setColumnStretch(1, 1)
        grid.setSpacing(4)

        def _row(label, row):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
            val = QLabel("—")
            val.setStyleSheet("font-size: 12px;")
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            return val

        self._dev_name_lbl = _row("Name", 0)
        self._dev_addr_lbl = _row("Address", 1)
        self._dev_fw_lbl = _row("Firmware", 2)

        return grp

    def _build_controls_group(self) -> QGroupBox:
        grp = QGroupBox("Connection")
        h = QHBoxLayout(grp)
        h.setSpacing(8)

        self._scan_btn = QPushButton("🔍  Scan for Mug")
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setStyleSheet(f"color: {_GREEN};")
        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setStyleSheet(f"color: {_RED};")

        h.addWidget(self._scan_btn)
        h.addWidget(self._connect_btn)
        h.addWidget(self._disconnect_btn)
        h.addStretch()

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        h.addWidget(self._status_label)

        return grp

    def _build_settings_group(self) -> QGroupBox:
        grp = QGroupBox("Settings")
        h = QHBoxLayout(grp)
        h.setSpacing(10)

        unit_lbl = QLabel("Temp unit:")
        unit_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        h.addWidget(unit_lbl)

        self._unit_f = QPushButton("°F")
        self._unit_f.setCheckable(True)
        self._unit_f.setProperty("toggle_unit", True)
        self._unit_c = QPushButton("°C")
        self._unit_c.setCheckable(True)
        self._unit_c.setProperty("toggle_unit", True)

        if self._settings.temp_unit == "F":
            self._unit_f.setChecked(True)
        else:
            self._unit_c.setChecked(True)

        h.addWidget(self._unit_f)
        h.addWidget(self._unit_c)
        h.addSpacing(20)

        checked = self._settings.auto_connect
        self._auto_cb = QPushButton(
            ("☑" if checked else "☐") + "  Auto-connect on launch"
        )
        self._auto_cb.setCheckable(True)
        self._auto_cb.setChecked(checked)
        self._auto_cb.setProperty("toggle_checkbox", True)
        h.addWidget(self._auto_cb)
        h.addStretch()

        return grp

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self):
        self._backend.connected.connect(self._refresh_ui_connected)
        self._backend.data_updated.connect(self._on_data)
        self._backend.error.connect(self._on_error)
        self._backend.devices_found.connect(self._on_devices_found)
        self._backend.scanning.connect(self._on_scanning)

        self._scan_btn.clicked.connect(self._on_scan)
        self._connect_btn.clicked.connect(self._on_connect)
        self._disconnect_btn.clicked.connect(self._backend.disconnect_mug)
        self._tgt_minus.clicked.connect(lambda: self._adjust_target(-1))
        self._tgt_plus.clicked.connect(lambda: self._adjust_target(+1))

        self._unit_f.clicked.connect(lambda: self._on_unit_changed("F"))
        self._unit_c.clicked.connect(lambda: self._on_unit_changed("C"))
        def _on_auto_toggled(checked: bool):
            self._auto_cb.setText(("☑" if checked else "☐") + "  Auto-connect on launch")
            self._settings.auto_connect = checked
        self._auto_cb.toggled.connect(_on_auto_toggled)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _refresh_ui_connected(self, connected: bool):
        self._bt_icon_label.setPixmap(
            ic.bluetooth_icon(24, connected).scaled(
                24, 24,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        if connected:
            self._conn_label.setText("Connected")
            self._conn_label.setStyleSheet(f"color: {_GREEN}; font-size: 12px;")
        else:
            self._conn_label.setText("Disconnected")
            self._conn_label.setStyleSheet(f"color: {_MUTED}; font-size: 12px;")

        self._connect_btn.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._tgt_minus.setEnabled(connected)
        self._tgt_plus.setEnabled(connected)

        if not connected:
            self._status_label.setText("")

    def _on_data(self, data):
        self._last_data = data
        unit = self._settings.temp_unit

        # Battery
        bat = data.battery
        if bat is not None:
            px = ic.battery_icon(28, bat.percent, bat.on_charging_base)
            self._bat_row.set_icon(px)
            charge_str = " ⚡" if bat.on_charging_base else ""
            self._bat_row.set_value_text(f"{int(bat.percent)}%{charge_str}")
        else:
            self._bat_row.set_value_text("—")

        # Target temp
        self._target_temp_c = data.target_temp
        tgt_px = ic.temp_icon(28)
        self._tgt_row.set_icon(tgt_px)
        self._tgt_label.setText(_fmt_temp(data.target_temp, unit))

        # Current temp
        cur_px = ic.temp_icon(28)
        self._cur_row.set_icon(cur_px)
        cur_disp = _c_to_display(data.current_temp, unit)
        tgt_disp = _c_to_display(data.target_temp, unit)
        diff = cur_disp - tgt_disp
        if abs(diff) <= 2:
            bg, fg = "#1a4d1a", _GREEN
        elif diff > 2:
            bg, fg = "#4d2000", _ORANGE
        else:
            bg, fg = "#001a4d", _BLUE
        self._cur_row.set_value_text(_fmt_temp(data.current_temp, unit), color=fg, bg=bg)

        # Liquid state
        state_int = int(data.liquid_state) if data.liquid_state is not None else -1
        if state_int >= 0:
            state_px = ic.liquid_state_icon(28, state_int)
            self._state_row.set_icon(state_px)
            self._state_row.set_value_text(ic.STATE_LABELS.get(state_int, "Unknown"))
        else:
            self._state_row.set_value_text("—")

        # Liquid level
        level = data.liquid_level if data.liquid_level is not None else 0
        level_pct = level / 30 * 100
        level_px = ic.liquid_level_icon(28, level_pct)
        self._level_row.set_icon(level_px)
        self._level_row.set_value_text(f"{int(level_pct)}%")

        # Device info
        self._dev_name_lbl.setText(data.name or "EMBER")
        if self._settings.mug_address:
            self._dev_addr_lbl.setText(self._settings.mug_address)
        fw = data.firmware
        if fw is not None:
            self._dev_fw_lbl.setText(str(fw))

    def _on_error(self, msg: str):
        self._status_label.setText(msg)

    def _on_scanning(self, active: bool):
        self._scan_btn.setEnabled(not active)
        self._scan_btn.setText("Scanning…" if active else "🔍  Scan for Mug")

    def _on_scan(self):
        reply = QMessageBox.information(
            self,
            "Put mug in pairing mode",
            "Hold the power button on the bottom of your Ember Mug\n"
            "until the LED pulses. Then click OK to start scanning.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Ok:
            self._backend.start_discovery()

    def _on_connect(self):
        addr = self._settings.mug_address
        if not addr:
            QMessageBox.information(
                self,
                "No mug paired",
                "Use 'Scan for Mug' to find and pair your mug first.",
            )
            return
        self._backend.connect_to_mug(addr)

    def _on_devices_found(self, devices: list):
        if not devices:
            QMessageBox.warning(
                self, "No Mugs Found",
                "No Ember Mugs were found in pairing mode.\n"
                "Make sure the LED is pulsing and try again.",
            )
            return

        if len(devices) == 1:
            address, name = devices[0]
            self._save_and_connect(address, name)
            return

        # Multiple devices — let user pick
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Mug")
        dlg.setStyleSheet(_BASE_STYLE)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Multiple Ember devices found. Select one:"))
        lst = QListWidget()
        for addr, name in devices:
            lst.addItem(f"{name}  ({addr})")
        v.addWidget(lst)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        v.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted and lst.currentRow() >= 0:
            address, name = devices[lst.currentRow()]
            self._save_and_connect(address, name)

    def _save_and_connect(self, address: str, name: str):
        self._settings.mug_address = address
        self._dev_addr_lbl.setText(address)
        self._backend.connect_to_mug(address)

    def _adjust_target(self, delta: int):
        unit = self._settings.temp_unit
        current_display = _c_to_display(self._target_temp_c, unit)
        new_display = current_display + delta
        new_c = _display_to_c(new_display, unit)

        # Clamp to Ember Mug limits
        new_c = max(_TEMP_MIN_C, min(_TEMP_MAX_C, new_c))
        self._target_temp_c = new_c
        self._tgt_label.setText(_fmt_temp(new_c, unit))
        self._backend.set_target_temp(new_c)

    def closeEvent(self, event):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def _on_unit_changed(self, unit: str):
        # Enforce mutual exclusion between the two toggle buttons
        self._unit_f.setChecked(unit == "F")
        self._unit_c.setChecked(unit == "C")
        # Qt doesn't auto-repaint property-based styles on state change
        self._unit_f.style().unpolish(self._unit_f)
        self._unit_f.style().polish(self._unit_f)
        self._unit_c.style().unpolish(self._unit_c)
        self._unit_c.style().polish(self._unit_c)
        self._settings.temp_unit = unit
        if self._last_data:
            self._on_data(self._last_data)
