"""Punto de entrada de VisionBoard AI.

Mantengo este archivo mínimo a propósito: solo lee argumentos, prepara el
logging, carga la configuración y levanta la ventana. Toda la lógica real vive
en los módulos; si `main.py` empieza a crecer es señal de que algo se está
escapando de su capa.
"""

from __future__ import annotations

import argparse
import sys

from app.config.settings import AppSettings
from app.config.storage import load_settings
from app.utils.logging_config import get_logger, setup_logging


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Opciones de línea de comandos.

    `--no-camera` me sirve para trabajar en un equipo sin webcam y para probar
    la interfaz con el ratón; `--camera` me deja elegir otra cámara cuando
    tengo varias conectadas.
    """
    parser = argparse.ArgumentParser(
        prog="visionboard",
        description="Pizarrón virtual controlado por gestos de la mano.",
    )
    parser.add_argument("--camera", type=int, default=None, help="Índice de la cámara (0, 1, 2…).")
    parser.add_argument("--no-camera", action="store_true", help="Arranca solo con ratón.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de detalle del log.",
    )
    parser.add_argument("--width", type=int, default=None, help="Ancho del lienzo en píxeles.")
    parser.add_argument("--height", type=int, default=None, help="Alto del lienzo en píxeles.")
    return parser.parse_args(argv)


def build_settings(arguments: argparse.Namespace) -> AppSettings:
    """Cargo la configuración guardada y le aplico encima los argumentos.

    El orden es importante: lo que escribo en la terminal debe pesar más que
    lo que quedó guardado en la sesión anterior.
    """
    settings = load_settings()

    if arguments.camera is not None:
        settings.camera.index = arguments.camera
    if arguments.width is not None:
        settings.board.width = arguments.width
    if arguments.height is not None:
        settings.board.height = arguments.height

    settings.validate()
    return settings


def main(argv: list[str] | None = None) -> int:
    """Arranco la aplicación y devuelvo el código de salida del proceso."""
    arguments = parse_arguments(argv)
    setup_logging(arguments.log_level)
    logger = get_logger(__name__)

    try:
        settings = build_settings(arguments)
    except Exception as error:  # noqa: BLE001 - último filtro antes de rendirme
        logger.error("Configuración inválida: %s", error)
        return 2

    # Importo Qt aquí y no arriba porque tarda bastante en cargar: si el
    # usuario solo pidió `--help`, no quiero pagar ese costo.
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    application = QApplication(sys.argv[:1])
    application.setApplicationName("VisionBoard AI")

    window = MainWindow(settings, use_camera=not arguments.no_camera)
    window.show()

    logger.info("VisionBoard AI en marcha.")
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
