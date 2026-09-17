"""
Servidor web do Semáforo Inteligente.

Expõe:
- GET  /                 -> dashboard (HTML)
- GET  /video_feed       -> stream MJPEG da câmera com overlays de detecção
- GET  /api/status       -> snapshot JSON do estado atual
- POST /api/source       -> troca a fonte de vídeo (webcam/arquivo/RTSP)
- POST /api/audio        -> liga/desliga detecção de sirene por microfone
- WebSocket (SocketIO)   -> evento "status_update" a cada ~0.5s
"""
from __future__ import annotations

import logging
import threading
import time

import cv2
from flask import Flask, Response, jsonify, render_template, request
from flask_socketio import SocketIO

from .actuators import ActuatorController
from .camera_stream import CameraStream
from .emergency_detector import EmergencyDetector
from .traffic_controller import TrafficLightController
from .vehicle_detector import VehicleDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("semaforo")

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["SECRET_KEY"] = "semaforo-inteligente-dev"
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

camera = CameraStream(source=0)
vehicle_detector = VehicleDetector()
emergency_detector = EmergencyDetector()
traffic_controller = TrafficLightController()
actuators = ActuatorController()

_frame_lock = threading.Lock()
_latest_jpeg: bytes | None = None
_latest_status: dict = {}
_processing_active = True
_no_camera_warned = False
_simulation_lock = threading.Lock()
_manual_simulation = {
    "enabled": False,
    "cars": 0,
    "motorcycles": 0,
    "ambulance": False,
    "siren": False,
}


def _to_int(value, default: int = 0, min_value: int = 0, max_value: int = 200) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(max_value, parsed))


def _placeholder_frame(message: str):
    import numpy as np

    frame = np.zeros((480, 640, 3), dtype="uint8")
    cv2.putText(
        frame, message, (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
    )
    return frame


def _processing_loop() -> None:
    global _latest_jpeg, _latest_status, _no_camera_warned
    while _processing_active:
        frame = camera.read()
        if frame is None:
            if not _no_camera_warned:
                logger.warning(
                    "Nenhum frame recebido da fonte de vídeo (%s). "
                    "Verifique se a webcam/URL está conectada.",
                    camera.source,
                )
                _no_camera_warned = True
            frame = _placeholder_frame("Sem sinal de camera/webcam")
            time.sleep(0.5)
        else:
            _no_camera_warned = False

        vehicle_result = vehicle_detector.process(frame)
        emergency_status = emergency_detector.process(frame)

        with _simulation_lock:
            simulation = dict(_manual_simulation)

        if simulation["enabled"]:
            manual_total = simulation["cars"] + simulation["motorcycles"]
            manual_emergency = simulation["ambulance"] or simulation["siren"]

            vehicle_result["total_vehicles"] = manual_total
            vehicle_result["moving_vehicles"] = 0
            # Sem sensores de pista, usamos o total manual como fila parada para simular ciclo real.
            vehicle_result["stopped_vehicles"] = manual_total

            emergency_status.visual_alert = simulation["ambulance"]
            emergency_status.audio_alert = simulation["siren"]
            emergency_status.confidence = 1.0 if simulation["ambulance"] and simulation["siren"] else (0.85 if manual_emergency else 0.0)
            emergency_status.headlight_on = manual_emergency
        actuators.set_headlight(emergency_status.headlight_on)

        traffic_state = traffic_controller.update(
            stopped_vehicles=vehicle_result["stopped_vehicles"],
            total_vehicles=vehicle_result["total_vehicles"],
            emergency_active=emergency_status.is_emergency,
            emergency_confidence=emergency_status.confidence,
            headlight_on=emergency_status.headlight_on,
        )
        actuators.set_traffic_light(traffic_state.light)

        annotated = vehicle_result["annotated_frame"]
        _draw_hud(annotated, traffic_state, emergency_status)

        ok, buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok:
            with _frame_lock:
                _latest_jpeg = buf.tobytes()

        status_dict = traffic_controller.as_dict(traffic_state)
        status_dict["moving_vehicles"] = vehicle_result.get("moving_vehicles", 0)
        status_dict["audio_enabled"] = emergency_detector.siren_detector.enabled
        status_dict["camera_source"] = str(camera.source)
        status_dict["hardware_available"] = actuators.hardware_available
        status_dict["manual_mode"] = simulation["enabled"]
        status_dict["manual_cars"] = simulation["cars"]
        status_dict["manual_motorcycles"] = simulation["motorcycles"]
        status_dict["manual_ambulance"] = simulation["ambulance"]
        status_dict["manual_siren"] = simulation["siren"]
        _latest_status = status_dict
        socketio.emit("status_update", status_dict)

        time.sleep(0.03)  # ~30 fps alvo de processamento


def _draw_hud(frame, traffic_state, emergency_status) -> None:
    color = (0, 255, 0) if traffic_state.light == "GREEN" else (0, 0, 255)
    cv2.circle(frame, (30, 30), 18, color, -1)
    cv2.putText(
        frame, f"SEMAFORO: {traffic_state.light}", (60, 38),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
    )
    cv2.putText(
        frame,
        f"Parados: {traffic_state.stopped_vehicles} | Total: {traffic_state.total_vehicles}",
        (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
    )
    if emergency_status.is_emergency:
        cv2.putText(
            frame, "VEICULO DE EMERGENCIA DETECTADO", (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2,
        )


def _mjpeg_generator():
    while True:
        with _frame_lock:
            frame = _latest_jpeg
        if frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        time.sleep(0.03)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(_mjpeg_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/status")
def api_status():
    return jsonify(_latest_status)


@app.route("/api/source", methods=["POST"])
def api_source():
    data = request.get_json(force=True, silent=True) or {}
    source = data.get("source", "0")
    # tenta converter para índice inteiro (webcam); senão usa como string (arquivo/URL)
    try:
        source_value = int(source)
    except (TypeError, ValueError):
        source_value = source

    ok = camera.set_source(source_value)
    return jsonify({"ok": ok, "source": str(source_value)})


@app.route("/api/audio", methods=["POST"])
def api_audio():
    data = request.get_json(force=True, silent=True) or {}
    enable = bool(data.get("enable", False))
    if enable:
        ok = emergency_detector.enable_audio()
    else:
        emergency_detector.disable_audio()
        ok = True
    return jsonify({"ok": ok, "audio_enabled": emergency_detector.siren_detector.enabled})


@app.route("/api/simulation", methods=["POST"])
def api_simulation():
    data = request.get_json(force=True, silent=True) or {}
    with _simulation_lock:
        _manual_simulation["enabled"] = bool(data.get("enabled", _manual_simulation["enabled"]))
        _manual_simulation["cars"] = _to_int(data.get("cars", _manual_simulation["cars"]))
        _manual_simulation["motorcycles"] = _to_int(data.get("motorcycles", _manual_simulation["motorcycles"]))
        _manual_simulation["ambulance"] = bool(data.get("ambulance", _manual_simulation["ambulance"]))
        _manual_simulation["siren"] = bool(data.get("siren", _manual_simulation["siren"]))
        snapshot = dict(_manual_simulation)

    return jsonify({"ok": True, **snapshot})


def start_background_processing() -> None:
    thread = threading.Thread(target=_processing_loop, daemon=True)
    thread.start()
