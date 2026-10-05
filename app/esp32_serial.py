"""Comunicação opcional com um ESP32 pela porta USB/Serial.

Protocolo simples enviado ao ESP32, uma linha por comando:
    LIGHT GREEN
    LIGHT YELLOW
    LIGHT RED
    HEADLIGHT ON
    HEADLIGHT OFF

O sistema continua funcionando em modo simulado quando pyserial não está
instalado, a porta não existe ou o ESP32 está desconectado.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger("esp32")

try:
    import serial  # type: ignore
except Exception:
    serial = None


class ESP32Serial:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200) -> None:
        self._lock = threading.Lock()
        self._port_name = port or ""
        self._baudrate = baudrate
        self._connection = None

    def configure(self, port: Optional[str]) -> bool:
        with self._lock:
            self._close_locked()
            self._port_name = (port or "").strip()
            return self._connect_locked() if self._port_name else False

    def _connect_locked(self) -> bool:
        if not self._port_name or serial is None:
            return False
        try:
            self._connection = serial.Serial(
                self._port_name, self._baudrate, timeout=0.2
            )
            logger.info("ESP32 conectado em %s", self._port_name)
            return True
        except Exception as exc:
            self._connection = None
            logger.warning("Não foi possível conectar ao ESP32 em %s: %s", self._port_name, exc)
            return False

    def _close_locked(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
        self._connection = None

    def send(self, command: str) -> bool:
        with self._lock:
            if self._connection is None and not self._connect_locked():
                return False
            try:
                self._connection.write((command.strip() + "\n").encode("utf-8"))
                return True
            except Exception as exc:
                logger.warning("Falha enviando comando ao ESP32: %s", exc)
                self._close_locked()
                return False

    def set_light(self, state: str) -> bool:
        return self.send(f"LIGHT {state}")

    def set_headlight(self, on: bool) -> bool:
        return self.send(f"HEADLIGHT {'ON' if on else 'OFF'}")

    @property
    def available(self) -> bool:
        with self._lock:
            return self._connection is not None and bool(getattr(self._connection, "is_open", False))

    @property
    def port(self) -> str:
        return self._port_name

    def close(self) -> None:
        with self._lock:
            self._close_locked()
