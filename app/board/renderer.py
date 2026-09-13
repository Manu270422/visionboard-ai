"""Rasterización de primitivas sobre un lienzo NumPy.

Este módulo es el único que sabe pintar píxeles. Usa OpenCV, pero **no** usa
Qt: el lienzo es un `np.ndarray` normal. Gracias a eso puedo exportar a PNG,
probar el dibujo con pytest y, si algún día cambio de framework gráfico, la
interfaz es lo único que reescribo.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.board.strokes import Color, Shape, ShapeKind, Stroke

# Trabajo el lienzo en RGB (no BGR) porque es lo que Qt espera al construir el
# QImage. Convierto a BGR solo al escribir el PNG con OpenCV.
_LINE_TYPE = cv2.LINE_AA


def new_canvas(width: int, height: int, background: Color) -> np.ndarray:
    """Creo un lienzo RGB uint8 relleno del color de fondo."""
    if width < 1 or height < 1:
        raise ValueError("El lienzo necesita ancho y alto positivos.")
    canvas = np.empty((height, width, 3), dtype=np.uint8)
    canvas[:] = background.rgb
    return canvas


def fill(canvas: np.ndarray, color: Color) -> None:
    """Relleno el lienzo en sitio; lo usa el comando de limpiar."""
    canvas[:] = color.rgb


def draw_stroke(canvas: np.ndarray, stroke: Stroke) -> None:
    """Pinto una polilínea con extremos redondeados.

    Uso `cv2.polylines` en vez de un bucle de `cv2.line` porque hace el
    recorrido en C: con trazos largos la diferencia se nota en los FPS.
    Los círculos en los vértices evitan las muescas en los cambios de dirección.
    """
    color = stroke.color.rgb

    if stroke.is_dot:
        cv2.circle(canvas, stroke.points[0], max(1, stroke.width // 2), color, -1, _LINE_TYPE)
        return

    points = np.array(stroke.points, dtype=np.int32).reshape(-1, 1, 2)
    cv2.polylines(canvas, [points], False, color, stroke.width, _LINE_TYPE)

    radius = stroke.width // 2
    if radius >= 1:
        cv2.circle(canvas, stroke.points[0], radius, color, -1, _LINE_TYPE)
        cv2.circle(canvas, stroke.points[-1], radius, color, -1, _LINE_TYPE)


def draw_shape(canvas: np.ndarray, shape: Shape) -> None:
    """Pinto una figura geométrica según su tipo."""
    color = shape.color.rgb
    thickness = -1 if shape.filled else shape.width

    if shape.kind is ShapeKind.LINE:
        cv2.line(canvas, shape.start, shape.end, color, shape.width, _LINE_TYPE)
    elif shape.kind is ShapeKind.RECTANGLE:
        cv2.rectangle(canvas, shape.start, shape.end, color, thickness, _LINE_TYPE)
    elif shape.kind is ShapeKind.CIRCLE:
        # Tomo el punto inicial como centro y el arrastre como radio: es el
        # gesto más natural cuando dibujo con el dedo en el aire.
        cv2.circle(canvas, shape.start, max(1, shape.radius), color, thickness, _LINE_TYPE)
    elif shape.kind is ShapeKind.ARROW:
        cv2.arrowedLine(
            canvas, shape.start, shape.end, color, shape.width, _LINE_TYPE, tipLength=0.25
        )
    else:  # pragma: no cover - el Enum no deja llegar aquí
        raise ValueError(f"Figura no soportada: {shape.kind}")


def to_bgr(canvas: np.ndarray) -> np.ndarray:
    """Convierto a BGR para guardar con OpenCV."""
    return cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR)
