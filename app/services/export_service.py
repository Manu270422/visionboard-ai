"""Exportación del lienzo a imagen.

Lo saco a un servicio propio y no a un método de la pizarra porque exportar es
entrada/salida, no dibujo. Así la pizarra sigue siendo pura y testeable, y
mañana puedo añadir JPG o SVG sin tocarla.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from app.board import renderer
from app.utils.exceptions import ExportError
from app.utils.logging_config import get_logger
from app.utils.paths import DRAWINGS_DIR, IMAGE_EXTENSION, prepare_output_path, unique_path

logger = get_logger(__name__)


def default_image_path() -> Path:
    """Nombre por defecto con marca de tiempo, sin sobrescribir nada."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return unique_path(DRAWINGS_DIR, f"visionboard_{stamp}", IMAGE_EXTENSION)


def export_png(
    canvas: np.ndarray, path: str | Path | None = None, *, overwrite: bool = True
) -> Path:
    """Guardo el lienzo como PNG y devuelvo la ruta final.

    Recibo el lienzo en RGB (mi formato interno) y lo paso a BGR justo antes de
    escribir, porque `cv2.imwrite` interpreta el array como BGR.
    """
    _validate_canvas(canvas)

    target = (
        default_image_path()
        if path is None
        else prepare_output_path(path, expected_suffix=IMAGE_EXTENSION, overwrite=overwrite)
    )

    try:
        written = cv2.imwrite(str(target), renderer.to_bgr(canvas))
    except cv2.error as error:
        raise ExportError(f"OpenCV no pudo escribir '{target}': {error}") from error

    if not written:
        # imwrite devuelve False sin lanzar: sin esta comprobación creería
        # que guardé la imagen cuando en realidad no se escribió nada.
        raise ExportError(f"No se pudo escribir la imagen en '{target}'.")

    logger.info("Imagen exportada en %s", target)
    return target


def _validate_canvas(canvas: np.ndarray) -> None:
    if not isinstance(canvas, np.ndarray):
        raise ExportError("El lienzo debe ser un array de NumPy.")
    if canvas.ndim != 3 or canvas.shape[2] != 3:
        raise ExportError(f"Esperaba un lienzo de 3 canales y recibí {canvas.shape}.")
    if canvas.dtype != np.uint8:
        raise ExportError(f"Esperaba un lienzo uint8 y recibí {canvas.dtype}.")
