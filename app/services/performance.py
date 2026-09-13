"""Medición de rendimiento.

Mido FPS y tiempo de procesamiento porque en visión por computador es el
indicador que primero avisa de un problema: si los FPS caen, el trazo se
vuelve entrecortado y la culpa casi siempre está en el hilo de captura.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class FpsMeter:
    """FPS con media móvil sobre las últimas N marcas de tiempo."""

    window: int = 30
    _timestamps: deque[float] = field(default_factory=lambda: deque(maxlen=30), init=False)

    def __post_init__(self) -> None:
        self._timestamps = deque(maxlen=max(2, self.window))

    def tick(self, now: float | None = None) -> float:
        """Registro un frame y devuelvo los FPS actuales.

        Uso `perf_counter` y no `time.time` porque es monótono: no salta si el
        reloj del sistema se ajusta en mitad de la sesión.
        """
        moment = now if now is not None else time.perf_counter()
        self._timestamps.append(moment)
        return self.fps

    @property
    def fps(self) -> float:
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed

    def reset(self) -> None:
        self._timestamps.clear()


class Stopwatch:
    """Cronómetro de contexto para medir un bloque concreto.

    Lo uso puntualmente cuando quiero saber cuánto tarda la detección frente
    al render, sin llenar el código de llamadas a `time`.
    """

    def __init__(self) -> None:
        self._start = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self) -> Stopwatch:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0
