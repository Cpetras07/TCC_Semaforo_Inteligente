"""
Máquina de estados do semáforo inteligente.

Regras:
- Verde mínimo garantido (`MIN_GREEN_SECONDS`) e vermelho mínimo (`MIN_RED_SECONDS`).
- O tempo de verde é estendido dinamicamente conforme o nº de veículos parados
  (mais fila -> mais tempo de verde, até `MAX_GREEN_SECONDS`).
- Veículo de emergência detectado -> força/mantém verde imediatamente
  (modo prioridade), ignorando o timer normal, e aciona o atuador do farol/baliza.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, asdict
from enum import Enum


class LightState(str, Enum):
    RED = "RED"
    GREEN = "GREEN"


MIN_GREEN_SECONDS = 10
MAX_GREEN_SECONDS = 45
MIN_RED_SECONDS = 8
EXTRA_SECONDS_PER_STOPPED_CAR = 2.5


@dataclass
class TrafficState:
    light: str
    seconds_in_state: float
    stopped_vehicles: int
    total_vehicles: int
    emergency_active: bool
    emergency_confidence: float
    headlight_on: bool
    green_time_target: float


class TrafficLightController:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = LightState.RED
        self._state_started_at = time.time()
        self._green_target_seconds = MIN_GREEN_SECONDS
        self._stopped_vehicles = 0
        self._total_vehicles = 0
        self._emergency_active = False
        self._emergency_confidence = 0.0
        self._headlight_on = False

    # ------------------------------------------------------------------
    def _switch(self, new_state: LightState) -> None:
        self._state = new_state
        self._state_started_at = time.time()

    def update(
        self,
        stopped_vehicles: int,
        total_vehicles: int,
        emergency_active: bool,
        emergency_confidence: float,
        headlight_on: bool,
    ) -> TrafficState:
        with self._lock:
            self._stopped_vehicles = stopped_vehicles
            self._total_vehicles = total_vehicles
            self._emergency_active = emergency_active
            self._emergency_confidence = emergency_confidence
            self._headlight_on = headlight_on

            # Em cenarios sem classificacao confiavel de "parado", usamos a maior
            # demanda entre total e parados para representar a fila do cruzamento.
            traffic_demand = max(stopped_vehicles, total_vehicles)

            elapsed = time.time() - self._state_started_at

            # Prioridade máxima: veículo de emergência aproximando -> abre/mantém verde
            if emergency_active:
                if self._state == LightState.RED:
                    self._switch(LightState.GREEN)
                    self._green_target_seconds = MIN_GREEN_SECONDS
                else:
                    # mantém verde enquanto a emergência estiver presente
                    self._green_target_seconds = max(self._green_target_seconds, elapsed + 3)
            elif self._state == LightState.GREEN:
                # tempo de verde cresce com o volume de veículos parados na fila
                self._green_target_seconds = min(
                    MIN_GREEN_SECONDS + traffic_demand * EXTRA_SECONDS_PER_STOPPED_CAR,
                    MAX_GREEN_SECONDS,
                )
                if elapsed >= self._green_target_seconds:
                    self._switch(LightState.RED)
            elif self._state == LightState.RED:
                if elapsed >= MIN_RED_SECONDS and traffic_demand > 0:
                    self._switch(LightState.GREEN)
                    self._green_target_seconds = min(
                        MIN_GREEN_SECONDS + traffic_demand * EXTRA_SECONDS_PER_STOPPED_CAR,
                        MAX_GREEN_SECONDS,
                    )

            return TrafficState(
                light=self._state.value,
                seconds_in_state=round(time.time() - self._state_started_at, 1),
                stopped_vehicles=self._stopped_vehicles,
                total_vehicles=self._total_vehicles,
                emergency_active=self._emergency_active,
                emergency_confidence=round(self._emergency_confidence, 2),
                headlight_on=self._headlight_on,
                green_time_target=round(self._green_target_seconds, 1),
            )

    def as_dict(self, state: TrafficState) -> dict:
        return asdict(state)
