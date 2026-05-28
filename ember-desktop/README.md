# Ember Mug Desktop App

A PyQt6 desktop app for monitoring and controlling your Ember Mug over Bluetooth (BLE) on Windows.

## Requirements

- Python 3.11+
- `PyQt6`
- `python-ember-mug`
- `bleak`

Install dependencies:

```
pip install PyQt6 python-ember-mug bleak
```

## Running

```
cd ember-desktop
python main.py
```

## First-time Setup

Before the app can control your mug, pair it with Windows:

1. Hold the power button on the bottom of the mug until the LED pulses.
2. Open **Windows Settings → Bluetooth & devices → Add device** and pair the mug.
3. Launch the app and use **Scan for Mug** to find and register the mug's address.

Once scanned, the address is saved and the app will connect automatically on future launches (if auto-connect is enabled).

---

## Full View

The default view on launch. A dark-themed window showing all mug status and controls.

<img width="489" height="675" alt="image" src="https://github.com/user-attachments/assets/7b4bcac9-7b2f-4c6e-b0fd-a0e4296e5e29" />

### Live Status

| Field | Description |
|---|---|
| Battery | Charge percentage with an icon that changes at low/mid/high levels. A ⚡ indicator appears when the mug is on its charging base. |
| Target Temp | The temperature the mug is trying to maintain. Use the **−** and **+** buttons to adjust in 1° increments. |
| Current Temp | The actual liquid temperature. Color-coded: green when at target (±2°), orange when too hot, blue when still heating. |
| Liquid State | The mug's reported state (e.g. Heating, Cooling, Stable, Empty). |
| Liquid Level | Fill level as a percentage (0–100%). |

### Device Info

Displays the mug's BLE name, hardware address, and firmware version once connected.

### Connection

- **Scan for Mug** — scans for Ember devices in pairing mode (prompts you to put the mug in pairing mode first). If multiple mugs are found, a picker dialog lets you choose one.
- **Connect** — connects to the previously scanned mug address.
- **Disconnect** — cleanly disconnects from the mug.
- A status bar at the bottom right of this section shows connection events and error messages.

### Settings

- **°F / °C toggle** — switches the temperature unit for all displays. The choice is saved and persists across restarts.
- **Auto-connect on launch** — when checked, the app automatically connects to the saved mug address on startup. Saved immediately when toggled.

### Switch to Toolbar

The blue **Switch to Toolbar →** button at the bottom hides the full window and shows the compact toolbar instead.

---

## Toolbar Mode

A compact, frameless floating bar that stays on top of all other windows. Intended for use while the mug is connected and you just want a glance at its status.

<img width="546" height="42" alt="image" src="https://github.com/user-attachments/assets/892f1737-3e49-44fb-8e61-3b4076aaf6b2" />

### Display (left to right)

| Element | Description |
|---|---|
| Bluetooth icon | Blue when connected, grey when disconnected. |
| Battery % | Percentage with a battery icon. ⚡ shown in gold when on the charging base. |
| Target Temp | Current target temperature with **−** and **+** buttons. Buttons are disabled when disconnected. |
| Current Temp | Live temperature with the same color coding as full view (green/orange/blue). |
| Liquid State | Icon and short label for the mug's state. |
| Liquid Level | Icon and percentage fill. |
| ⊞ button | Switches back to the full view. |

### Dragging and Position

Click and drag anywhere on the toolbar to reposition it. The position is saved automatically on mouse release and restored the next time the app starts. The toolbar defaults to the bottom-right corner of the primary screen on first launch.

### Right-click Menu

Right-clicking the toolbar opens a context menu with:

- **Full View** — switch to the full window.
- **Lock / Unlock Position** — prevents accidental dragging when locked.
- **Quit** — exits the app cleanly, disconnecting from the mug.

---

## Settings File

Settings are stored at:

```
%USERPROFILE%\.ember_mug_app\config.json
```

Fields saved: `temp_unit`, `mug_address`, `toolbar_position`, `auto_connect`.
