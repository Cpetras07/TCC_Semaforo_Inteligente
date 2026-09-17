"""
Captura de vídeo com troca de fonte em tempo de execução (webcam, arquivo
de vídeo ou URL RTSP/HTTP de câmera IP), pensado para testes reais com
câmera/webcam conectada ao computador.
"""
from __future__ import annotations

import threading
from typing import Optional, Union

import cv2
import numpy as np


class CameraStream:
    def __init__(self, source: Union[int, str] = 0) -> None:
        self._lock = threading.Lock()
        self._source: Union[int, str] = source
        self._cap: Optional[cv2.VideoCapture] = None
        self._open(source)

    def _open(self, source: Union[int, str]) -> bool:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
            self._cap = cv2.VideoCapture(source)
            self._source = source
            return self._cap.isOpened()

    def set_source(self, source: Union[int, str]) -> bool:
        """Troca a fonte em tempo real: índice de webcam (0, 1, ...),
        caminho de arquivo de vídeo, ou URL RTSP/HTTP de câmera IP."""
        return self._open(source)

    def read(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return None
            ok, frame = self._cap.read()
            if not ok:
                return None
            return frame

    @property
    def source(self) -> Union[int, str]:
        return self._source

    @property
    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def release(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
