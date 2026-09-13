"""Traducción de gesto → acción de la pizarra.

Mantengo este mapeo fuera del clasificador y fuera de la pizarra: el
clasificador no debe saber qué hace la aplicación con un puño, y la pizarra no
debe saber que existen las manos. Este módulo es el contrato entre ambos, y por
eso el mapeo se puede cambiar en caliente sin tocar ninguno de los dos.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from types import MappingProxyType

from app.gestures.gesture_types import Gesture


class BoardAction(Enum):
    """Qué hace la pizarra ante un gesto ya confirmado."""

    IDLE = "idle"  # No hay interacción; suelto cualquier trazo en curso.
    DRAW = "draw"  # Dibujo con la herramienta activa.
    HOVER = "hover"  # Muevo el cursor sin pintar (modo selección).
    ERASE = "erase"  # Activo el borrador temporalmente.
    CONFIRM = "confirm"  # Confirmo la acción pendiente.
    PAUSE = "pause"  # Congelo la interacción.
    ADJUST = "adjust"  # Ajusto el grosor con la distancia de la pinza.


# Mapeo por defecto. Lo dejo inmutable para que nadie lo modifique por accidente
# desde otro módulo; quien quiera otro comportamiento pasa su propio diccionario.
DEFAULT_ACTION_MAP: Mapping[Gesture, BoardAction] = MappingProxyType(
    {
        Gesture.NONE: BoardAction.IDLE,
        Gesture.DRAW: BoardAction.DRAW,
        Gesture.SELECT: BoardAction.HOVER,
        Gesture.FIST: BoardAction.ERASE,
        Gesture.OPEN_PALM: BoardAction.PAUSE,
        Gesture.THUMBS_UP: BoardAction.CONFIRM,
        Gesture.PINCH: BoardAction.ADJUST,
    }
)


def resolve_action(
    gesture: Gesture,
    action_map: Mapping[Gesture, BoardAction] | None = None,
) -> BoardAction:
    """Devuelvo la acción del gesto; si no está mapeado, no hago nada."""
    mapping = action_map or DEFAULT_ACTION_MAP
    return mapping.get(gesture, BoardAction.IDLE)


# Acciones durante las cuales el puntero debe pintar en el lienzo.
DRAWING_ACTIONS: frozenset[BoardAction] = frozenset({BoardAction.DRAW, BoardAction.ERASE})
