"""Herramienta de figuras geométricas.

Una sola clase parametrizada por `ShapeKind` en vez de cuatro clases casi
idénticas (línea, rectángulo, círculo, flecha). El comportamiento es el mismo
—dos puntos definen la figura— y lo único que cambia es qué dibuja el renderer.
"""

from __future__ import annotations

from app.board.commands import Command, ShapeCommand
from app.board.strokes import Pixel, Shape, ShapeKind
from app.tools.base import Tool, ToolContext, ToolId

# Relaciono cada figura con su identificador de herramienta y su etiqueta.
_SHAPE_METADATA: dict[ShapeKind, tuple[ToolId, str, str]] = {
    ShapeKind.LINE: (ToolId.LINE, "Línea", "L"),
    ShapeKind.RECTANGLE: (ToolId.RECTANGLE, "Rectángulo", "R"),
    ShapeKind.CIRCLE: (ToolId.CIRCLE, "Círculo", "C"),
    ShapeKind.ARROW: (ToolId.ARROW, "Flecha", "F"),
}


class ShapeTool(Tool):
    """Dibuja una figura arrastrando desde el punto inicial al final."""

    continuous = False  # No pinta al moverse: solo muestra la vista previa.

    def __init__(self, kind: ShapeKind = ShapeKind.RECTANGLE, filled: bool = False) -> None:
        super().__init__()
        self.kind = kind
        self.filled = filled
        self.id, self.label, self.shortcut = _SHAPE_METADATA[kind]
        self._start: Pixel | None = None
        self._end: Pixel | None = None

    def press(self, point: Pixel, context: ToolContext) -> None:
        self._active = True
        self._start = point
        self._end = point

    def move(self, point: Pixel, context: ToolContext) -> None:
        if self._active:
            self._end = point

    def release(self, context: ToolContext) -> Command | None:
        command = self._build(context)
        self._active = False
        self._start = None
        self._end = None
        return command

    def preview(self, context: ToolContext) -> Command | None:
        return self._build(context) if self._active else None

    def cancel(self) -> None:
        super().cancel()
        self._start = None
        self._end = None

    def _build(self, context: ToolContext) -> Command | None:
        """Descarto figuras degeneradas: un clic sin arrastre no es una figura."""
        if self._start is None or self._end is None:
            return None
        if self._start == self._end:
            return None

        shape = Shape(
            kind=self.kind,
            start=self._start,
            end=self._end,
            color=context.color,
            width=context.width,
            filled=self.filled,
        )
        return ShapeCommand(shape)
