"""Ventana principal.

Ensambla las piezas y cablea las señales. Deliberadamente no contiene lógica
de dibujo ni de visión: si tengo que decidir algo sobre el lienzo, la decisión
pertenece al controlador y esta ventana solo la refleja.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QWidget,
)

from app.config.settings import AppSettings
from app.config.storage import save_settings
from app.gestures.gesture_types import Gesture
from app.tools.base import ToolId
from app.ui.board_view import BoardView
from app.ui.controller import BoardController
from app.ui.status_panel import StatusPanel
from app.ui.theme import stylesheet
from app.ui.toolbar import ToolRail
from app.ui.vision_worker import VisionWorker
from app.utils.exceptions import ConfigError
from app.utils.logging_config import get_logger
from app.utils.paths import DRAWINGS_DIR, PROJECT_EXTENSION
from app.vision import overlay
from app.vision.frame import FramePacket

logger = get_logger(__name__)

# Un atajo puede llegar como secuencia estándar de Qt o como texto suelto.
_Shortcut = QKeySequence | QKeySequence.StandardKey | str


class MainWindow(QMainWindow):
    """Ventana principal de VisionBoard AI."""

    def __init__(self, settings: AppSettings, *, use_camera: bool = True) -> None:
        super().__init__()
        self._settings = settings
        self._use_camera = use_camera
        self._worker: VisionWorker | None = None

        self.setWindowTitle("VisionBoard AI")
        self.resize(1440, 860)
        self.setStyleSheet(stylesheet())

        self._controller = BoardController(settings, self)
        self._rail = ToolRail()
        self._view = BoardView()
        self._panel = StatusPanel()

        self._build_layout()
        self._build_shortcuts()
        self._connect_signals()
        self._apply_initial_state()

        if use_camera:
            self._start_vision()
        else:
            self._panel.set_camera_state("Cámara desactivada (modo ratón)", ok=False)
            self._panel.clear_frame("Modo sin cámara")

    # -------------------------------------------------------------- montaje

    def _build_layout(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._rail)
        layout.addWidget(self._view, 1)
        layout.addWidget(self._panel)
        self.setCentralWidget(central)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Índice arriba para dibujar · puño para borrar · palma para pausar")

    def _build_shortcuts(self) -> None:
        """Atajos de teclado.

        Los defino como QAction de la ventana y no dentro de los widgets para
        que funcionen sin importar qué tenga el foco.
        """
        definitions: list[tuple[str, _Shortcut, Callable[[], object]]] = [
            ("Deshacer", QKeySequence.StandardKey.Undo, self._controller.undo),
            ("Rehacer", QKeySequence.StandardKey.Redo, self._controller.redo),
            ("Rehacer alternativo", "Ctrl+Y", self._controller.redo),
            ("Guardar", QKeySequence.StandardKey.Save, self._on_save),
            ("Exportar", "Ctrl+E", self._on_export),
            ("Abrir", QKeySequence.StandardKey.Open, self._on_open),
            ("Limpiar", "Ctrl+Shift+C", self._controller.clear),
            ("Reconocer figura", "Ctrl+Shift+A", self._controller.clean_selection),
            ("Salir", QKeySequence.StandardKey.Quit, self.close),
        ]

        for name, shortcut, handler in definitions:
            action = QAction(name, self)
            action.setShortcut(shortcut)
            action.triggered.connect(handler)  # type: ignore[arg-type]
            self.addAction(action)

        # Atajos de herramienta: leo la letra de la propia herramienta para no
        # mantener la lista en dos sitios.
        for tool_id in ToolId:
            tool = self._controller._tools.get(tool_id)  # noqa: SLF001 - registro interno
            if not tool.shortcut:
                continue
            action = QAction(tool.label, self)
            action.setShortcut(tool.shortcut)
            action.triggered.connect(lambda _checked=False, t=tool_id: self._select_tool(t))
            self.addAction(action)

    def _connect_signals(self) -> None:
        self._rail.toolSelected.connect(self._select_tool)

        self._panel.colorSelected.connect(self._controller.set_color)
        self._panel.thicknessChanged.connect(self._controller.set_thickness)
        self._panel.undoRequested.connect(self._controller.undo)
        self._panel.redoRequested.connect(self._controller.redo)
        self._panel.clearRequested.connect(self._controller.clear)
        self._panel.aiCleanRequested.connect(self._controller.clean_selection)
        self._panel.saveRequested.connect(self._on_save)
        self._panel.exportRequested.connect(self._on_export)
        self._panel.landmarksToggled.connect(self._on_landmarks_toggled)
        self._panel.previewToggled.connect(self._on_preview_toggled)

        self._view.pointerPressed.connect(self._controller.pointer_press)
        self._view.pointerMoved.connect(self._controller.pointer_move)
        self._view.pointerReleased.connect(self._controller.pointer_release)

        self._controller.boardChanged.connect(self._refresh_board)
        self._controller.gestureChanged.connect(self._panel.set_gesture)
        self._controller.pointerMoved.connect(self._view.set_cursor_position)
        self._controller.pointerLost.connect(self._view.clear_cursor)
        self._controller.thicknessChanged.connect(self._on_thickness_changed)
        self._controller.colorChanged.connect(self._panel.set_color)
        self._controller.historyChanged.connect(self._panel.set_history_state)
        self._controller.toolChanged.connect(self._rail.select)
        self._controller.statusMessage.connect(self._show_message)

    def _apply_initial_state(self) -> None:
        self._panel.set_thickness(self._controller.thickness)
        self._panel.set_color(self._controller.color)
        self._panel.set_gesture(Gesture.NONE)
        self._panel.set_history_state(False, False)
        self._panel._show_landmarks.setChecked(self._settings.ui.show_landmarks)  # noqa: SLF001
        self._panel._show_preview.setChecked(self._settings.ui.show_preview)  # noqa: SLF001
        self._view.set_cursor_radius(self._controller.thickness)
        self._refresh_board()

    # --------------------------------------------------------------- visión

    def _start_vision(self) -> None:
        worker = VisionWorker(self._settings, self)
        worker.frameReady.connect(self._on_frame)
        worker.cameraOpened.connect(self._on_camera_opened)
        worker.failed.connect(self._on_camera_failed)
        worker.start()
        self._worker = worker

    @Slot(object)
    def _on_frame(self, packet: FramePacket) -> None:
        """Recibo el frame en el hilo de la interfaz y actualizo todo."""
        self._controller.handle_packet(packet)

        if self._settings.ui.show_preview:
            # Copio antes de dibujar el overlay: el array original es el que
            # acaba de usar el detector y prefiero no mutarlo.
            preview = packet.frame_rgb.copy()
            if self._settings.ui.show_landmarks:
                overlay.draw_detection(preview, packet.detection)
            self._panel.show_frame(preview)

        self._panel.set_metrics(packet.fps, packet.process_ms)

    @Slot(int, int)
    def _on_camera_opened(self, width: int, height: int) -> None:
        self._panel.set_camera_state(f"Conectada · {width}x{height}")

    @Slot(str)
    def _on_camera_failed(self, message: str) -> None:
        """Aviso del fallo pero dejo la aplicación usable con el ratón."""
        self._panel.set_camera_state("Sin cámara", ok=False)
        self._panel.clear_frame("Cámara no disponible")
        self._show_message(message)
        QMessageBox.warning(
            self,
            "Cámara no disponible",
            f"{message}\n\nPuedes seguir dibujando con el ratón.",
        )

    # -------------------------------------------------------------- acciones

    @Slot(object)
    def _select_tool(self, tool_id: ToolId) -> None:
        self._controller.set_tool(tool_id)
        self._rail.select(tool_id)

    @Slot(int)
    def _on_thickness_changed(self, value: int) -> None:
        self._panel.set_thickness(value)
        self._view.set_cursor_radius(value)

    @Slot(bool)
    def _on_landmarks_toggled(self, enabled: bool) -> None:
        self._settings.ui.show_landmarks = enabled

    @Slot(bool)
    def _on_preview_toggled(self, enabled: bool) -> None:
        self._settings.ui.show_preview = enabled
        if not enabled:
            self._panel.clear_frame()

    @Slot()
    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar proyecto",
            str(DRAWINGS_DIR / f"proyecto{PROJECT_EXTENSION}"),
            f"Proyecto VisionBoard (*{PROJECT_EXTENSION})",
        )
        if path:
            self._controller.save_project(path)

    @Slot()
    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar imagen", str(DRAWINGS_DIR / "pizarra.png"), "Imagen PNG (*.png)"
        )
        if path:
            self._controller.export_png(path)

    @Slot()
    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir proyecto",
            str(DRAWINGS_DIR),
            f"Proyecto VisionBoard (*{PROJECT_EXTENSION})",
        )
        if path:
            self._controller.open_project(Path(path))

    @Slot()
    def _refresh_board(self) -> None:
        self._view.set_canvas(self._controller.board.composite())

    @Slot(str)
    def _show_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)

    # ---------------------------------------------------------------- cierre

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - firma de Qt
        """Cierre seguro: paro el hilo, libero la cámara y guardo ajustes.

        Este método es el que garantiza que la luz de la webcam se apague.
        Paro el hilo ANTES de dejar que Qt destruya los widgets.
        """
        logger.info("Cerrando la aplicación…")

        if self._worker is not None:
            self._worker.stop()
            self._worker = None

        self._controller.shutdown()

        try:
            save_settings(self._settings)
        except ConfigError as error:
            logger.warning("No pude guardar la configuración al salir: %s", error)

        super().closeEvent(event)
