"""Paquete de datos que viaja del hilo de visión a la interfaz.

Defino una dataclass en vez de emitir cinco señales sueltas: así el frame, su
detección y sus métricas llegan siempre juntos y coherentes. Si emitiera el
frame por un lado y los landmarks por otro, podrían desincronizarse.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.vision.landmarks import DetectionResult


@dataclass(frozen=True, slots=True)
class FramePacket:
    """Un frame ya procesado, listo para consumir en el hilo de la interfaz."""

    frame_rgb: np.ndarray
    detection: DetectionResult
    fps: float = 0.0
    process_ms: float = 0.0

    @property
    def size(self) -> tuple[int, int]:
        height, width = self.frame_rgb.shape[:2]
        return width, height
