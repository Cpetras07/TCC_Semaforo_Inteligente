"""Ponto de entrada do Semáforo Inteligente.

Uso:
    python run.py [--port 5000] [--source 0]
"""
import argparse

from app.server import app, actuators, camera, socketio, start_background_processing


def main() -> None:
    parser = argparse.ArgumentParser(description="Semáforo Inteligente - servidor")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--esp32-port",
        default="",
        help="Porta USB do ESP32, por exemplo COM3. Opcional.",
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Índice da webcam (0,1,...), caminho de arquivo de vídeo ou URL RTSP/HTTP",
    )
    args = parser.parse_args()

    try:
        source_value = int(args.source)
    except ValueError:
        source_value = args.source
    camera.set_source(source_value)
    if args.esp32_port:
        actuators.configure_esp32(args.esp32_port)

    start_background_processing()

    print(f"\n>> Acesse o painel em: http://localhost:{args.port}\n")
    socketio.run(app, host="0.0.0.0", port=args.port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
