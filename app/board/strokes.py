"""Primitivas de dibujo: color, trazo y figura.

Son datos puros e inmutables. No saben dibujarse a sí mismos: de eso se encarga
el renderer. Esa separación es la que me deja serializarlos a JSON para guardar
un proyecto sin arrastrar nada de OpenCV ni de Qt.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

Pixel = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Color:
    """Color RGB. Guardo RGB y convierto a BGR solo al pintar con OpenCV."""

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for channel in (self.r, self.g, self.b):
            if not 0 <= channel <= 255:
                raise ValueError(f"Canal de color fuera de rango: {channel}")

    @property
    def bgr(self) -> tuple[int, int, int]:
        """OpenCV trabaja en BGR; hago la conversión en un solo sitio."""
        return (self.b, self.g, self.r)

    @property
    def rgb(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)

    @property
    def hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    @classmethod
    def from_tuple(cls, values: Sequence[int]) -> Color:
        r, g, b = values
        return cls(int(r), int(g), int(b))

    @classmethod
    def from_hex(cls, value: str) -> Color:
        text = value.lstrip("#")
        if len(text) != 6:
            raise ValueError(f"Color hexadecimal inválido: {value}")
        return cls(int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))

    def to_dict(self) -> dict[str, int]:
        return {"r": self.r, "g": self.g, "b": self.b}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Color:
        return cls(int(data["r"]), int(data["g"]), int(data["b"]))


@dataclass(frozen=True, slots=True)
class Stroke:
    """Trazo a mano alzada: una polilínea con color y grosor."""

    points: tuple[Pixel, ...]
    color: Color
    width: int

    def __post_init__(self) -> None:
        if self.width < 1:
            raise ValueError("El grosor mínimo de un trazo es 1 píxel.")
        if not self.points:
            raise ValueError("Un trazo necesita al menos un punto.")

    @property
    def is_dot(self) -> bool:
        """Un trazo de un solo punto lo pinto como círculo, no como línea."""
        return len(self.points) == 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": [list(p) for p in self.points],
            "color": self.color.to_dict(),
            "width": self.width,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Stroke:
        points = tuple((int(p[0]), int(p[1])) for p in data["points"])
        return cls(points=points, color=Color.from_dict(data["color"]), width=int(data["width"]))


class ShapeKind(Enum):
    """Figuras geométricas que sé dibujar hoy."""

    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ARROW = "arrow"


@dataclass(frozen=True, slots=True)
class Shape:
    """Figura definida por dos puntos: inicio y fin del arrastre."""

    kind: ShapeKind
    start: Pixel
    end: Pixel
    color: Color
    width: int
    filled: bool = False

    def __post_init__(self) -> None:
        if self.width < 1:
            raise ValueError("El grosor mínimo de una figura es 1 píxel.")

    @property
    def radius(self) -> int:
        """Radio para el círculo: distancia entre inicio y fin."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return int(round((dx * dx + dy * dy) ** 0.5))

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "start": list(self.start),
            "end": list(self.end),
            "color": self.color.to_dict(),
            "width": self.width,
            "filled": self.filled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Shape:
        return cls(
            kind=ShapeKind(data["kind"]),
            start=(int(data["start"][0]), int(data["start"][1])),
            end=(int(data["end"][0]), int(data["end"][1])),
            color=Color.from_dict(data["color"]),
            width=int(data["width"]),
            filled=bool(data.get("filled", False)),
        )


# Paleta por defecto de la interfaz. La dejo aquí porque son datos de dibujo,
# no de presentación: el motor también la usa para el color inicial.
DEFAULT_PALETTE: tuple[Color, ...] = (
    Color(24, 28, 36),  # Tinta
    Color(214, 69, 65),  # Rojo
    Color(232, 145, 44),  # Ámbar
    Color(46, 160, 118),  # Verde
    Color(46, 124, 214),  # Azul
    Color(138, 92, 214),  # Violeta
    Color(255, 255, 255),  # Blanco (útil sobre fondos oscuros)
)
