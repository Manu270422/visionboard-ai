"""Herramientas de trazo libre: lápiz y borrador.

El borrador hereda del lápiz porque hacen lo mismo con distinto color y
grosor. Duplicar la clase entera solo para cambiar dos valores sería el tipo
de código repetido que quiero evitar.
"""

from __future__ import annotations

from app.board.commands import Command, EraseCommand, StrokeCommand
from app.board.strokes import Pixel, Stroke
from app.tools.base import Tool, ToolContext, ToolId


class PencilTool(Tool):
    """Trazo a mano alzada siguiendo la punta del índice."""

    id = ToolId.PENCIL
    label = "Lápiz"
    shortcut = "P"
    continuous = True

    #: Distancia mínima en píxeles entre dos puntos guardados.
    min_distance: int = 2
    #: Tope de puntos por trazo para que un trazo eterno no crezca sin control.
    max_points: int = 4000

    def __init__(self) -> None:
        super().__init__()
        self._points: list[Pixel] = []

    def press(self, point: Pixel, context: ToolContext) -> None:
        self._active = True
        self._points = [point]

    def move(self, point: Pixel, context: ToolContext) -> None:
        """Añado el punto solo si me alejé lo suficiente del anterior.

        Filtrar por distancia me quita el temblor de la mano y reduce mucho el
        tamaño del trazo: a 30 FPS, un dedo quieto generaría 30 puntos por
        segundo en el mismo sitio.
        """
        if not self._active:
            return

        last_x, last_y = self._points[-1]
        if abs(point[0] - last_x) + abs(point[1] - last_y) < self.min_distance:
            return

        if len(self._points) < self.max_points:
            self._points.append(point)

    def release(self, context: ToolContext) -> Command | None:
        if not self._active:
            return None
        command = self._build(context)
        self._active = False
        self._points = []
        return command

    def preview(self, context: ToolContext) -> Command | None:
        if not self._active:
            return None
        return self._build(context)

    def cancel(self) -> None:
        super().cancel()
        self._points = []

    def _build(self, context: ToolContext) -> Command | None:
        """Construyo el comando concreto. Las subclases cambian solo esto."""
        if not self._points:
            return None
        stroke = Stroke(tuple(self._points), context.color, context.width)
        return StrokeCommand(stroke)


class EraserTool(PencilTool):
    """Borra pintando con el color de fondo y un grosor mayor."""

    id = ToolId.ERASER
    label = "Borrador"
    shortcut = "E"

    #: Cuántas veces más grueso que el lápiz.
    multiplier: float = 4.0

    def _build(self, context: ToolContext) -> Command | None:
        if not self._points:
            return None
        width = max(2, int(context.width * self.multiplier))
        stroke = Stroke(tuple(self._points), context.background, width)
        return EraseCommand(stroke)
