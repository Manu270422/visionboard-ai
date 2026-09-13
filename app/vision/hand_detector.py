"""Detección de manos con MediaPipe.

Este es el único módulo del proyecto que conoce MediaPipe. Todo lo demás habla
con `DetectionResult`, que es mío. Esa frontera es la que me permitiría cambiar
a otro detector (o a un modelo propio) sin tocar gestos, pizarra ni interfaz.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.config.settings import VisionSettings
from app.utils.exceptions import VisionError
from app.utils.logging_config import get_logger
from app.vision.landmarks import DetectionResult, Handedness, HandLandmarks

logger = get_logger(__name__)


class HandDetector:
    """Envuelvo `mediapipe.solutions.hands` y devuelvo datos tipados míos."""

    def __init__(self, settings: VisionSettings | None = None) -> None:
        self._settings = settings or VisionSettings()
        self._settings.validate()
        self._hands: Any | None = None
        self._closed = False

    def open(self) -> None:
        """Cargo el modelo.

        Importo MediaPipe aquí dentro y no arriba del archivo a propósito: la
        importación tarda y arrastra TensorFlow Lite, así que solo la pago
        cuando realmente voy a detectar manos. Además puedo convertir el
        ImportError en un error mío con un mensaje entendible.
        """
        if self._hands is not None:
            return

        try:
            import mediapipe as mp
        except ImportError as error:
            raise VisionError(
                "MediaPipe no está instalado. Ejecuta: pip install -r requirements.txt"
            ) from error

        try:
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=self._settings.max_hands,
                model_complexity=self._settings.model_complexity,
                min_detection_confidence=self._settings.detection_confidence,
                min_tracking_confidence=self._settings.tracking_confidence,
            )
        except (RuntimeError, ValueError, OSError) as error:
            raise VisionError(f"No pude inicializar MediaPipe Hands: {error}") from error

        logger.info(
            "MediaPipe Hands listo (manos=%d, complejidad=%d)",
            self._settings.max_hands,
            self._settings.model_complexity,
        )

    def process(self, rgb_frame: np.ndarray) -> DetectionResult:
        """Proceso un frame **en RGB** y devuelvo las manos encontradas.

        Exijo RGB en la firma en vez de convertir aquí para no hacer la
        conversión dos veces: quien captura el frame ya la hizo una vez para
        mostrarlo en pantalla.
        """
        if self._closed:
            raise VisionError("El detector ya fue cerrado.")
        if self._hands is None:
            self.open()

        self._validate_frame(rgb_frame)

        assert self._hands is not None  # ya lo abrí arriba; esto es para mypy

        # Marco el array como de solo lectura: MediaPipe evita una copia interna
        # y gano algunos milisegundos por frame.
        rgb_frame.flags.writeable = False
        try:
            raw = self._hands.process(rgb_frame)
        except (RuntimeError, ValueError) as error:
            raise VisionError(f"MediaPipe falló procesando el frame: {error}") from error
        finally:
            rgb_frame.flags.writeable = True

        return self._parse(raw)

    @staticmethod
    def _validate_frame(frame: np.ndarray) -> None:
        if not isinstance(frame, np.ndarray):
            raise VisionError("El frame debe ser un array de NumPy.")
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise VisionError(f"Esperaba un frame RGB de 3 canales y recibí {frame.shape}.")
        if frame.dtype != np.uint8:
            raise VisionError(f"Esperaba un frame uint8 y recibí {frame.dtype}.")

    @staticmethod
    def _parse(raw: Any) -> DetectionResult:
        """Traduzco la respuesta de MediaPipe a mis dataclasses."""
        landmark_sets = getattr(raw, "multi_hand_landmarks", None)
        if not landmark_sets:
            return DetectionResult()

        handedness_info = getattr(raw, "multi_handedness", None) or []
        hands: list[HandLandmarks] = []

        for position, landmark_set in enumerate(landmark_sets):
            label, score = "", 0.0
            if position < len(handedness_info):
                classification = handedness_info[position].classification[0]
                label = classification.label
                score = float(classification.score)

            hands.append(
                HandLandmarks.from_iterable(
                    ((lm.x, lm.y, lm.z) for lm in landmark_set.landmark),
                    handedness=Handedness.from_label(label),
                    score=score,
                )
            )

        return DetectionResult(hands=tuple(hands))

    def close(self) -> None:
        """Libero el modelo. Lo llamo siempre al cerrar la aplicación."""
        if self._hands is not None:
            try:
                self._hands.close()
            except (RuntimeError, ValueError) as error:
                logger.warning("Error cerrando MediaPipe: %s", error)
            finally:
                self._hands = None
        self._closed = True
        logger.info("Detector de manos cerrado.")

    def __enter__(self) -> HandDetector:
        self.open()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()
