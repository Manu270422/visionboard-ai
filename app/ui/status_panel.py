"""Panel lateral derecho: estado del seguimiento y acciones del lienzo.

Agrupo aquí todo lo que responde a la pregunta "¿qué está viendo la cámara
ahora mismo?": el preview con los landmarks, el gesto reconocido y los FPS.
En una aplicación de visión por computador ese estado no es decoración: sin él
no sé si la aplicación no responde o si simplemente no me está viendo la mano.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal, SignalInstance
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.board.strokes import Color
from app.gestures.gesture_types import GESTURE_ICONS, Gesture, describe
from app.ui.theme import PALETTE, PANEL_WIDTH, PREVIEW_HEIGHT
from app.ui.toolbar import ColorPalette, section_label


class StatusPanel(QFrame):
    """Preview de cámara, gesto detectado, grosor, colores y acciones."""

    colorSelected = Signal(object)  # Color
    thicknessChanged = Signal(int)
    undoRequested = Signal()
    redoRequested = Signal()
    clearRequested = Signal()
    aiCleanRequested = Signal()
    saveRequested = Signal()
    exportRequested = Signal()
    landmarksToggled = Signal(bool)
    previewToggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setFixedWidth(PANEL_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addWidget(section_label("Cámara"))
        self._preview = QLabel("Iniciando cámara…")
        self._preview.setObjectName("preview")
        self._preview.setFixedHeight(PREVIEW_HEIGHT)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._preview)

        self._camera_state = QLabel("Conectando…")
        self._camera_state.setObjectName("metric")
        layout.addWidget(self._camera_state)

        layout.addWidget(section_label("Gesto"))
        gesture_row = QHBoxLayout()
        gesture_row.setSpacing(10)
        self._glyph = QLabel("·")
        self._glyph.setObjectName("gestureGlyph")
        self._name = QLabel("Sin mano")
        self._name.setObjectName("gestureName")
        gesture_row.addWidget(self._glyph)
        gesture_row.addWidget(self._name, 1)
        layout.addLayout(gesture_row)

        self._metrics = QLabel("— FPS")
        self._metrics.setObjectName("metric")
        layout.addWidget(self._metrics)

        layout.addWidget(section_label("Color"))
        self._palette = ColorPalette()
        self._palette.colorSelected.connect(self.colorSelected)
        layout.addWidget(self._palette)

        layout.addWidget(section_label("Grosor"))
        thickness_row = QHBoxLayout()
        self._thickness = QSlider(Qt.Orientation.Horizontal)
        self._thickness.setRange(1, 48)
        self._thickness.setValue(6)
        self._thickness.valueChanged.connect(self.thicknessChanged)
        self._thickness_value = QLabel("6 px")
        self._thickness_value.setObjectName("metric")
        thickness_row.addWidget(self._thickness, 1)
        thickness_row.addWidget(self._thickness_value)
        layout.addLayout(thickness_row)

        layout.addWidget(section_label("Acciones"))
        self._undo = self._action_button("Deshacer", self.undoRequested)
        self._redo = self._action_button("Rehacer", self.redoRequested)
        history_row = QHBoxLayout()
        history_row.addWidget(self._undo)
        history_row.addWidget(self._redo)
        layout.addLayout(history_row)

        files_row = QHBoxLayout()
        files_row.addWidget(self._action_button("Guardar", self.saveRequested))
        files_row.addWidget(self._action_button("Exportar PNG", self.exportRequested))
        layout.addLayout(files_row)

        layout.addWidget(self._action_button("Limpiar pizarra", self.clearRequested))

        layout.addWidget(section_label("IA"))
        ai_button = self._action_button("Reconocer figura ✨", self.aiCleanRequested)
        ai_button.setToolTip(
            "Selecciona un área con la herramienta de selección y pulsa aquí:\n"
            "cambio cada trazo torcido de esa zona por la figura perfecta que sugiere."
        )
        layout.addWidget(ai_button)

        layout.addWidget(section_label("Vista"))
        self._show_landmarks = QCheckBox("Mostrar landmarks")
        self._show_landmarks.setChecked(True)
        self._show_landmarks.toggled.connect(self.landmarksToggled)
        layout.addWidget(self._show_landmarks)

        self._show_preview = QCheckBox("Mostrar cámara")
        self._show_preview.setChecked(True)
        self._show_preview.toggled.connect(self.previewToggled)
        layout.addWidget(self._show_preview)

        layout.addStretch(1)
        self.set_history_state(False, False)

    def _action_button(self, text: str, signal: SignalInstance) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(signal)
        return button

    # ----------------------------------------------------------- entradas

    def show_frame(self, frame_rgb: np.ndarray) -> None:
        """Muestro el frame de la cámara escalado al ancho del panel.

        Construyo el QPixmap sobre una copia contigua porque el array original
        pertenece al hilo de visión y puede ser reemplazado en cualquier
        momento; sin la copia Qt podría pintar memoria ya reutilizada.
        """
        buffer = np.ascontiguousarray(frame_rgb)
        height, width = buffer.shape[:2]
        image = QImage(
            buffer.data, width, height, buffer.strides[0], QImage.Format.Format_RGB888
        ).copy()

        self._preview.setPixmap(
            QPixmap.fromImage(image).scaled(
                self._preview.width(),
                self._preview.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def clear_frame(self, message: str = "Cámara oculta") -> None:
        self._preview.clear()
        self._preview.setText(message)

    def set_gesture(self, gesture: Gesture) -> None:
        self._glyph.setText(GESTURE_ICONS.get(gesture, "·"))
        self._name.setText(describe(gesture))
        color = PALETTE.muted if gesture is Gesture.NONE else PALETTE.accent
        self._glyph.setStyleSheet(f"color: {color};")

    def set_metrics(self, fps: float, process_ms: float) -> None:
        self._metrics.setText(f"{fps:.0f} FPS · {process_ms:.0f} ms por frame")

    def set_camera_state(self, text: str, *, ok: bool = True) -> None:
        self._camera_state.setText(text)
        self._camera_state.setStyleSheet(f"color: {PALETTE.muted if ok else PALETTE.alert};")

    def set_thickness(self, value: int) -> None:
        """Sincronizo el slider cuando el grosor cambia por gesto de pinza."""
        self._thickness.blockSignals(True)
        self._thickness.setValue(value)
        self._thickness.blockSignals(False)
        self._thickness_value.setText(f"{value} px")

    def set_color(self, color: Color) -> None:
        self._palette.select(color)

    def set_history_state(self, can_undo: bool, can_redo: bool) -> None:
        self._undo.setEnabled(can_undo)
        self._redo.setEnabled(can_redo)
