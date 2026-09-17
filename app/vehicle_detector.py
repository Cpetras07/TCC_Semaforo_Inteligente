"""
Detector de veículos e de veículos parados usando subtração de fundo (MOG2).

Este módulo não depende de modelos de IA pesados (YOLO) para funcionar
imediatamente em qualquer máquina, mas foi escrito para que um detector
baseado em rede neural (ex.: YOLOv8 via `ultralytics`) possa substituir o
método `detect()` sem alterar o restante do sistema (ver `USE_YOLO` abaixo).

Lógica:
1. Subtração de fundo identifica blobs em movimento (candidatos a veículo).
2. Cada blob recebe um ID por proximidade de centróide entre frames
   (tracking simples "nearest centroid").
3. Um veículo é considerado "parado" quando seu centróide se desloca menos
   que `STOP_PIXEL_THRESHOLD` por `STOP_FRAMES` frames consecutivos.
4. O sistema expõe a contagem de veículos parados, usada pelo controlador
   de semáforo para decidir o tempo de verde.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import cv2
import numpy as np

# Ative esta flag se instalar `ultralytics` (YOLOv8) para detecção mais precisa.
USE_YOLO = False

MIN_CONTOUR_AREA = 900          # área mínima (px²) para considerar um blob como veículo
STOP_PIXEL_THRESHOLD = 6        # deslocamento máximo (px) para considerar "parado"
STOP_FRAMES = 15                # nº de frames consecutivos parado para confirmar
MAX_MATCH_DISTANCE = 80         # distância máxima (px) para associar blob a track existente
TRACK_TTL_FRAMES = 20           # frames sem atualização até remover um track


@dataclass
class VehicleTrack:
    track_id: int
    centroid: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    still_frames: int = 0
    missed_frames: int = 0
    is_stopped: bool = False


class VehicleDetector:
    def __init__(self) -> None:
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=32, detectShadows=True
        )
        self.tracks: Dict[int, VehicleTrack] = {}
        self._next_id = 1
        self._yolo_model = None

        if USE_YOLO:
            try:
                from ultralytics import YOLO  # import tardio, opcional

                self._yolo_model = YOLO("yolov8n.pt")
            except Exception:
                self._yolo_model = None  # cai para o método clássico se falhar

    # ------------------------------------------------------------------
    def _detect_boxes_classic(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        fg_mask = self.bg_subtractor.apply(frame)
        # remove sombras (valor 127 no MOG2) e ruído
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        thresh = cv2.dilate(thresh, np.ones((7, 7), np.uint8), iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < MIN_CONTOUR_AREA:
                continue
            x, y, w, h = cv2.boundingRect(c)
            boxes.append((x, y, w, h))
        return boxes

    def _detect_boxes_yolo(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        vehicle_classes = {2, 3, 5, 7}  # car, motorcycle, bus, truck (COCO)
        results = self._yolo_model.predict(frame, verbose=False)[0]
        boxes = []
        for box in results.boxes:
            cls = int(box.cls[0])
            if cls not in vehicle_classes:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            boxes.append((x1, y1, x2 - x1, y2 - y1))
        return boxes

    # ------------------------------------------------------------------
    def _update_tracks(self, boxes: List[Tuple[int, int, int, int]]) -> None:
        centroids = [(x + w // 2, y + h // 2) for (x, y, w, h) in boxes]
        unmatched_boxes = list(range(len(boxes)))
        matched_track_ids = set()

        # associa cada detecção ao track existente mais próximo
        for idx in list(unmatched_boxes):
            cx, cy = centroids[idx]
            best_id, best_dist = None, MAX_MATCH_DISTANCE
            for tid, track in self.tracks.items():
                if tid in matched_track_ids:
                    continue
                tx, ty = track.centroid
                dist = ((tx - cx) ** 2 + (ty - cy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist, best_id = dist, tid

            if best_id is not None:
                track = self.tracks[best_id]
                moved = ((track.centroid[0] - cx) ** 2 + (track.centroid[1] - cy) ** 2) ** 0.5
                track.still_frames = track.still_frames + 1 if moved < STOP_PIXEL_THRESHOLD else 0
                track.is_stopped = track.still_frames >= STOP_FRAMES
                track.centroid = (cx, cy)
                track.bbox = boxes[idx]
                track.missed_frames = 0
                matched_track_ids.add(best_id)
                unmatched_boxes.remove(idx)

        # cria novos tracks para o que sobrou
        for idx in unmatched_boxes:
            tid = self._next_id
            self._next_id += 1
            self.tracks[tid] = VehicleTrack(
                track_id=tid, centroid=centroids[idx], bbox=boxes[idx]
            )

        # remove tracks obsoletos
        for tid, track in list(self.tracks.items()):
            if tid not in matched_track_ids:
                track.missed_frames += 1
                if track.missed_frames > TRACK_TTL_FRAMES:
                    del self.tracks[tid]

    # ------------------------------------------------------------------
    def process(self, frame: np.ndarray) -> Dict:
        """Processa um frame e retorna estatísticas + desenha overlays."""
        boxes = (
            self._detect_boxes_yolo(frame)
            if self._yolo_model is not None
            else self._detect_boxes_classic(frame)
        )
        self._update_tracks(boxes)

        total = len(self.tracks)
        moving = sum(1 for t in self.tracks.values() if not t.is_stopped)
        stopped = sum(1 for t in self.tracks.values() if t.is_stopped)

        annotated = frame.copy()
        for track in self.tracks.values():
            x, y, w, h = track.bbox
            color = (0, 0, 255) if track.is_stopped else (0, 255, 0)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            label = f"#{track.track_id}{' PARADO' if track.is_stopped else ''}"
            cv2.putText(
                annotated, label, (x, max(y - 8, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
            )

        return {
            "annotated_frame": annotated,
            "total_vehicles": total,
            "moving_vehicles": moving,
            "stopped_vehicles": stopped,
            "timestamp": time.time(),
        }
