"""Reconocimiento de figuras a partir de trazos a mano alzada.

La idea es la que ya sugería el README: un `Stroke` es solo una lista de
puntos, y un `Shape` es una figura perfecta con dos puntos de control. Si
puedo medir qué tan "recto", "cerrado" o "circular" es un trazo, puedo decidir
si el usuario quiso dibujar una línea, un rectángulo o un círculo y devolver
la figura equivalente. No entreno nada: con trazos de unos pocos cientos de
puntos, ajustar geometría clásica con OpenCV es más rápido, más predecible y
no arrastra ninguna dependencia nueva.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.board.strokes import Pixel, Shape, ShapeKind, Stroke

#: Cuánto puede desviarse un trazo de una recta perfecta (proporción de la
#: diagonal de su cuadro delimitador) para seguir aceptándose como línea.
_LINE_TOLERANCE = 0.045
#: Qué tan cerca deben quedar el primer y el último punto (proporción de esa
#: misma diagonal) para tratar el trazo como una figura cerrada.
_CLOSURE_TOLERANCE = 0.18
#: Circularidad mínima (4·pi·área/perímetro², 1.0 = círculo perfecto).
_CIRCULARITY_MIN = 0.75
#: Con menos puntos que esto no hay forma fiable de medir nada: lo dejo tal cual.
_MIN_POINTS = 6


def recognize_shape(stroke: Stroke) -> Shape | None:
    """Devuelvo la figura perfecta que sugiere el trazo, o None si no hay ninguna.

    Prefiero un falso negativo (dejar un trazo válido sin corregir) a un falso
    positivo (deformar un dibujo intencional): por eso cada prueba exige un
    ajuste bastante bueno antes de aceptar una figura.
    """
    if len(stroke.points) < _MIN_POINTS or stroke.is_dot:
        return None

    points = np.array(stroke.points, dtype=np.float32)
    diagonal = _bbox_diagonal(points)
    if diagonal < 1e-6:
        return None

    line = _try_line(points, stroke, diagonal)
    if line is not None:
        return line

    if not _is_closed(points, diagonal):
        return None

    return _try_circle(points, stroke) or _try_rectangle(points, stroke)


def _bbox_diagonal(points: np.ndarray) -> float:
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    return float(np.hypot(*(maxs - mins)))


def _try_line(points: np.ndarray, stroke: Stroke, diagonal: float) -> Shape | None:
    """Ajusto una recta y mido cuánto se aleja el trazo de ella.

    `cv2.fitLine` minimiza la distancia perpendicular total, así que es la
    referencia correcta para "qué tan recto" es el trazo sin que importe la
    dirección en la que el usuario movió la mano.
    """
    vx, vy, x0, y0 = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    direction = np.array([vx, vy], dtype=np.float32)
    origin = np.array([x0, y0], dtype=np.float32)

    offsets = points - origin
    projections = offsets @ direction
    closest = origin + np.outer(projections, direction)
    residuals = np.linalg.norm(points - closest, axis=1)

    if float(residuals.max()) > _LINE_TOLERANCE * diagonal:
        return None

    start = points[int(np.argmin(projections))]
    end = points[int(np.argmax(projections))]
    return Shape(
        kind=ShapeKind.LINE,
        start=_to_pixel(start),
        end=_to_pixel(end),
        color=stroke.color,
        width=stroke.width,
    )


def _is_closed(points: np.ndarray, diagonal: float) -> bool:
    """Un trazo "cerrado" es el único candidato a círculo o rectángulo.

    Nadie cierra un círculo o un rectángulo a mano con precisión de píxel,
    pero sí deja los extremos mucho más cerca entre sí que del resto del
    trazo: esa es la señal que separo aquí de una simple curva abierta.
    """
    gap = float(np.linalg.norm(points[0] - points[-1]))
    return gap <= _CLOSURE_TOLERANCE * diagonal


def _try_circle(points: np.ndarray, stroke: Stroke) -> Shape | None:
    contour = points.reshape(-1, 1, 2)
    area = abs(cv2.contourArea(contour))
    perimeter = cv2.arcLength(contour, True)
    if perimeter < 1e-6:
        return None

    circularity = 4.0 * np.pi * area / (perimeter * perimeter)
    if circularity < _CIRCULARITY_MIN:
        return None

    (cx, cy), radius = cv2.minEnclosingCircle(contour)
    center = (int(round(cx)), int(round(cy)))
    edge = (int(round(cx + radius)), int(round(cy)))
    return Shape(kind=ShapeKind.CIRCLE, start=center, end=edge, color=stroke.color, width=stroke.width)


def _try_rectangle(points: np.ndarray, stroke: Stroke) -> Shape | None:
    """Simplifico el contorno y acepto solo lo que quede en 4 esquinas.

    `approxPolyDP` con un épsilon relativo al perímetro es la forma estándar
    de OpenCV de preguntar "¿cuántas esquinas tiene esto de verdad?": filtra
    el temblor de la mano sin necesitar un umbral fijo en píxeles.
    """
    contour = points.reshape(-1, 1, 2)
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)
    if len(approx) != 4 or not cv2.isContourConvex(approx):
        return None

    xs = approx[:, 0, 0]
    ys = approx[:, 0, 1]
    start = (int(round(float(xs.min()))), int(round(float(ys.min()))))
    end = (int(round(float(xs.max()))), int(round(float(ys.max()))))
    return Shape(kind=ShapeKind.RECTANGLE, start=start, end=end, color=stroke.color, width=stroke.width)


def _to_pixel(point: np.ndarray) -> Pixel:
    return (int(round(float(point[0]))), int(round(float(point[1]))))
