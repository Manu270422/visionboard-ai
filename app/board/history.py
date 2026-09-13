"""Historial de acciones con deshacer y rehacer.

Implemento el historial como una lista de comandos más un cursor (`_index`)
que marca cuántos están activos. Deshacer es mover el cursor hacia atrás, no
borrar nada; solo descarto la cola cuando dibujo algo nuevo después de haber
deshecho, que es el comportamiento estándar de cualquier editor.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.board.commands import Command


class HistoryStack:
    """Pila de comandos con cursor de deshacer/rehacer y límite de tamaño."""

    def __init__(self, limit: int = 300) -> None:
        if limit < 1:
            raise ValueError("El historial necesita un límite de al menos 1.")
        self._limit = limit
        self._commands: list[Command] = []
        self._index = 0  # Número de comandos activos (no un índice de elemento).

    def push(self, command: Command) -> None:
        """Registro un comando nuevo.

        Si había comandos deshechos, los descarto: la rama que se abandona
        deja de ser alcanzable, igual que en Word o Photoshop.
        """
        del self._commands[self._index :]
        self._commands.append(command)

        if len(self._commands) > self._limit:
            # Suelto los más antiguos para acotar la memoria en sesiones largas.
            overflow = len(self._commands) - self._limit
            del self._commands[:overflow]

        self._index = len(self._commands)

    def undo(self) -> bool:
        """Retrocedo un paso. Devuelvo False si no había nada que deshacer."""
        if not self.can_undo:
            return False
        self._index -= 1
        return True

    def redo(self) -> bool:
        """Avanzo un paso. Devuelvo False si no había nada que rehacer."""
        if not self.can_redo:
            return False
        self._index += 1
        return True

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._commands)

    @property
    def active(self) -> Sequence[Command]:
        """Comandos vigentes, en orden de aplicación."""
        return tuple(self._commands[: self._index])

    @property
    def last(self) -> Command | None:
        return self._commands[self._index - 1] if self._index else None

    def clear(self) -> None:
        """Vacío el historial por completo (proyecto nuevo o cargado)."""
        self._commands.clear()
        self._index = 0

    def replace(self, commands: Sequence[Command]) -> None:
        """Cargo un historial completo, por ejemplo al abrir un proyecto."""
        self._commands = list(commands)[-self._limit :]
        self._index = len(self._commands)

    def __len__(self) -> int:
        return self._index
