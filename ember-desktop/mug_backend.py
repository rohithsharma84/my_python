"""
Async BLE backend running in a dedicated QThread.

All public methods are safe to call from the Qt main thread.
Signals are emitted cross-thread; PyQt6 queues them automatically.
"""
import asyncio
import logging
import threading
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)


class MugBackend(QThread):
    # Emitted with True on successful connect, False on disconnect
    connected = pyqtSignal(bool)
    # Emitted every time the mug's data changes (passes the MugData object)
    data_updated = pyqtSignal(object)
    # Emitted on non-fatal errors (status messages / warnings)
    error = pyqtSignal(str)
    # Emitted after start_discovery(); list of (address, name) tuples
    devices_found = pyqtSignal(list)
    # Discovery scanning started/stopped
    scanning = pyqtSignal(bool)

    def __init__(self, address: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._address = address
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._mug = None
        self._connect_task: Optional[asyncio.Task] = None
        self._running = False
        self._pending: list = []
        self._lock = threading.Lock()

    # ── Public interface (callable from Qt main thread) ──────────────────────

    def connect_to_mug(self, address: Optional[str] = None):
        """Start connecting to the mug at *address* (or the stored address)."""
        if address:
            self._address = address
        self._schedule(self._start_connect(self._address))

    def disconnect_mug(self):
        """Cancel the connection loop (mug will disconnect cleanly)."""
        if self._connect_task and self._loop:
            self._loop.call_soon_threadsafe(self._connect_task.cancel)

    def start_discovery(self):
        """Scan for Ember devices in pairing mode."""
        self._schedule(self._discover())

    def set_target_temp(self, temp_celsius: float):
        """Set the mug target temperature (in Celsius)."""
        if self._mug and self._loop:
            self._schedule(self._set_temp(temp_celsius))

    def stop(self):
        """Cleanly shut down the event loop and thread."""
        self._running = False
        if self._connect_task and self._loop:
            self._loop.call_soon_threadsafe(self._connect_task.cancel)
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait(3000)

    # ── QThread entry point ───────────────────────────────────────────────────

    def run(self):
        self._running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self._lock:
            self._loop = loop
            for coro in self._pending:
                asyncio.run_coroutine_threadsafe(coro, loop)
            self._pending.clear()
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _schedule(self, coro):
        """Thread-safely schedule a coroutine on the backend loop."""
        with self._lock:
            if self._loop is not None:
                asyncio.run_coroutine_threadsafe(coro, self._loop)
            else:
                self._pending.append(coro)

    async def _start_connect(self, address: Optional[str]):
        """Cancel any existing connection, then start a new connect loop."""
        if self._connect_task and not self._connect_task.done():
            self._connect_task.cancel()
            try:
                await self._connect_task
            except (asyncio.CancelledError, Exception):
                pass

        self._connect_task = asyncio.create_task(self._connect_loop(address))

    async def _connect_loop(self, address: Optional[str]):
        """Keep connecting (and reconnecting on drop) until cancelled."""
        from ember_mug.scanner import find_device
        from ember_mug.mug import EmberMug

        while self._running:
            self._mug = None
            try:
                self.error.emit("Searching for mug…")
                result = await find_device(mac=address, timeout=15)
                if result is None or result[0] is None:
                    self.error.emit("Mug not found — is it on and nearby?")
                    await asyncio.sleep(5)
                    continue

                device, adv = result
                model_info = self._get_model_info(adv)
                self._mug = EmberMug(device, model_info)

                async with self._mug.connection():
                    await self._mug.update_all()
                    self.connected.emit(True)
                    self.data_updated.emit(self._mug.data)

                    unregister = self._mug.register_callback(self._on_data_change)
                    try:
                        while self._running:
                            await asyncio.sleep(1)
                            await self._mug.update_queued_attributes()
                    finally:
                        unregister()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.exception("Connection error")
                self.connected.emit(False)
                self._mug = None
                if self._running:
                    self.error.emit(f"Connection lost: {exc!s} — retrying in 5 s")
                    await asyncio.sleep(5)

        self.connected.emit(False)
        self._mug = None

    async def _discover(self):
        """Scan for Ember devices in pairing mode and emit results."""
        from ember_mug.scanner import discover_devices

        self.scanning.emit(True)
        try:
            results = await discover_devices(wait=15)
            devices = [(dev.address, dev.name or "Ember Mug") for dev, _ in results]
            self.devices_found.emit(devices)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.error.emit(f"Discovery error: {exc!s}")
        finally:
            self.scanning.emit(False)

    async def _set_temp(self, temp_celsius: float):
        if self._mug:
            try:
                await self._mug.set_target_temp(temp_celsius)
            except Exception as exc:
                msg = str(exc)
                if "Write Not Permitted" in msg or "not permitted" in msg.lower():
                    self.error.emit(
                        "Write blocked — pair the mug in Windows Bluetooth settings first, then reconnect."
                    )
                else:
                    self.error.emit(f"Could not set temperature: {msg}")

    def _on_data_change(self, data):
        """Called by ember_mug on the asyncio thread; signals queue to Qt."""
        self.data_updated.emit(data)

    @staticmethod
    def _get_model_info(adv):
        try:
            from ember_mug.utils import get_model_info_from_advertiser_data
            return get_model_info_from_advertiser_data(adv)
        except Exception:
            # Fallback: use None-safe default ModelInfo if parsing fails
            try:
                from ember_mug.data import ModelInfo
                return ModelInfo()
            except Exception:
                return None
