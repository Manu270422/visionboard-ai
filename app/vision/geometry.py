"""Cálculos geométricos sobre los landmarks.

Aquí vive toda la matemática de la detección de gestos. La aíslo en funciones
puras (entra datos, sale un número o un bool) porque así puedo probarla con
pytest sin cámara, sin MediaPipe y sin interfaz.
"""

from __future__ import annotations

import math

from app.vision.landmarks import (
    FINGER_LANDMARKS,
    Finger,
    Handedness,
    HandLandmarks,
    LandmarkIndex,
    Point,
)


def distance(a: Point, b: Point) -> float:
    return a.distance_to(b)


def midpoint(a: Point, b: Point) -> Point:
    return Point((a.x + b.x) / 2.0, (a.y + b.y) / 2.0, (a.z + b.z) / 2.0)


def hand_scale(hand: HandLandmarks) -> float:
    """Tamaño de referencia de la mano: muñeca → nudillo del dedo medio.

    Necesito esta escala para que los umbrales funcionen igual si la mano está
    cerca o lejos de la cámara. Sin normalizar, una pinza lejana nunca se
    detectaría porque en píxeles todo es más pequeño.
    """
    scale = distance(hand.wrist, hand.point(LandmarkIndex.MIDDLE_MCP))
    # Evito dividir por cero cuando la detección viene degenerada.
    return max(scale, 1e-6)


def normalized_distance(a: Point, b: Point, hand: HandLandmarks) -> float:
    """Distancia entre dos puntos expresada en 'tamaños de mano'."""
    return distance(a, b) / hand_scale(hand)


def is_finger_extended(hand: HandLandmarks, finger: Finger, margin: float = 0.02) -> bool:
    """Decido si un dedo está estirado.

    Para los cuatro dedos largos comparo alturas: si la punta está por encima
    de la articulación PIP (recordando que en imagen la Y crece hacia abajo),
    el dedo está estirado.

    El pulgar no se puede medir así porque se abre de lado, no hacia arriba.
    Para él comparo cuánto se aleja de la muñeca la punta frente al nudillo IP:
    si la punta está claramente más lejos, el pulgar está abierto. Esto funciona
    con mano izquierda y derecha sin necesitar casos especiales por lateralidad.
    """
    mcp_index, pip_index, tip_index = FINGER_LANDMARKS[finger]
    tip = hand.point(tip_index)
    pip = hand.point(pip_index)

    if finger is Finger.THUMB:
        wrist = hand.wrist
        scale = hand_scale(hand)
        tip_reach = distance(tip, wrist) / scale
        ip_reach = distance(pip, wrist) / scale
        return tip_reach > ip_reach + margin

    return tip.y < pip.y - margin


def extended_fingers(hand: HandLandmarks, margin: float = 0.02) -> dict[Finger, bool]:
    """Estado de los cinco dedos en un solo diccionario tipado."""
    return {finger: is_finger_extended(hand, finger, margin) for finger in Finger}


def pinch_ratio(hand: HandLandmarks) -> float:
    """Distancia pulgar-índice normalizada: cerca de 0 significa pinza cerrada."""
    return normalized_distance(hand.thumb_tip, hand.index_tip, hand)


def thumb_points_up(hand: HandLandmarks, margin: float = 0.15) -> bool:
    """Compruebo que el pulgar apunte hacia arriba, no solo que esté abierto.

    Sin esta verificación un puño de lado se confundiría con un 'pulgar arriba'.
    """
    scale = hand_scale(hand)
    vertical_gap = (hand.wrist.y - hand.thumb_tip.y) / scale
    return vertical_gap > margin


def angle_between(a: Point, vertex: Point, b: Point) -> float:
    """Ángulo en grados del vértice; lo dejo listo para gestos futuros."""
    v1 = (a.x - vertex.x, a.y - vertex.y)
    v2 = (b.x - vertex.x, b.y - vertex.y)
    norm1 = math.hypot(*v1)
    norm2 = math.hypot(*v2)
    if norm1 < 1e-9 or norm2 < 1e-9:
        return 0.0
    cosine = (v1[0] * v2[0] + v1[1] * v2[1]) / (norm1 * norm2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def map_to_canvas(
    point: Point,
    canvas_width: int,
    canvas_height: int,
    margin: float = 0.12,
) -> tuple[int, int]:
    """Mapeo un punto normalizado de la cámara a píxeles de la pizarra.

    Recorto un margen en los bordes porque MediaPipe pierde precisión cerca del
    borde del encuadre: sin este recorte tendría que sacar la mano del cuadro
    para llegar a las esquinas del lienzo.
    """
    span = max(1e-6, 1.0 - 2.0 * margin)
    normalized_x = clamp((point.x - margin) / span, 0.0, 1.0)
    normalized_y = clamp((point.y - margin) / span, 0.0, 1.0)
    x = int(round(normalized_x * (canvas_width - 1)))
    y = int(round(normalized_y * (canvas_height - 1)))
    return x, y


def describe_handedness(handedness: Handedness) -> str:
    """Texto en español para mostrar en la interfaz."""
    return {
        Handedness.LEFT: "Izquierda",
        Handedness.RIGHT: "Derecha",
        Handedness.UNKNOWN: "—",
    }[handedness]
