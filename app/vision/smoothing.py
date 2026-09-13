"""Suavizado del puntero de la mano.

El dedo tiembla y MediaPipe añade ruido frame a frame. Si dibujo directamente
con la posición cruda, los trazos salen dentados. Aplico un filtro exponencial
(EMA) porque es barato, no añade latencia perceptible y se ajusta con un solo
parámetro.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PointSmoother:
    """Media móvil exponencial sobre coordenadas 2D.

    `alpha` es el peso del punto nuevo: 1.0 es sin filtro (crudo) y valores
    bajos suavizan más pero responden más lento.
    """

    alpha: float = 0.35
    _x: float | None = field(default=None, init=False, repr=False)
    _y: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not 0.0 < self.alpha <= 1.0:
            raise ValueError("alpha debe estar en el rango (0, 1].")

    def update(self, x: float, y: float) -> tuple[float, float]:
        """Incorporo una muestra nueva y devuelvo la posición filtrada."""
        if self._x is None or self._y is None:
            # Con la primera muestra no tengo historia: la acepto tal cual.
            self._x, self._y = float(x), float(y)
        else:
            self._x = self.alpha * float(x) + (1.0 - self.alpha) * self._x
            self._y = self.alpha * float(y) + (1.0 - self.alpha) * self._y
        return self._x, self._y

    def update_int(self, x: float, y: float) -> tuple[int, int]:
        """Versión en píxeles enteros, que es lo que consume el motor de dibujo."""
        fx, fy = self.update(x, y)
        return int(round(fx)), int(round(fy))

    def reset(self) -> None:
        """Olvido la historia; lo llamo cuando la mano desaparece del cuadro.

        Si no reseteo, al volver a aparecer la mano el filtro interpolaría
        entre la última posición y la nueva, dibujando una línea fantasma.
        """
        self._x = None
        self._y = None

    @property
    def has_value(self) -> bool:
        return self._x is not None
