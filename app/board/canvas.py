"""Motor de dibujo (`DrawingBoard`).

Es el corazón de la pizarra y **no sabe que existe PySide6**. Solo maneja un
lienzo NumPy, una lista de comandos y un historial. La interfaz le pide la
imagen y la pinta; podría igual de bien pintarla una web o un script.

Sobre el rendimiento: cuando añado un comando lo aplico directamente al lienzo
que ya tengo (barato). Solo cuando deshago o rehago reconstruyo desde cero
reproduciendo los comandos activos, porque un comando no se puede "despintar".
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from app.board import renderer
from app.board.commands import ClearCommand, Command
from app.board.history import HistoryStack
from app.board.strokes import Color
from app.config.settings import BoardSettings
from app.utils.exceptions import BoardError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class DrawingBoard:
    """Lienzo + historial + render. Sin dependencias de interfaz."""

    def __init__(self, settings: BoardSettings | None = None) -> None:
        self._settings = settings or BoardSettings()
        self._settings.validate()
        self._background = Color.from_tuple(self._settings.background)
        self._history = HistoryStack(self._settings.history_limit)
        self._canvas = renderer.new_canvas(
            self._settings.width, self._settings.height, self._background
        )
        self._preview: Command | None = None
        self._dirty = False

    # ---------------------------------------------------------------- estado

    @property
    def width(self) -> int:
        return self._canvas.shape[1]

    @property
    def height(self) -> int:
        return self._canvas.shape[0]

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height

    @property
    def background(self) -> Color:
        return self._background

    @property
    def history(self) -> HistoryStack:
        return self._history

    @property
    def is_empty(self) -> bool:
        return len(self._history) == 0

    @property
    def has_unsaved_changes(self) -> bool:
        return self._dirty

    def mark_saved(self) -> None:
        self._dirty = False

    # ------------------------------------------------------------- comandos

    def execute(self, command: Command) -> None:
        """Aplico un comando y lo registro en el historial."""
        command.apply(self._canvas)
        self._history.push(command)
        self._preview = None
        self._dirty = True

    def set_preview(self, command: Command | None) -> None:
        """Guardo el trazo o figura que se está dibujando ahora mismo.

        La vista previa no entra al historial: es efímera y se repinta sobre
        una copia del lienzo en cada frame. Así puedo mostrar la figura
        mientras muevo el dedo sin ensuciar el deshacer con estados a medias.
        """
        self._preview = command

    def clear(self) -> None:
        """Limpio el lienzo dejando la acción en el historial."""
        self.execute(ClearCommand(self._background))

    def undo(self) -> bool:
        if not self._history.undo():
            return False
        self._rerender()
        self._dirty = True
        return True

    def redo(self) -> bool:
        if not self._history.redo():
            return False
        self._rerender()
        self._dirty = True
        return True

    def load_commands(self, commands: Sequence[Command]) -> None:
        """Reemplazo el contenido por el de un proyecto cargado."""
        self._history.replace(commands)
        self._rerender()
        self._dirty = False

    # ---------------------------------------------------------------- render

    def _rerender(self) -> None:
        """Reconstruyo el lienzo reproduciendo los comandos activos.

        Reutilizo el mismo array (`fill` en sitio) en lugar de crear uno nuevo
        para no generar basura de memoria en cada deshacer.
        """
        renderer.fill(self._canvas, self._background)
        for command in self._history.active:
            command.apply(self._canvas)

    def image(self) -> np.ndarray:
        """Lienzo confirmado, sin vista previa. Devuelvo la referencia real.

        No copio aquí porque esto se llama en cada repintado; quien necesite
        modificarlo debe pedir `snapshot()`.
        """
        return self._canvas

    def composite(self) -> np.ndarray:
        """Lienzo + vista previa, listo para mostrar en pantalla."""
        if self._preview is None:
            return self._canvas
        frame = self._canvas.copy()
        self._preview.apply(frame)
        return frame

    def snapshot(self) -> np.ndarray:
        """Copia independiente del lienzo, para exportar o guardar."""
        return self._canvas.copy()

    # ---------------------------------------------------------------- tamaño

    def resize(self, width: int, height: int) -> None:
        """Cambio el tamaño del lienzo y vuelvo a renderizar el contenido.

        Los comandos guardan píxeles absolutos, así que al redimensionar el
        contenido no se escala: se re-dibuja en el lienzo nuevo. Lo dejo
        documentado porque es una limitación consciente de la versión 1.
        """
        if width < 320 or height < 240:
            raise BoardError("El lienzo no puede ser menor a 320x240.")
        self._canvas = renderer.new_canvas(width, height, self._background)
        self._rerender()
        logger.info("Lienzo redimensionado a %dx%d", width, height)
