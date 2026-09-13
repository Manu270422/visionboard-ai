"""Configuración única del logging de la aplicación.

Uso `logging` en vez de `print` porque necesito niveles, contexto y un archivo
donde revisar qué pasó cuando la cámara falle en otro computador.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.utils.paths import LOGS_DIR, ensure_directory

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"
_configured = False


def setup_logging(level: str = "INFO", *, to_file: bool = True) -> None:
    """Configuro el logger raíz una sola vez.

    Uso un handler rotativo para que el log no crezca sin control durante
    sesiones largas de cámara (cada frame puede generar mensajes en DEBUG).
    """
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    if to_file:
        try:
            log_dir: Path = ensure_directory(LOGS_DIR)
            file_handler = RotatingFileHandler(
                log_dir / "visionboard.log",
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            # Si no puedo escribir el archivo sigo con consola: no es fatal.
            root.warning("No pude crear el archivo de log; sigo solo con consola.")

    # MediaPipe y absl son muy ruidosos en INFO, los bajo a WARNING.
    for noisy in ("mediapipe", "absl", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Atajo para pedir un logger con el nombre del módulo."""
    return logging.getLogger(name)
