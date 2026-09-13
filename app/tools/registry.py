"""Registro de herramientas.

Guardo *fábricas* y no instancias sueltas para que cada herramienta se cree
limpia y para poder registrar herramientas nuevas en tiempo de ejecución.
El resto de la aplicación pide herramientas por `ToolId` y nunca importa las
clases concretas: así la interfaz no depende de la implementación.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from app.board.strokes import ShapeKind
from app.tools.base import Tool, ToolId
from app.tools.freehand import EraserTool, PencilTool
from app.tools.selector import SelectorTool
from app.tools.shapes import ShapeTool

ToolFactory = Callable[[], Tool]


class ToolRegistry:
    """Contenedor de herramientas: crea una instancia y la cachea por id."""

    def __init__(self) -> None:
        self._factories: dict[ToolId, ToolFactory] = {}
        self._instances: dict[ToolId, Tool] = {}

    def register(self, tool_id: ToolId, factory: ToolFactory) -> None:
        self._factories[tool_id] = factory
        self._instances.pop(tool_id, None)

    def get(self, tool_id: ToolId) -> Tool:
        """Devuelvo siempre la misma instancia por herramienta.

        Mantener la instancia me conserva su estado (por ejemplo, la selección
        activa) cuando cambio de herramienta y vuelvo.
        """
        if tool_id not in self._instances:
            if tool_id not in self._factories:
                raise KeyError(f"Herramienta no registrada: {tool_id}")
            self._instances[tool_id] = self._factories[tool_id]()
        return self._instances[tool_id]

    def available(self) -> tuple[ToolId, ...]:
        return tuple(self._factories)

    def __iter__(self) -> Iterator[Tool]:
        return (self.get(tool_id) for tool_id in self._factories)

    def __contains__(self, tool_id: object) -> bool:
        return tool_id in self._factories


def build_default_registry() -> ToolRegistry:
    """Registro las herramientas de la versión 1 en el orden de la barra."""
    registry = ToolRegistry()
    registry.register(ToolId.PENCIL, PencilTool)
    registry.register(ToolId.ERASER, EraserTool)
    registry.register(ToolId.SELECTOR, SelectorTool)
    registry.register(ToolId.LINE, lambda: ShapeTool(ShapeKind.LINE))
    registry.register(ToolId.RECTANGLE, lambda: ShapeTool(ShapeKind.RECTANGLE))
    registry.register(ToolId.CIRCLE, lambda: ShapeTool(ShapeKind.CIRCLE))
    registry.register(ToolId.ARROW, lambda: ShapeTool(ShapeKind.ARROW))
    return registry
