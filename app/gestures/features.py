"""Características derivadas de una mano ("snapshot").

Antes de clasificar calculo UNA sola vez las medidas que todas las reglas
necesitan (qué dedos están estirados, la pinza, la escala). Si cada regla las
recalculara, estaría midiendo lo mismo seis veces por frame.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import GestureSettings
from app.vision import geometry
from app.vision.landmarks import Finger, Handedness, HandLandmarks, Point


@dataclass(frozen=True, slots=True)
class HandSnapshot:
    """Fotografía numérica de la mano en un frame concreto."""

    hand: HandLandmarks
    fingers: dict[Finger, bool]
    pinch: float  # Distancia pulgar-índice normalizada.
    scale: float
    thumb_up: bool

    @property
    def extended_count(self) -> int:
        return sum(self.fingers.values())

    @property
    def long_fingers_folded(self) -> bool:
        """True si medio, anular y meñique están recogidos."""
        return not any(self.fingers[f] for f in (Finger.MIDDLE, Finger.RING, Finger.PINKY))

    def is_extended(self, finger: Finger) -> bool:
        return self.fingers[finger]

    @property
    def index_tip(self) -> Point:
        return self.hand.index_tip

    @property
    def thumb_tip(self) -> Point:
        return self.hand.thumb_tip

    @property
    def handedness(self) -> Handedness:
        return self.hand.handedness


def build_snapshot(hand: HandLandmarks, settings: GestureSettings | None = None) -> HandSnapshot:
    """Construyo el snapshot a partir de los landmarks crudos."""
    config = settings or GestureSettings()
    return HandSnapshot(
        hand=hand,
        fingers=geometry.extended_fingers(hand, config.extended_margin),
        pinch=geometry.pinch_ratio(hand),
        scale=geometry.hand_scale(hand),
        thumb_up=geometry.thumb_points_up(hand),
    )
