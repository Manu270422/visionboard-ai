"""Clasificador de gestos y estabilizador temporal.

Separo dos responsabilidades que suelen mezclarse:

- El clasificador mira UN frame y dice qué gesto ve.
- El estabilizador mira la secuencia y decide cuándo el gesto es real.

Sin el segundo, un frame ruidoso en mitad de un trazo cambiaría de herramienta
y me arruinaría el dibujo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import GestureSettings
from app.gestures.features import HandSnapshot, build_snapshot
from app.gestures.gesture_types import Gesture
from app.gestures.rules import GestureRule, default_rules
from app.vision.landmarks import HandLandmarks


@dataclass(frozen=True, slots=True)
class GestureReading:
    """Lo que entrego por frame: gesto detectado y la mano que lo produjo."""

    gesture: Gesture
    snapshot: HandSnapshot | None = None

    @property
    def has_hand(self) -> bool:
        return self.snapshot is not None


class GestureClassifier:
    """Evalúa las reglas registradas y devuelve la de mayor prioridad que encaje."""

    def __init__(
        self,
        settings: GestureSettings | None = None,
        rules: list[GestureRule] | None = None,
    ) -> None:
        self._settings = settings or GestureSettings()
        self._settings.validate()
        self._rules = rules if rules is not None else default_rules(self._settings)

    @property
    def rules(self) -> tuple[GestureRule, ...]:
        return tuple(self._rules)

    def register(self, rule: GestureRule) -> None:
        """Agrego una regla nueva en caliente y reordeno por prioridad.

        Este método es la puerta para los gestos futuros: no necesito modificar
        el clasificador para enseñarle un gesto más.
        """
        self._rules.append(rule)
        self._rules.sort(key=lambda item: item.priority, reverse=True)

    def classify(self, hand: HandLandmarks | None) -> GestureReading:
        """Clasifico una mano. Si no hay mano, devuelvo NONE sin inventar nada."""
        if hand is None:
            return GestureReading(Gesture.NONE)

        snapshot = build_snapshot(hand, self._settings)
        for rule in self._rules:
            if rule.matches(snapshot):
                return GestureReading(rule.gesture, snapshot)

        return GestureReading(Gesture.NONE, snapshot)


class GestureStabilizer:
    """Confirma un gesto solo tras verlo N frames seguidos.

    Es un filtro de histéresis simple: mientras el gesto candidato no acumule
    suficientes repeticiones, mantengo el último gesto confirmado.
    """

    def __init__(self, required_frames: int = 3) -> None:
        if required_frames < 1:
            raise ValueError("Necesito al menos 1 frame para confirmar un gesto.")
        self._required = required_frames
        self._stable = Gesture.NONE
        self._candidate = Gesture.NONE
        self._streak = 0

    @property
    def current(self) -> Gesture:
        return self._stable

    @property
    def required_frames(self) -> int:
        return self._required

    def update(self, gesture: Gesture) -> Gesture:
        """Alimento el filtro con la lectura del frame y devuelvo el gesto estable."""
        if gesture is self._candidate:
            self._streak += 1
        else:
            self._candidate = gesture
            self._streak = 1

        if self._streak >= self._required:
            self._stable = self._candidate

        return self._stable

    def changed_to(self, gesture: Gesture) -> bool:
        """Consulta de conveniencia para los flancos de subida."""
        return self._stable is gesture

    def reset(self) -> None:
        self._stable = Gesture.NONE
        self._candidate = Gesture.NONE
        self._streak = 0
