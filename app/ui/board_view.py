"""Vista del lienzo.

Este widget solo pinta y traduce coordenadas. No sabe qué es un gesto ni qué
herramienta está activa: recibe una imagen y la muestra, y reenvía los eventos
del ratón al controlador convertidos a coordenadas de lienzo.

Lo del ratón no es un capricho: me deja usar y probar toda la cadena de dibujo
aunque no haya cámara conectada.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from app.board.strokes import Pixel
from app.ui.theme import PALETTE


class BoardView(QWidget):
    """Muestra el lienzo escalado y manteniendo su proporción."""

    pointerPressed = Signal(tuple)
    pointerMoved = Signal(tuple)
    pointerReleased = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 320)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Guardo una referencia al array mientras el QImage lo esté usando:
        # QImage no copia el buffer y si NumPy libera la memoria antes de
        # repintar, Qt leería memoria inválida.
        self._buffer: np.ndarray | None = None
        self._image: QImage | None = None
        self._canvas_size = (1280, 720)
        self._cursor: Pixel | None = None
        self._cursor_active = False
        self._cursor_radius = 8

    # ---------------------------------------------------------------- datos

    def set_canvas(self, canvas: np.ndarray) -> None:
        """Recibo el lienzo (RGB, uint8, contiguo) y lo preparo para pintar."""
        if canvas.ndim != 3 or canvas.shape[2] != 3:
            raise ValueError("El lienzo debe ser RGB de 3 canales.")

        self._buffer = np.ascontiguousarray(canvas)
        height, width = self._buffer.shape[:2]
        self._canvas_size = (width, height)
        self._image = QImage(
            self._buffer.data, width, height, self._buffer.strides[0], QImage.Format.Format_RGB888
        )
        self.update()

    def set_cursor_position(self, x: int, y: int, drawing: bool) -> None:
        self._cursor = (x, y)
        self._cursor_active = drawing
        self.update()

    def clear_cursor(self) -> None:
        self._cursor = None
        self.update()

    def set_cursor_radius(self, thickness: int) -> None:
        """El cursor crece con el grosor: veo el tamaño real antes de pintar."""
        self._cursor_radius = max(5, thickness)
        self.update()

    # -------------------------------------------------------------- dibujo

    def _target_rect(self) -> QRect:
        """Rectángulo donde cabe el lienzo centrado y sin deformarse."""
        canvas_w, canvas_h = self._canvas_size
        widget_w, widget_h = self.width(), self.height()
        scale = min(widget_w / canvas_w, widget_h / canvas_h)
        width = int(canvas_w * scale)
        height = int(canvas_h * scale)
        return QRect((widget_w - width) // 2, (widget_h - height) // 2, width, height)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - firma de Qt
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PALETTE.deep))

        if self._image is None:
            painter.setPen(QColor(PALETTE.muted))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Pizarra lista")
            painter.end()
            return

        target = self._target_rect()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(target, self._image)

        # Marco sutil para separar el lienzo blanco del fondo oscuro.
        painter.setPen(QPen(QColor(PALETTE.line), 1))
        painter.drawRect(target.adjusted(0, 0, -1, -1))

        self._paint_cursor(painter, target)
        painter.end()

    def _paint_cursor(self, painter: QPainter, target: QRect) -> None:
        """Dibujo el puntero de la mano: relleno si está pintando, hueco si no."""
        if self._cursor is None:
            return

        position = self._canvas_to_widget(self._cursor, target)
        color = QColor(PALETTE.accent if self._cursor_active else PALETTE.muted)
        scale = target.width() / max(1, self._canvas_size[0])
        radius = max(4, int(self._cursor_radius * scale))

        painter.setPen(QPen(color, 2))
        if self._cursor_active:
            painter.setBrush(color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(position, radius, radius)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    # --------------------------------------------------------- coordenadas

    def _canvas_to_widget(self, point: Pixel, target: QRect) -> QPoint:
        canvas_w, canvas_h = self._canvas_size
        x = target.left() + point[0] * target.width() / canvas_w
        y = target.top() + point[1] * target.height() / canvas_h
        return QPoint(int(x), int(y))

    def widget_to_canvas(self, position: QPoint) -> Pixel | None:
        """Convierto un clic del widget a píxeles del lienzo.

        Devuelvo None si el clic cayó fuera del lienzo (en las bandas del
        fondo): dibujar ahí produciría coordenadas negativas.
        """
        target = self._target_rect()
        if not target.contains(position) or target.width() == 0:
            return None

        canvas_w, canvas_h = self._canvas_size
        x = (position.x() - target.left()) * canvas_w / target.width()
        y = (position.y() - target.top()) * canvas_h / target.height()
        return int(x), int(y)

    # ------------------------------------------------------------- eventos

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - firma de Qt
        if event.button() is Qt.MouseButton.LeftButton:
            point = self.widget_to_canvas(event.position().toPoint())
            if point is not None:
                self.pointerPressed.emit(point)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - firma de Qt
        point = self.widget_to_canvas(event.position().toPoint())
        if point is None:
            return
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.pointerMoved.emit(point)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - firma de Qt
        if event.button() is Qt.MouseButton.LeftButton:
            self.pointerReleased.emit()
