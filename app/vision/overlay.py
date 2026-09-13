"""Overlay de landmarks sobre el frame de la cámara.

Dibujo yo mismo el esqueleto en vez de usar `mediapipe.solutions.drawing_utils`
por dos razones: controlo los colores para que combinen con mi interfaz, y no
ato el dibujo a MediaPipe (el overlay funciona con cualquier detector).
"""

from __future__ import annotations

import cv2
import numpy as np

from app.vision.landmarks import HAND_CONNECTIONS, DetectionResult, HandLandmarks, LandmarkIndex

# Colores en BGR porque trabajo el frame con OpenCV antes de pasarlo a Qt.
_BONE_COLOR = (168, 182, 63)  # Verde azulado del acento de la interfaz.
_JOINT_COLOR = (238, 229, 220)
_TIP_COLOR = (99, 121, 224)  # Naranja/rojo para las puntas, que son las que importan.

_FINGERTIPS = frozenset(
    {
        int(LandmarkIndex.THUMB_TIP),
        int(LandmarkIndex.INDEX_TIP),
        int(LandmarkIndex.MIDDLE_TIP),
        int(LandmarkIndex.RING_TIP),
        int(LandmarkIndex.PINKY_TIP),
    }
)


def draw_hand(frame: np.ndarray, hand: HandLandmarks) -> np.ndarray:
    """Dibujo huesos y articulaciones de una mano sobre el frame recibido.

    Modifico el frame en sitio: ya es una copia de trabajo del preview y
    duplicarlo otra vez en cada frame costaría memoria sin ganar nada.
    """
    height, width = frame.shape[:2]
    pixels = hand.to_pixels(width, height)

    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, pixels[start], pixels[end], _BONE_COLOR, 2, cv2.LINE_AA)

    for index, position in enumerate(pixels):
        is_tip = index in _FINGERTIPS
        cv2.circle(
            frame,
            position,
            5 if is_tip else 3,
            _TIP_COLOR if is_tip else _JOINT_COLOR,
            -1,
            cv2.LINE_AA,
        )

    return frame


def draw_detection(frame: np.ndarray, detection: DetectionResult) -> np.ndarray:
    """Dibujo todas las manos detectadas en el frame."""
    for hand in detection.hands:
        draw_hand(frame, hand)
    return frame
