"""Contrato de las herramientas de dibujo (patrón Strategy).

Toda herramienta recibe los mismos tres eventos —presionar, mover, soltar— y
devuelve, como mucho, un `Command`. El controlador no sabe si está usando el
lápiz o el rectángulo: solo reenvía eventos y ejecuta lo que le devuelvan.

Gracias a esto, añadir "flecha", "texto" o "regla" más adelante no toca el
controlador ni la pizarra: es una clase nueva registrada en el registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from app.board.commands import Command
from app.board.strokes import Color, Pixel


class ToolId(Enum):
    """Identificadores estables de herramienta (los uso en UI y en atajos)."""

    PENCIL = "pencil"
    ERASER = "eraser"
    SELECTOR = "selector"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ARROW = "arrow"


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Lo que la herramienta necesita saber del entorno al dibujar.

    Lo paso como parámetro en cada evento en lugar de guardarlo dentro de la
    herramienta: así el color y el grosor pueden cambiar a mitad de sesión sin
    tener que sincronizar estado duplicado.
    """

    color: Color
    width: int
    background: Color
    canvas_size: tuple[int, int]

    def with_width(self, width: int) -> ToolContext:
        return ToolContext(self.color, max(1, width), self.background, self.canvas_size)


class Tool(ABC):
    """Herramienta de dibujo. Mantiene el estado del gesto en curso."""

    id: ToolId
    label: str
    shortcut: str = ""
    #: Si es True, el puntero pinta mientras se mueve (lápiz, borrador).
    continuous: bool = True

    def __init__(self) -> None:
        self._active = False

    @property
    def is_active(self) -> bool:
        """True si hay un trazo o figura empezado y sin soltar."""
        return self._active

    @abstractmethod
    def press(self, point: Pixel, context: ToolContext) -> None:
        """Empiezo la interacción en este punto."""

    @abstractmethod
    def move(self, point: Pixel, context: ToolContext) -> None:
        """Continúo la interacción."""

    @abstractmethod
    def release(self, context: ToolContext) -> Command | None:
        """Termino y devuelvo el comando definitivo, o None si no hay nada."""

    def preview(self, context: ToolContext) -> Command | None:
        """Comando temporal para mostrar el trabajo en curso. Opcional."""
        return None

    def cancel(self) -> None:
        """Aborto la interacción sin producir comando (mano fuera de cuadro)."""
        self._active = False

    def __repr__(self) -> str:  # pragma: no cover - depuración
        return f"{type(self).__name__}(id={self.id.value})"
