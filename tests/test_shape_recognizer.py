"""Pruebas del reconocimiento de figuras (Fase 8)."""

from __future__ import annotations

import math

from app.ai.shape_recognizer import recognize_shape
from app.board.strokes import Color, ShapeKind, Stroke

ROJO = Color(255, 0, 0)


def _linea_temblorosa() -> Stroke:
    """Una línea casi recta de (10,10) a (200,12), con un temblor mínimo."""
    points = tuple((x, 10 + (1 if x % 20 == 0 else 0)) for x in range(10, 201, 5))
    return Stroke(points, ROJO, 4)


def _circulo(radius: float = 60.0, center: tuple[int, int] = (150, 150)) -> Stroke:
    points = tuple(
        (
            int(round(center[0] + radius * math.cos(t))),
            int(round(center[1] + radius * math.sin(t))),
        )
        for t in (i * 2 * math.pi / 40 for i in range(40))
    )
    return Stroke(points, ROJO, 4)


def _rectangulo(left: int = 20, top: int = 20, right: int = 220, bottom: int = 140) -> Stroke:
    top_edge = [(x, top) for x in range(left, right, 10)]
    right_edge = [(right, y) for y in range(top, bottom, 10)]
    bottom_edge = [(x, bottom) for x in range(right, left, -10)]
    left_edge = [(left, y) for y in range(bottom, top, -10)]
    points = tuple(top_edge + right_edge + bottom_edge + left_edge + [(left, top)])
    return Stroke(points, ROJO, 4)


def _garabato() -> Stroke:
    """Un zigzag irregular que no debería parecerse a ninguna figura."""
    points = ((10, 10), (40, 90), (20, 40), (90, 100), (15, 60), (100, 15), (30, 80))
    return Stroke(points, ROJO, 4)


class TestReconocimientoDeLinea:
    def test_linea_recta_se_reconoce(self) -> None:
        shape = recognize_shape(_linea_temblorosa())
        assert shape is not None
        assert shape.kind is ShapeKind.LINE

    def test_conserva_color_y_grosor(self) -> None:
        shape = recognize_shape(_linea_temblorosa())
        assert shape is not None
        assert shape.color == ROJO
        assert shape.width == 4


class TestReconocimientoDeCirculo:
    def test_circulo_se_reconoce(self) -> None:
        shape = recognize_shape(_circulo())
        assert shape is not None
        assert shape.kind is ShapeKind.CIRCLE

    def test_radio_es_razonable(self) -> None:
        shape = recognize_shape(_circulo(radius=60.0))
        assert shape is not None
        assert 50 <= shape.radius <= 70


class TestReconocimientoDeRectangulo:
    def test_rectangulo_se_reconoce(self) -> None:
        shape = recognize_shape(_rectangulo())
        assert shape is not None
        assert shape.kind is ShapeKind.RECTANGLE


class TestSinFigura:
    def test_garabato_no_se_reconoce(self) -> None:
        assert recognize_shape(_garabato()) is None

    def test_trazo_muy_corto_no_se_reconoce(self) -> None:
        stroke = Stroke(((0, 0), (5, 5), (10, 10)), ROJO, 4)
        assert recognize_shape(stroke) is None

    def test_punto_no_se_reconoce(self) -> None:
        stroke = Stroke(((5, 5),), ROJO, 4)
        assert recognize_shape(stroke) is None
