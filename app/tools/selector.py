"""Herramienta de selección.

No modifica el lienzo: solo mantiene un rectángulo de selección. Hoy la uso
como puntero (mover el cursor sin pintar) y como base para las funciones que
vienen después: recortar, mover una región o mandar esa región al módulo de IA
para reconocer la figura dibujada.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.board.commands import Command
from app.board.strokes import Pixel
from app.tools.base import Tool, ToolContext, ToolId


@dataclass(frozen=True, slots=True)
class Selection:
    """Rectángulo normalizado: `left` siempre es menor que `right`."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    @classmethod
    def from_points(cls, start: Pixel, end: Pixel) -> Selection:
        """Ordeno las coordenadas para poder arrastrar en cualquier dirección."""
        return cls(
            left=min(start[0], end[0]),
            top=min(start[1], end[1]),
            right=max(start[0], end[0]),
            bottom=max(start[1], end[1]),
        )


class SelectorTool(Tool):
    """Puntero y selección rectangular. Nunca produce comandos de dibujo."""

    id = ToolId.SELECTOR
    label = "Selección"
    shortcut = "S"
    continuous = False

    def __init__(self) -> None:
        super().__init__()
        self._start: Pixel | None = None
        self._current: Pixel | None = None
        self._selection: Selection | None = None

    @property
    def selection(self) -> Selection | None:
        return self._selection

    def press(self, point: Pixel, context: ToolContext) -> None:
        self._active = True
        self._start = point
        self._current = point
        self._selection = None

    def move(self, point: Pixel, context: ToolContext) -> None:
        if self._active:
            self._current = point

    def release(self, context: ToolContext) -> Command | None:
        """Cierro la selección y devuelvo None: el lienzo no cambia."""
        if self._start is not None and self._current is not None:
            candidate = Selection.from_points(self._start, self._current)
            self._selection = None if candidate.is_empty else candidate

        self._active = False
        self._start = None
        self._current = None
        return None

    def cancel(self) -> None:
        super().cancel()
        self._start = None
        self._current = None

    def clear_selection(self) -> None:
        self._selection = None
