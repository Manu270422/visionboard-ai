"""Reglas de reconocimiento, una clase por gesto.

Esta es la decisión de arquitectura más importante del módulo de gestos:
en vez de un `if/elif` gigante, cada gesto es un objeto con su prioridad y su
condición. Añadir un gesto nuevo = crear una clase y registrarla; no toco nada
de lo que ya funciona (principio abierto/cerrado).

La prioridad importa porque varias poses se solapan: una pinza también tiene el
índice "medio estirado", así que la pinza debe evaluarse antes que el dibujo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.config.settings import GestureSettings
from app.gestures.features import HandSnapshot
from app.gestures.gesture_types import Gesture
from app.vision.landmarks import Finger


class GestureRule(ABC):
    """Contrato de una regla: qué gesto produce, con qué prioridad y cuándo."""

    gesture: Gesture
    priority: int = 0

    def __init__(self, settings: GestureSettings | None = None) -> None:
        self.settings = settings or GestureSettings()

    @abstractmethod
    def matches(self, snapshot: HandSnapshot) -> bool:
        """True si la mano del snapshot corresponde a este gesto."""

    def __repr__(self) -> str:  # pragma: no cover - solo para depurar
        return f"{type(self).__name__}(gesture={self.gesture.value}, priority={self.priority})"


class PinchRule(GestureRule):
    """🤏 Pulgar e índice juntos, con la mano medio cerrada."""

    gesture = Gesture.PINCH
    priority = 100

    def matches(self, snapshot: HandSnapshot) -> bool:
        # Exijo además que el anular y el meñique estén recogidos: así no
        # confundo una mano abierta con los dedos rozándose por perspectiva.
        fingers_ok = not snapshot.is_extended(Finger.RING) and not snapshot.is_extended(
            Finger.PINKY
        )
        return snapshot.pinch < self.settings.pinch_ratio and fingers_ok


class ThumbsUpRule(GestureRule):
    """👍 Solo el pulgar estirado y apuntando hacia arriba."""

    gesture = Gesture.THUMBS_UP
    priority = 90

    def matches(self, snapshot: HandSnapshot) -> bool:
        only_thumb = snapshot.is_extended(Finger.THUMB) and not any(
            snapshot.is_extended(f)
            for f in (Finger.INDEX, Finger.MIDDLE, Finger.RING, Finger.PINKY)
        )
        return only_thumb and snapshot.thumb_up


class DrawRule(GestureRule):
    """☝️ Índice estirado y el resto de dedos largos recogidos."""

    gesture = Gesture.DRAW
    priority = 80

    def matches(self, snapshot: HandSnapshot) -> bool:
        return snapshot.is_extended(Finger.INDEX) and snapshot.long_fingers_folded


class SelectRule(GestureRule):
    """✌️ Índice y medio estirados; anular y meñique recogidos."""

    gesture = Gesture.SELECT
    priority = 70

    def matches(self, snapshot: HandSnapshot) -> bool:
        return (
            snapshot.is_extended(Finger.INDEX)
            and snapshot.is_extended(Finger.MIDDLE)
            and not snapshot.is_extended(Finger.RING)
            and not snapshot.is_extended(Finger.PINKY)
        )


class OpenPalmRule(GestureRule):
    """🖐️ Al menos cuatro dedos estirados."""

    gesture = Gesture.OPEN_PALM
    priority = 60

    def matches(self, snapshot: HandSnapshot) -> bool:
        # Pido 4 y no 5 porque el pulgar es el dedo que peor se mide de frente.
        return snapshot.extended_count >= 4


class FistRule(GestureRule):
    """✊ Ningún dedo estirado."""

    gesture = Gesture.FIST
    priority = 50

    def matches(self, snapshot: HandSnapshot) -> bool:
        return snapshot.extended_count == 0


def default_rules(settings: GestureSettings | None = None) -> list[GestureRule]:
    """Conjunto de reglas por defecto, ya ordenado por prioridad descendente."""
    config = settings or GestureSettings()
    rules: list[GestureRule] = [
        PinchRule(config),
        ThumbsUpRule(config),
        DrawRule(config),
        SelectRule(config),
        OpenPalmRule(config),
        FistRule(config),
    ]
    return sorted(rules, key=lambda rule: rule.priority, reverse=True)
