"""
Camada de atuadores físicos (farol/baliza, relé do semáforo, etc).

Em um protótipo real com Raspberry Pi, este módulo controlaria pinos GPIO
para acionar relés/LEDs. Como nem todo ambiente tem RPi.GPIO disponível,
o import é opcional: se não existir hardware, o módulo apenas loga a ação
("modo simulação"), permitindo testar toda a lógica sem hardware conectado
e trocar para hardware real apenas configurando `GPIO_HEADLIGHT_PIN` etc.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("atuadores")

GPIO_HEADLIGHT_PIN = 17
GPIO_GREEN_PIN = 27
GPIO_RED_PIN = 22

try:
    import RPi.GPIO as GPIO  # type: ignore

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_HEADLIGHT_PIN, GPIO.OUT)
    GPIO.setup(GPIO_GREEN_PIN, GPIO.OUT)
    GPIO.setup(GPIO_RED_PIN, GPIO.OUT)
    HARDWARE_AVAILABLE = True
except Exception:
    GPIO = None
    HARDWARE_AVAILABLE = False


class ActuatorController:
    def __init__(self) -> None:
        self._headlight_state = False
        self._light_state = "RED"

    def set_headlight(self, on: bool) -> None:
        if on == self._headlight_state:
            return
        self._headlight_state = on
        if HARDWARE_AVAILABLE:
            GPIO.output(GPIO_HEADLIGHT_PIN, GPIO.HIGH if on else GPIO.LOW)
        logger.info("Farol/baliza de emergência: %s", "LIGADO" if on else "DESLIGADO")

    def set_traffic_light(self, state: str) -> None:
        if state == self._light_state:
            return
        self._light_state = state
        if HARDWARE_AVAILABLE:
            GPIO.output(GPIO_GREEN_PIN, GPIO.HIGH if state == "GREEN" else GPIO.LOW)
            GPIO.output(GPIO_RED_PIN, GPIO.HIGH if state == "RED" else GPIO.LOW)
        logger.info("Semáforo físico: %s", state)

    @property
    def hardware_available(self) -> bool:
        return HARDWARE_AVAILABLE
