"""Comandos de dibujo (patrón Command).

Decisión clave del deshacer/rehacer: **no guardo imágenes**, guardo comandos.

Un historial de bitmaps de 1280x720x3 gasta 2.6 MB por paso; con 300 pasos me
comería 800 MB. Guardando el comando (unos pocos puntos y un color) el
historial pesa kilobytes, y para deshacer simplemente vuelvo a renderizar la
lista desde un lienzo limpio, que en OpenCV cuesta pocos milisegundos.

Como beneficio extra, un comando serializable es exactamente lo que necesito
para guardar el proyecto en disco y para reconocer figuras más adelante.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from app.board import renderer
from app.board.strokes import Color, Shape, Stroke
from app.utils.exceptions import BoardError


class Command(ABC):
    """Una acción aplicable al lienzo, reproducible y serializable."""

    #: Identificador corto que uso al guardar en JSON.
    type_id: str = "command"
    #: Texto para la interfaz ("Deshacer: Trazo").
    label: str = "Acción"

    @abstractmethod
    def apply(self, canvas: np.ndarray) -> None:
        """Aplico la acción sobre el lienzo recibido, en sitio."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serializo el comando para guardarlo en un proyecto."""


class StrokeCommand(Command):
    """Añade un trazo a mano alzada."""

    type_id = "stroke"
    label = "Trazo"

    def __init__(self, stroke: Stroke) -> None:
        self.stroke = stroke

    def apply(self, canvas: np.ndarray) -> None:
        renderer.draw_stroke(canvas, self.stroke)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type_id, "stroke": self.stroke.to_dict()}


class EraseCommand(StrokeCommand):
    """Borra pintando con el color de fondo.

    Hereda de StrokeCommand porque mecánicamente es el mismo trazo; lo separo
    en su propia clase para que el historial muestre "Borrado" y para poder
    cambiar la implementación (máscaras, capas) sin tocar el resto.
    """

    type_id = "erase"
    label = "Borrado"


class ShapeCommand(Command):
    """Añade una figura geométrica."""

    type_id = "shape"
    label = "Figura"

    def __init__(self, shape: Shape) -> None:
        self.shape = shape

    def apply(self, canvas: np.ndarray) -> None:
        renderer.draw_shape(canvas, self.shape)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type_id, "shape": self.shape.to_dict()}


class ClearCommand(Command):
    """Limpia el lienzo completo.

    Al ser un comando más, limpiar también se puede deshacer: el lienzo se
    reconstruye reproduciendo los comandos anteriores.
    """

    type_id = "clear"
    label = "Limpiar"

    def __init__(self, background: Color) -> None:
        self.background = background

    def apply(self, canvas: np.ndarray) -> None:
        renderer.fill(canvas, self.background)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type_id, "background": self.background.to_dict()}


def command_from_dict(data: dict[str, Any]) -> Command:
    """Reconstruyo un comando desde JSON.

    Uso una tabla explícita de tipos y no `eval` ni importaciones dinámicas:
    un archivo de proyecto es entrada no confiable y no quiero que pueda
    ejecutar código arbitrario en mi máquina.
    """
    if not isinstance(data, dict):
        raise BoardError("Cada comando del proyecto debe ser un objeto JSON.")

    type_id = data.get("type")
    try:
        if type_id == StrokeCommand.type_id:
            return StrokeCommand(Stroke.from_dict(data["stroke"]))
        if type_id == EraseCommand.type_id:
            return EraseCommand(Stroke.from_dict(data["stroke"]))
        if type_id == ShapeCommand.type_id:
            return ShapeCommand(Shape.from_dict(data["shape"]))
        if type_id == ClearCommand.type_id:
            return ClearCommand(Color.from_dict(data["background"]))
    except (KeyError, TypeError, ValueError) as error:
        raise BoardError(f"Comando '{type_id}' con datos inválidos: {error}") from error

    raise BoardError(f"Tipo de comando desconocido: {type_id!r}")
