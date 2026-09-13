"""Fixtures compartidas de las pruebas.

Fabrico manos sintéticas con coordenadas escritas a mano. Es la pieza que hace
testeable todo el módulo de gestos: no necesito cámara, ni MediaPipe, ni una
mano real para verificar que un puño se reconoce como puño.
"""

from __future__ import annotations

import pytest

from app.board.canvas import DrawingBoard
from app.board.strokes import Color
from app.config.settings import BoardSettings
from app.tools.base import ToolContext
from app.vision.landmarks import Handedness, HandLandmarks, LandmarkIndex

# Muñeca y nudillo del dedo medio definen la escala de referencia (0.25).
_WRIST = (0.50, 0.90)
_MIDDLE_MCP = (0.50, 0.65)

# Posición horizontal de cada dedo largo.
_COLUMN_X = {"index": 0.44, "middle": 0.50, "ring": 0.56, "pinky": 0.62}


def _long_finger(name: str, extended: bool) -> list[tuple[float, float]]:
    """Devuelvo (mcp, pip, dip, tip) de un dedo largo.

    Estirado: la punta queda por encima de la PIP. Recogido: por debajo.
    Es exactamente la condición que evalúa `is_finger_extended`.
    """
    x = _COLUMN_X[name]
    mcp = (x, 0.65)
    pip = (x, 0.55)
    if extended:
        return [mcp, pip, (x, 0.48), (x, 0.42)]
    return [mcp, pip, (x, 0.58), (x, 0.62)]


def _thumb(extended: bool) -> list[tuple[float, float]]:
    """Devuelvo (cmc, mcp, ip, tip) del pulgar.

    Recogido lo cruzo sobre la palma, de forma que la punta queda MÁS CERCA de
    la muñeca que la articulación IP; abierto, más lejos.
    """
    if extended:
        return [(0.44, 0.85), (0.40, 0.80), (0.36, 0.75), (0.30, 0.70)]
    return [(0.46, 0.84), (0.44, 0.78), (0.42, 0.72), (0.46, 0.76)]


def make_hand(
    *,
    thumb: bool = False,
    index: bool = False,
    middle: bool = False,
    ring: bool = False,
    pinky: bool = False,
    handedness: Handedness = Handedness.RIGHT,
    score: float = 0.95,
) -> HandLandmarks:
    """Construyo una mano de 21 landmarks con los dedos que le pida."""
    points: list[tuple[float, float]] = [_WRIST]
    points += _thumb(thumb)
    points += _long_finger("index", index)
    points += _long_finger("middle", middle)
    points += _long_finger("ring", ring)
    points += _long_finger("pinky", pinky)

    # Corrijo el nudillo del dedo medio para fijar la escala de referencia.
    points[int(LandmarkIndex.MIDDLE_MCP)] = _MIDDLE_MCP
    return HandLandmarks.from_iterable(points, handedness=handedness, score=score)


def make_pinch_hand() -> HandLandmarks:
    """Mano en pinza: punta del pulgar y del índice prácticamente juntas."""
    hand = make_hand(index=True)
    points = list(hand.points)
    thumb_tip = points[int(LandmarkIndex.INDEX_TIP)]
    points[int(LandmarkIndex.THUMB_TIP)] = type(thumb_tip)(0.445, 0.43, 0.0)
    return HandLandmarks(tuple(points), hand.handedness, hand.score)


@pytest.fixture
def board() -> DrawingBoard:
    """Pizarra pequeña para que las pruebas corran rápido."""
    return DrawingBoard(BoardSettings(width=640, height=480, history_limit=50))


@pytest.fixture
def context(board: DrawingBoard) -> ToolContext:
    return ToolContext(
        color=Color(10, 20, 30),
        width=4,
        background=board.background,
        canvas_size=board.size,
    )
