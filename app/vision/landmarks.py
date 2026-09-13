"""Estructuras de datos de la mano detectada.

Convierto la salida cruda de MediaPipe a tipos míos apenas la recibo. Así el
resto de la aplicación (gestos, pizarra, UI) no depende de MediaPipe: si mañana
cambio de motor de detección, solo reescribo el detector.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum, IntEnum


class LandmarkIndex(IntEnum):
    """Índices oficiales de los 21 landmarks de MediaPipe Hands."""

    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


class Finger(Enum):
    """Los cinco dedos, con sus landmarks clave asociados."""

    THUMB = "thumb"
    INDEX = "index"
    MIDDLE = "middle"
    RING = "ring"
    PINKY = "pinky"


# Guardo (mcp, pip, tip) por dedo: es lo que necesito para saber si está estirado.
FINGER_LANDMARKS: dict[Finger, tuple[LandmarkIndex, LandmarkIndex, LandmarkIndex]] = {
    Finger.THUMB: (LandmarkIndex.THUMB_MCP, LandmarkIndex.THUMB_IP, LandmarkIndex.THUMB_TIP),
    Finger.INDEX: (LandmarkIndex.INDEX_MCP, LandmarkIndex.INDEX_PIP, LandmarkIndex.INDEX_TIP),
    Finger.MIDDLE: (LandmarkIndex.MIDDLE_MCP, LandmarkIndex.MIDDLE_PIP, LandmarkIndex.MIDDLE_TIP),
    Finger.RING: (LandmarkIndex.RING_MCP, LandmarkIndex.RING_PIP, LandmarkIndex.RING_TIP),
    Finger.PINKY: (LandmarkIndex.PINKY_MCP, LandmarkIndex.PINKY_PIP, LandmarkIndex.PINKY_TIP),
}

# Conexiones del esqueleto de la mano; las uso para dibujar el overlay yo mismo
# en vez de arrastrar el módulo de dibujo de MediaPipe.
HAND_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)


class Handedness(Enum):
    """Mano izquierda, derecha o desconocida."""

    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"

    @classmethod
    def from_label(cls, label: str | None) -> Handedness:
        if not label:
            return cls.UNKNOWN
        normalized = label.strip().lower()
        if normalized.startswith("l"):
            return cls.LEFT
        if normalized.startswith("r"):
            return cls.RIGHT
        return cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class Point:
    """Punto normalizado (0..1) con profundidad relativa.

    Trabajo en coordenadas normalizadas hasta el último momento: así la lógica
    de gestos no depende de la resolución de la cámara.
    """

    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: Point) -> float:
        """Distancia euclidiana en 2D; ignoro z porque es poco confiable."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def to_pixels(self, width: int, height: int) -> tuple[int, int]:
        return int(self.x * width), int(self.y * height)


@dataclass(frozen=True, slots=True)
class HandLandmarks:
    """Una mano completa: 21 puntos, lateralidad y confianza."""

    points: tuple[Point, ...]
    handedness: Handedness = Handedness.UNKNOWN
    score: float = 0.0

    def __post_init__(self) -> None:
        if len(self.points) != 21:
            raise ValueError(f"Esperaba 21 landmarks y recibí {len(self.points)}.")

    def point(self, index: LandmarkIndex | int) -> Point:
        return self.points[int(index)]

    @property
    def wrist(self) -> Point:
        return self.point(LandmarkIndex.WRIST)

    @property
    def index_tip(self) -> Point:
        return self.point(LandmarkIndex.INDEX_TIP)

    @property
    def thumb_tip(self) -> Point:
        return self.point(LandmarkIndex.THUMB_TIP)

    def to_pixels(self, width: int, height: int) -> tuple[tuple[int, int], ...]:
        return tuple(p.to_pixels(width, height) for p in self.points)

    @classmethod
    def from_iterable(
        cls,
        coordinates: Iterable[Sequence[float]],
        handedness: Handedness = Handedness.UNKNOWN,
        score: float = 0.0,
    ) -> HandLandmarks:
        """Construyo la mano desde cualquier iterable de (x, y[, z]).

        Este constructor me sirve tanto para MediaPipe como para las pruebas,
        donde fabrico manos sintéticas sin necesidad de cámara.
        """
        points = tuple(
            Point(float(c[0]), float(c[1]), float(c[2]) if len(c) > 2 else 0.0) for c in coordinates
        )
        return cls(points=points, handedness=handedness, score=score)


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Resultado de procesar un frame: cero, una o varias manos."""

    hands: tuple[HandLandmarks, ...] = ()

    @property
    def has_hands(self) -> bool:
        return bool(self.hands)

    @property
    def primary(self) -> HandLandmarks | None:
        """Devuelvo la mano con mayor confianza: es la que controla la pizarra."""
        if not self.hands:
            return None
        return max(self.hands, key=lambda hand: hand.score)
