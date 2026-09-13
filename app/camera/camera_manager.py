"""Gestión de la cámara con OpenCV.

Encapsulo `cv2.VideoCapture` para poder hacer tres cosas bien: convertir los
fallos silenciosos de OpenCV en excepciones claras, garantizar que la cámara
siempre se libera, y poder sustituir la cámara por un doble en las pruebas.

OpenCV casi nunca lanza excepciones: devuelve `False`. Si no compruebo cada
retorno, la aplicación se queda "funcionando" con frames vacíos.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.config.settings import CameraSettings
from app.utils.exceptions import CameraError, FrameError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CameraManager:
    """Abre, lee y libera la cámara de forma segura."""

    def __init__(self, settings: CameraSettings | None = None) -> None:
        self._settings = settings or CameraSettings()
        self._settings.validate()
        self._capture: cv2.VideoCapture | None = None

    @property
    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    @property
    def settings(self) -> CameraSettings:
        return self._settings

    def open(self) -> None:
        """Abro la cámara y aplico la resolución y los FPS pedidos.

        Después de pedir una resolución leo la que quedó de verdad: muchas
        webcams ignoran el valor y entregan otro. Si asumiera el valor pedido,
        el mapeo de coordenadas quedaría descuadrado.
        """
        if self.is_open:
            return

        capture = cv2.VideoCapture(self._settings.index)
        if not capture.isOpened():
            capture.release()
            raise CameraError(
                f"No pude abrir la cámara {self._settings.index}. "
                "Verifica que exista, que no esté en uso por otra aplicación "
                "y que la aplicación tenga permisos de cámara."
            )

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._settings.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._settings.height)
        capture.set(cv2.CAP_PROP_FPS, self._settings.fps)
        # Buffer pequeño = menos latencia; prefiero frames frescos a frames en cola.
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._capture = capture
        self._warmup()

        logger.info(
            "Cámara %d abierta a %dx%d @ %.0f FPS",
            self._settings.index,
            self.actual_width,
            self.actual_height,
            self.actual_fps,
        )

    def _warmup(self) -> None:
        """Descarto los primeros frames: suelen venir negros o mal expuestos."""
        assert self._capture is not None
        for _ in range(max(0, self._settings.warmup_frames)):
            self._capture.read()

    @property
    def actual_width(self) -> int:
        return int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)) if self._capture else 0

    @property
    def actual_height(self) -> int:
        return int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self._capture else 0

    @property
    def actual_fps(self) -> float:
        return float(self._capture.get(cv2.CAP_PROP_FPS)) if self._capture else 0.0

    def read(self) -> np.ndarray:
        """Leo un frame BGR. Aplico el espejo aquí si está configurado.

        Volteo horizontalmente porque sin espejo la cámara me devuelve la
        imagen invertida y mover la mano a la derecha movería el cursor a la
        izquierda, que es completamente antinatural al dibujar.
        """
        if self._capture is None:
            raise CameraError("La cámara no está abierta.")

        ok, frame = self._capture.read()
        if not ok or frame is None or frame.size == 0:
            raise FrameError("La cámara devolvió un frame vacío o inválido.")

        if self._settings.mirror:
            frame = cv2.flip(frame, 1)

        return frame

    def release(self) -> None:
        """Libero la cámara. Esto SIEMPRE se tiene que ejecutar al cerrar."""
        if self._capture is not None:
            try:
                self._capture.release()
            except cv2.error as error:  # pragma: no cover - depende del driver
                logger.warning("Error liberando la cámara: %s", error)
            finally:
                self._capture = None
                logger.info("Cámara liberada.")

    def __enter__(self) -> CameraManager:
        self.open()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.release()
