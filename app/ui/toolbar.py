"""Barra lateral de herramientas.

Widget de presentación puro: muestra botones y emite señales. No conoce la
pizarra ni ejecuta comandos; quien decide qué pasa al pulsar es el controlador.
Mantener esta frontera es lo que evita que la lógica se disuelva dentro de los
widgets.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.board.strokes import DEFAULT_PALETTE, Color
from app.tools.base import ToolId
from app.ui.theme import PALETTE, RAIL_WIDTH

# Glifos de texto en vez de archivos de icono: cero dependencias de assets y
# se ven nítidos en cualquier resolución.
_TOOL_GLYPHS: dict[ToolId, tuple[str, str]] = {
    ToolId.PENCIL: ("✎", "Lápiz (P)"),
    ToolId.ERASER: ("⌫", "Borrador (E)"),
    ToolId.SELECTOR: ("⬚", "Selección (S)"),
    ToolId.LINE: ("╱", "Línea (L)"),
    ToolId.RECTANGLE: ("▭", "Rectángulo (R)"),
    ToolId.CIRCLE: ("◯", "Círculo (C)"),
    ToolId.ARROW: ("↗", "Flecha (F)"),
}


class ToolRail(QFrame):
    """Columna vertical con las herramientas de dibujo."""

    toolSelected = Signal(object)  # ToolId

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rail")
        self.setFixedWidth(RAIL_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(8)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[ToolId, QPushButton] = {}

        for tool_id, (glyph, tooltip) in _TOOL_GLYPHS.items():
            button = QPushButton(glyph)
            button.setProperty("role", "tool")
            button.setCheckable(True)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _checked, t=tool_id: self.toolSelected.emit(t))
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._group.addButton(button)
            self._buttons[tool_id] = button

        layout.addStretch(1)
        self.select(ToolId.PENCIL)

    def select(self, tool_id: ToolId) -> None:
        """Marco la herramienta activa sin reemitir la señal.

        Bloqueo las señales a propósito: si el controlador me llama para
        sincronizar el estado, no quiero que eso dispare otro cambio y entre
        en un bucle.
        """
        button = self._buttons.get(tool_id)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(True)
        button.blockSignals(False)


class ColorPalette(QWidget):
    """Rejilla de colores seleccionables."""

    colorSelected = Signal(object)  # Color

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for position, color in enumerate(DEFAULT_PALETTE):
            button = QPushButton()
            button.setProperty("role", "swatch")
            button.setCheckable(True)
            button.setToolTip(color.hex)
            # El color va en línea porque es dato, no tema. Repito aquí la
            # forma del botón porque una hoja de estilos en línea reemplaza
            # por completo la regla global del rol "swatch".
            # Solo pinto el color: la forma y el tamaño vienen del rol
            # "swatch" del tema, para no repetir la misma medida en dos sitios.
            button.setStyleSheet(
                f"QPushButton {{ background-color: {color.hex}; }}"
                f"QPushButton:checked {{ border: 2px solid {PALETTE.accent}; }}"
            )
            button.clicked.connect(lambda _checked, c=color: self.colorSelected.emit(c))
            layout.addWidget(
                button, position // 4, position % 4, alignment=Qt.AlignmentFlag.AlignLeft
            )
            self._group.addButton(button)
            self._buttons[color.hex] = button

        self.select(DEFAULT_PALETTE[0])

    def select(self, color: Color) -> None:
        button = self._buttons.get(color.hex)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(True)
        button.blockSignals(False)


def section_label(text: str) -> QLabel:
    """Etiqueta de sección con el estilo del panel."""
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label
