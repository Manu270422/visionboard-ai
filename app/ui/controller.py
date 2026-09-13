"""Controlador de la aplicación.

Aquí se cierra el circuito: recibo paquetes del hilo de visión, los convierto
en gestos, los gestos en acciones, las acciones en eventos de herramienta y
las herramientas en comandos para la pizarra.

Es un QObject solo para poder emitir señales; deliberadamente **no dibuja ni
crea widgets**. Toda la lógica de aplicación vive aquí y las vistas se limitan
a mostrar lo que este controlador les cuenta.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.ai.shape_recognizer import recognize_shape
from app.board.canvas import DrawingBoard
from app.board.commands import Command, EraseCommand, ShapeCommand, StrokeCommand
from app.board.strokes import Color, Pixel, Shape
from app.config.settings import AppSettings
from app.gestures.actions import BoardAction, resolve_action
from app.gestures.classifier import GestureClassifier, GestureStabilizer
from app.gestures.gesture_types import Gesture
from app.services import export_service, project_service
from app.tools.base import Tool, ToolContext, ToolId
from app.tools.registry import build_default_registry
from app.tools.selector import Selection, SelectorTool
from app.utils.exceptions import ExportError, ProjectError
from app.utils.logging_config import get_logger
from app.vision import geometry
from app.vision.frame import FramePacket
from app.vision.smoothing import PointSmoother

logger = get_logger(__name__)

#: Rango de grosor al ajustarlo con la pinza.
_MIN_THICKNESS = 1
_MAX_THICKNESS = 48
#: Distancia de pinza (normalizada) que mapeo a ese rango.
_PINCH_MIN = 0.05
_PINCH_MAX = 0.65


class BoardController(QObject):
    """Orquesta pizarra, herramientas y gestos. Sin dependencias de widgets."""

    boardChanged = Signal()
    gestureChanged = Signal(object)  # Gesture
    pointerMoved = Signal(int, int, bool)  # x, y, ¿está dibujando?
    pointerLost = Signal()
    toolChanged = Signal(object)  # ToolId
    thicknessChanged = Signal(int)
    colorChanged = Signal(object)  # Color
    historyChanged = Signal(bool, bool)  # puede deshacer, puede rehacer
    statusMessage = Signal(str)

    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._board = DrawingBoard(settings.board)
        self._tools = build_default_registry()
        self._tool_id = ToolId.PENCIL
        self._color = Color.from_tuple(settings.board.default_color)
        self._thickness = settings.board.default_thickness

        self._classifier = GestureClassifier(settings.gestures)
        self._stabilizer = GestureStabilizer(settings.gestures.stable_frames)
        self._smoother = PointSmoother(settings.vision.smoothing)

        self._gesture = Gesture.NONE
        self._paused = False
        #: Herramienta que el gesto de puño activa temporalmente.
        self._temporary_tool: ToolId | None = None

    # --------------------------------------------------------------- estado

    @property
    def board(self) -> DrawingBoard:
        return self._board

    @property
    def tool(self) -> Tool:
        """Herramienta efectiva: la temporal del gesto tiene prioridad."""
        return self._tools.get(self._temporary_tool or self._tool_id)

    @property
    def tool_id(self) -> ToolId:
        return self._tool_id

    @property
    def color(self) -> Color:
        return self._color

    @property
    def thickness(self) -> int:
        return self._thickness

    @property
    def gesture(self) -> Gesture:
        return self._gesture

    @property
    def is_paused(self) -> bool:
        return self._paused

    def context(self) -> ToolContext:
        """Contexto actual que paso a las herramientas en cada evento."""
        return ToolContext(
            color=self._color,
            width=self._thickness,
            background=self._board.background,
            canvas_size=self._board.size,
        )

    # ------------------------------------------------------------ comandos

    @Slot(object)
    def set_tool(self, tool_id: ToolId) -> None:
        if tool_id == self._tool_id:
            return
        self._finish_interaction()
        self._tool_id = tool_id
        self._temporary_tool = None
        self.toolChanged.emit(tool_id)
        self.statusMessage.emit(f"Herramienta: {self._tools.get(tool_id).label}")

    @Slot(object)
    def set_color(self, color: Color) -> None:
        self._color = color
        self.colorChanged.emit(color)

    @Slot(int)
    def set_thickness(self, value: int) -> None:
        clamped = int(max(_MIN_THICKNESS, min(_MAX_THICKNESS, value)))
        if clamped == self._thickness:
            return
        self._thickness = clamped
        self.thicknessChanged.emit(clamped)

    @Slot()
    def undo(self) -> None:
        if self._board.undo():
            self._emit_board_update()
            self.statusMessage.emit("Deshecho")

    @Slot()
    def redo(self) -> None:
        if self._board.redo():
            self._emit_board_update()
            self.statusMessage.emit("Rehecho")

    @Slot()
    def clear(self) -> None:
        self._finish_interaction()
        self._board.clear()
        self._emit_board_update()
        self.statusMessage.emit("Pizarra limpia")

    @Slot()
    def clean_selection(self) -> None:
        """Sustituyo por figuras perfectas los trazos torcidos de la selección.

        Reconstruyo la lista completa de comandos activos y se la paso a
        `load_commands`: `HistoryStack` no tiene una forma de editar un
        comando puntual, y no quiero inventar una segunda vía para mutar el
        historial cuando cargar un proyecto ya resuelve exactamente esto.
        """
        self._finish_interaction()

        selector = self._tools.get(ToolId.SELECTOR)
        assert isinstance(selector, SelectorTool)
        selection = selector.selection
        if selection is None or selection.is_empty:
            self.statusMessage.emit("Selecciona un área para reconocer figuras")
            return

        commands = list(self._board.history.active)
        updated: list[Command] = []
        converted = 0

        for command in commands:
            shape = self._recognize(command, selection)
            if shape is not None:
                updated.append(ShapeCommand(shape))
                converted += 1
            else:
                updated.append(command)

        selector.clear_selection()

        if converted == 0:
            self.statusMessage.emit("No encontré ningún trazo reconocible en la selección")
            return

        self._board.load_commands(updated)
        self._emit_board_update()
        self.statusMessage.emit(f"{converted} trazo(s) convertido(s) a figura")

    def _recognize(self, command: Command, selection: Selection) -> Shape | None:
        """Reconozco un trazo solo si es un trazo real y cae dentro de la selección.

        Excluyo `EraseCommand`: aunque hereda de `StrokeCommand`, es borrado,
        no dibujo, y "reconocer" un borrado como figura no tiene sentido.
        """
        if not isinstance(command, StrokeCommand) or isinstance(command, EraseCommand):
            return None
        if not self._stroke_within(command.stroke.points, selection):
            return None
        return recognize_shape(command.stroke)

    @staticmethod
    def _stroke_within(points: tuple[Pixel, ...], selection: Selection) -> bool:
        return all(
            selection.left <= x <= selection.right and selection.top <= y <= selection.bottom
            for x, y in points
        )

    # ----------------------------------------------------------- archivos

    def export_png(self, path: str | Path | None = None) -> Path | None:
        """Exporto el lienzo. Devuelvo la ruta o None si falló."""
        try:
            destination = export_service.export_png(self._board.snapshot(), path)
        except ExportError as error:
            logger.error("Exportación fallida: %s", error)
            self.statusMessage.emit(f"No pude exportar: {error}")
            return None
        self.statusMessage.emit(f"Imagen guardada en {destination.name}")
        return destination

    def save_project(self, path: str | Path | None = None) -> Path | None:
        try:
            destination = project_service.save_project(
                path,
                width=self._board.width,
                height=self._board.height,
                background=self._board.background,
                commands=list(self._board.history.active),
            )
        except ProjectError as error:
            logger.error("Guardado fallido: %s", error)
            self.statusMessage.emit(f"No pude guardar: {error}")
            return None
        self._board.mark_saved()
        self.statusMessage.emit(f"Proyecto guardado en {destination.name}")
        return destination

    def open_project(self, path: str | Path) -> bool:
        try:
            project = project_service.load_project(path)
        except ProjectError as error:
            logger.error("Apertura fallida: %s", error)
            self.statusMessage.emit(f"No pude abrir el proyecto: {error}")
            return False

        if project.size != self._board.size:
            self._board.resize(project.width, project.height)

        self._board.load_commands(list(project.commands))
        self._emit_board_update()
        self.statusMessage.emit(f"Proyecto cargado ({len(project.commands)} acciones)")
        return True

    # ------------------------------------------------------- puntero manual

    def pointer_press(self, point: Pixel) -> None:
        """Entrada con ratón: me sirve para trabajar sin cámara y para probar."""
        self.tool.press(point, self.context())
        self._refresh_preview()

    def pointer_move(self, point: Pixel) -> None:
        if self.tool.is_active:
            self.tool.move(point, self.context())
            self._refresh_preview()

    def pointer_release(self) -> None:
        self._finish_interaction()

    # ----------------------------------------------------------- gestos

    @Slot(object)
    def handle_packet(self, packet: FramePacket) -> None:
        """Proceso un frame ya detectado y muevo la pizarra en consecuencia.

        El orden importa: primero estabilizo el gesto, luego resuelvo la
        acción y solo al final toco la herramienta. Así un frame ruidoso nunca
        llega a modificar el lienzo.
        """
        reading = self._classifier.classify(packet.detection.primary)
        gesture = self._stabilizer.update(reading.gesture)

        if gesture is not self._gesture:
            self._gesture = gesture
            self.gestureChanged.emit(gesture)

        if reading.snapshot is None:
            # Sin mano: cierro lo que estuviera dibujando y olvido el suavizado
            # para que al reaparecer la mano no se dibuje una línea fantasma.
            self._finish_interaction()
            self._smoother.reset()
            self.pointerLost.emit()
            return

        action = resolve_action(gesture)
        point = self._project(reading.snapshot.index_tip)

        if action is BoardAction.ADJUST:
            self._apply_pinch_thickness(reading.snapshot.pinch)

        self._apply_action(action, point)
        self.pointerMoved.emit(point[0], point[1], self.tool.is_active)

    def _project(self, index_tip: object) -> Pixel:
        """Paso la punta del índice a píxeles de la pizarra, ya suavizada."""
        raw_x, raw_y = geometry.map_to_canvas(
            index_tip,  # type: ignore[arg-type]
            self._board.width,
            self._board.height,
            self._settings.vision.active_margin,
        )
        return self._smoother.update_int(raw_x, raw_y)

    def _apply_action(self, action: BoardAction, point: Pixel) -> None:
        """Máquina de estados mínima entre la acción y la herramienta activa."""
        if action is BoardAction.PAUSE:
            if not self._paused:
                # Al pausar confirmo el trazo en curso en vez de descartarlo:
                # perder un trazo por levantar la mano sería muy frustrante.
                self._finish_interaction()
                self._paused = True
                self.statusMessage.emit("Interacción pausada")
            return

        if self._paused:
            self._paused = False
            self.statusMessage.emit("Interacción reanudada")

        if action is BoardAction.ERASE:
            self._set_temporary_tool(ToolId.ERASER)
            self._drive_tool(point)
            return

        self._set_temporary_tool(None)

        if action is BoardAction.DRAW:
            self._drive_tool(point)
        elif action in (BoardAction.HOVER, BoardAction.IDLE, BoardAction.ADJUST):
            self._finish_interaction()
        elif action is BoardAction.CONFIRM:
            # El pulgar arriba cierra la figura o el trazo que esté en curso.
            self._finish_interaction()

    def _set_temporary_tool(self, tool_id: ToolId | None) -> None:
        """Cambio de herramienta por gesto sin perder la elegida en la barra."""
        if tool_id == self._temporary_tool:
            return
        self._finish_interaction()
        self._temporary_tool = tool_id

    def _drive_tool(self, point: Pixel) -> None:
        """Presiono o muevo, según si la herramienta ya estaba activa."""
        tool = self.tool
        if tool.is_active:
            tool.move(point, self.context())
        else:
            tool.press(point, self.context())
        self._refresh_preview()

    def _apply_pinch_thickness(self, pinch: float) -> None:
        """Convierto la apertura de la pinza en grosor de trazo.

        Interpolación lineal entre los extremos útiles de la pinza. Fuera de
        ese rango recorto, porque más allá la medida deja de ser fiable.
        """
        span = _PINCH_MAX - _PINCH_MIN
        normalized = geometry.clamp((pinch - _PINCH_MIN) / span, 0.0, 1.0)
        value = _MIN_THICKNESS + normalized * (_MAX_THICKNESS - _MIN_THICKNESS)
        self.set_thickness(int(round(value)))

    # ------------------------------------------------------------- interno

    def _finish_interaction(self) -> None:
        """Cierro la interacción activa y aplico su comando si lo produjo."""
        tool = self.tool
        if not tool.is_active:
            return

        command = tool.release(self.context())
        self._board.set_preview(None)

        if command is not None:
            self._board.execute(command)

        self._emit_board_update()

    def _refresh_preview(self) -> None:
        self._board.set_preview(self.tool.preview(self.context()))
        self.boardChanged.emit()

    def _emit_board_update(self) -> None:
        self.boardChanged.emit()
        self.historyChanged.emit(self._board.history.can_undo, self._board.history.can_redo)

    def shutdown(self) -> None:
        """Cierro cualquier trazo pendiente antes de salir de la aplicación."""
        self._finish_interaction()
