"""Catálogo de gestos reconocidos.

Uso un Enum y no cadenas de texto porque quiero que un gesto mal escrito falle
al importar, no en tiempo de ejecución en mitad de una sesión de dibujo.
"""

from __future__ import annotations

from enum import Enum


class Gesture(Enum):
    """Gestos que la aplicación entiende hoy."""

    NONE = "none"  # No hay mano o no reconozco la pose.
    DRAW = "draw"  # ☝️ Índice levantado.
    SELECT = "select"  # ✌️ Índice + medio.
    FIST = "fist"  # ✊ Puño.
    OPEN_PALM = "open_palm"  # 🖐️ Mano abierta.
    THUMBS_UP = "thumbs_up"  # 👍 Pulgar arriba.
    PINCH = "pinch"  # 🤏 Pinza índice-pulgar.


# Etiquetas para la interfaz. Las separo del Enum para poder traducirlas o
# cambiarlas sin tocar la lógica que compara gestos.
GESTURE_LABELS: dict[Gesture, str] = {
    Gesture.NONE: "Sin mano",
    Gesture.DRAW: "Dibujar",
    Gesture.SELECT: "Seleccionar",
    Gesture.FIST: "Borrador",
    Gesture.OPEN_PALM: "Pausa",
    Gesture.THUMBS_UP: "Confirmar",
    Gesture.PINCH: "Grosor",
}

GESTURE_ICONS: dict[Gesture, str] = {
    Gesture.NONE: "·",
    Gesture.DRAW: "☝",
    Gesture.SELECT: "✌",
    Gesture.FIST: "✊",
    Gesture.OPEN_PALM: "🖐",
    Gesture.THUMBS_UP: "👍",
    Gesture.PINCH: "🤏",
}


def describe(gesture: Gesture) -> str:
    """Texto listo para mostrar en el panel de estado."""
    return GESTURE_LABELS.get(gesture, gesture.value)
