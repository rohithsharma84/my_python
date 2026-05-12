import json
import os
from pathlib import Path


class SettingsManager:
    _DEFAULTS = {
        "temp_unit": "F",
        "mug_address": None,
        "toolbar_position": None,
        "auto_connect": True,
    }

    def __init__(self):
        self._path = Path.home() / ".ember_mug_app" / "config.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = dict(self._DEFAULTS)
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError:
            pass

    # --- temp_unit ---
    @property
    def temp_unit(self) -> str:
        return self._data.get("temp_unit", "F")

    @temp_unit.setter
    def temp_unit(self, value: str):
        self._data["temp_unit"] = value
        self.save()

    # --- mug_address ---
    @property
    def mug_address(self) -> str | None:
        return self._data.get("mug_address")

    @mug_address.setter
    def mug_address(self, value: str | None):
        self._data["mug_address"] = value
        self.save()

    # --- toolbar_position ---
    @property
    def toolbar_position(self) -> dict | None:
        return self._data.get("toolbar_position")

    @toolbar_position.setter
    def toolbar_position(self, value: dict | None):
        self._data["toolbar_position"] = value
        self.save()

    # --- auto_connect ---
    @property
    def auto_connect(self) -> bool:
        return self._data.get("auto_connect", True)

    @auto_connect.setter
    def auto_connect(self, value: bool):
        self._data["auto_connect"] = value
        self.save()
