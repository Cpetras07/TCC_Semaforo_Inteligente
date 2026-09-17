"""
Detector heurístico de veículos de emergência.

Combina dois sinais independentes:

1. VISUAL — detecta o padrão de piscar do giroflex (luzes vermelho/azul
   alternadas) analisando a proporção de pixels vermelhos e azuis no frame
   ao longo de uma janela deslizante de tempo. Um giroflex real produz uma
   oscilação característica entre os dois canais de cor.

2. SONORO — captura áudio do microfone e procura a "assinatura" de uma
   sirene: energia concentrada na faixa 500–1800 Hz com modulação periódica
   (o clássico som "wee-woo" varia de frequência ciclicamente).

Qualquer um dos dois sinais ativos já liga o alerta; os dois juntos elevam
a confiança. Se o `sounddevice`/microfone não estiver disponível, o sistema
continua funcionando apenas com o sinal visual.
"""
from __future__ import annotations

import collections
import threading
import time
from dataclasses import dataclass
from typing import Deque, Optional

import cv2
import numpy as np

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False

# --- parâmetros visuais ---
COLOR_WINDOW_SECONDS = 2.5
MIN_COLOR_PIXEL_RATIO = 0.0025   # % mínima de pixels da cor no frame para contar
FLICKER_MIN_TRANSITIONS = 3      # nº mínimo de alternâncias vermelho<->azul na janela

# --- parâmetros de áudio (sirene) ---
SAMPLE_RATE = 22050
BLOCK_DURATION = 0.25            # segundos por bloco de análise
SIREN_BAND_HZ = (500, 1800)
SIREN_ENERGY_RATIO_THRESHOLD = 0.35  # % da energia total concentrada na banda
SIREN_HISTORY_SECONDS = 3.0


@dataclass
class EmergencyStatus:
    visual_alert: bool = False
    audio_alert: bool = False
    confidence: float = 0.0
    headlight_on: bool = False

    @property
    def is_emergency(self) -> bool:
        return self.visual_alert or self.audio_alert


class LightBarDetector:
    """Detecta padrão de giroflex vermelho/azul piscando no frame."""

    def __init__(self, fps_estimate: int = 15) -> None:
        window_len = max(int(COLOR_WINDOW_SECONDS * fps_estimate), 10)
        self._red_ratio_history: Deque[float] = collections.deque(maxlen=window_len)
        self._blue_ratio_history: Deque[float] = collections.deque(maxlen=window_len)

    @staticmethod
    def _color_ratio(hsv: np.ndarray, lower1, upper1, lower2=None, upper2=None) -> float:
        mask = cv2.inRange(hsv, lower1, upper1)
        if lower2 is not None:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower2, upper2))
        return float(np.count_nonzero(mask)) / mask.size

    def update(self, frame: np.ndarray) -> bool:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # vermelho ocupa duas faixas no HSV (perto de 0 e perto de 180)
        red_ratio = self._color_ratio(
            hsv,
            np.array([0, 120, 150]), np.array([10, 255, 255]),
            np.array([170, 120, 150]), np.array([180, 255, 255]),
        )
        blue_ratio = self._color_ratio(
            hsv, np.array([100, 120, 150]), np.array([130, 255, 255])
        )

        self._red_ratio_history.append(red_ratio)
        self._blue_ratio_history.append(blue_ratio)

        if len(self._red_ratio_history) < self._red_ratio_history.maxlen:
            return False

        reds = np.array(self._red_ratio_history)
        blues = np.array(self._blue_ratio_history)

        has_signal = reds.max() > MIN_COLOR_PIXEL_RATIO or blues.max() > MIN_COLOR_PIXEL_RATIO
        if not has_signal:
            return False

        # conta alternâncias: momentos em que vermelho domina vs azul domina
        dominance = np.sign(reds - blues)
        transitions = int(np.count_nonzero(np.diff(dominance) != 0))

        return transitions >= FLICKER_MIN_TRANSITIONS


class SirenDetector:
    """Detecta sirene analisando energia espectral do microfone."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._band_energy_history: Deque[float] = collections.deque(
            maxlen=max(int(SIREN_HISTORY_SECONDS / BLOCK_DURATION), 4)
        )
        self._stream: Optional["sd.InputStream"] = None
        self._enabled = False

    def start(self) -> bool:
        if not AUDIO_AVAILABLE:
            return False
        if self._enabled:
            return True
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                blocksize=int(SAMPLE_RATE * BLOCK_DURATION),
                callback=self._audio_callback,
            )
            self._stream.start()
            self._enabled = True
        except Exception:
            self._enabled = False
        return self._enabled

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        self._stream = None
        self._enabled = False

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        samples = indata[:, 0].astype(np.float64)
        if samples.size == 0:
            return

        windowed = samples * np.hanning(samples.size)
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(samples.size, d=1.0 / SAMPLE_RATE)

        total_energy = float(spectrum.sum()) + 1e-9
        band_mask = (freqs >= SIREN_BAND_HZ[0]) & (freqs <= SIREN_BAND_HZ[1])
        band_energy = float(spectrum[band_mask].sum())
        ratio = band_energy / total_energy

        with self._lock:
            self._band_energy_history.append(ratio)

    def is_siren_detected(self) -> bool:
        if not self._enabled:
            return False
        with self._lock:
            if len(self._band_energy_history) < self._band_energy_history.maxlen:
                return False
            history = np.array(self._band_energy_history)
        # sirene real modula: precisa de energia alta E variação (não ruído constante)
        return bool(history.mean() > SIREN_ENERGY_RATIO_THRESHOLD and history.std() > 0.02)

    @property
    def enabled(self) -> bool:
        return self._enabled


class EmergencyDetector:
    def __init__(self, fps_estimate: int = 15) -> None:
        self.light_bar_detector = LightBarDetector(fps_estimate=fps_estimate)
        self.siren_detector = SirenDetector()

    def enable_audio(self) -> bool:
        return self.siren_detector.start()

    def disable_audio(self) -> None:
        self.siren_detector.stop()

    def process(self, frame: np.ndarray) -> EmergencyStatus:
        visual_alert = self.light_bar_detector.update(frame)
        audio_alert = self.siren_detector.is_siren_detected()

        confidence = 0.0
        if visual_alert:
            confidence += 0.6
        if audio_alert:
            confidence += 0.6
        confidence = min(confidence, 1.0)

        status = EmergencyStatus(
            visual_alert=visual_alert,
            audio_alert=audio_alert,
            confidence=confidence,
        )
        # Regra do projeto: sirene ligada -> aciona farol/atuador automaticamente
        status.headlight_on = status.is_emergency
        return status
