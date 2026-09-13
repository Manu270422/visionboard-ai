"""Pruebas del historial, los comandos y el motor de dibujo."""

from __future__ import annotations

import numpy as np
import pytest

from app.board.canvas import DrawingBoard
from app.board.commands import (
    ClearCommand,
    EraseCommand,
    ShapeCommand,
    StrokeCommand,
    command_from_dict,
)
from app.board.history import HistoryStack
from app.board.strokes import Color, Shape, ShapeKind, Stroke
from app.utils.exceptions import BoardError

ROJO = Color(255, 0, 0)


def trazo(y: int = 10) -> StrokeCommand:
    return StrokeCommand(Stroke(((5, y), (60, y)), ROJO, 4))


class TestHistorial:
    def test_apilar_y_deshacer(self) -> None:
        historial = HistoryStack()
        historial.push(trazo())
        assert historial.can_undo and not historial.can_redo
        assert historial.undo()
        assert not historial.can_undo and historial.can_redo

    def test_rehacer_restaura(self) -> None:
        historial = HistoryStack()
        historial.push(trazo())
        historial.undo()
        assert historial.redo()
        assert len(historial.active) == 1

    def test_deshacer_sin_nada_devuelve_false(self) -> None:
        assert not HistoryStack().undo()

    def test_un_comando_nuevo_descarta_la_rama_deshecha(self) -> None:
        historial = HistoryStack()
        historial.push(trazo(10))
        historial.push(trazo(20))
        historial.undo()
        historial.push(trazo(30))
        assert not historial.can_redo
        assert len(historial.active) == 2

    def test_respeta_el_limite(self) -> None:
        historial = HistoryStack(limit=3)
        for y in range(10):
            historial.push(trazo(y))
        assert len(historial.active) == 3

    def test_replace_carga_un_proyecto(self) -> None:
        historial = HistoryStack()
        historial.replace([trazo(1), trazo(2)])
        assert len(historial.active) == 2
        assert not historial.can_redo


class TestPizarra:
    def test_arranca_con_el_color_de_fondo(self, board: DrawingBoard) -> None:
        assert np.array_equal(board.image()[0, 0], np.array(board.background.rgb))

    def test_dibujar_cambia_pixeles(self, board: DrawingBoard) -> None:
        antes = board.snapshot()
        board.execute(trazo(100))
        assert not np.array_equal(antes, board.image())

    def test_deshacer_restaura_el_lienzo(self, board: DrawingBoard) -> None:
        """Reconstruyo por comandos, así que el resultado debe ser idéntico."""
        limpio = board.snapshot()
        board.execute(trazo(100))
        board.undo()
        assert np.array_equal(limpio, board.image())

    def test_rehacer_vuelve_a_pintar(self, board: DrawingBoard) -> None:
        board.execute(trazo(100))
        pintado = board.snapshot()
        board.undo()
        board.redo()
        assert np.array_equal(pintado, board.image())

    def test_limpiar_se_puede_deshacer(self, board: DrawingBoard) -> None:
        board.execute(trazo(100))
        pintado = board.snapshot()
        board.clear()
        assert not np.array_equal(pintado, board.image())
        board.undo()
        assert np.array_equal(pintado, board.image())

    def test_el_borrador_devuelve_el_fondo(self, board: DrawingBoard) -> None:
        board.execute(StrokeCommand(Stroke(((5, 50), (200, 50)), ROJO, 6)))
        board.execute(EraseCommand(Stroke(((5, 50), (200, 50)), board.background, 24)))
        assert np.array_equal(board.image()[50, 100], np.array(board.background.rgb))

    def test_la_vista_previa_no_toca_el_lienzo(self, board: DrawingBoard) -> None:
        board.set_preview(trazo(100))
        assert np.array_equal(board.image(), board.snapshot())
        assert not np.array_equal(board.composite(), board.image())
        assert board.is_empty

    def test_snapshot_es_una_copia(self, board: DrawingBoard) -> None:
        copia = board.snapshot()
        copia[:] = 0
        assert not np.array_equal(copia, board.image())

    def test_redimensionar_conserva_el_contenido(self, board: DrawingBoard) -> None:
        board.execute(trazo(100))
        board.resize(800, 600)
        assert board.size == (800, 600)
        assert not board.is_empty

    def test_redimensionar_demasiado_pequeño_falla(self, board: DrawingBoard) -> None:
        with pytest.raises(BoardError):
            board.resize(10, 10)


class TestFiguras:
    @pytest.mark.parametrize("tipo", list(ShapeKind))
    def test_todas_las_figuras_pintan(self, board: DrawingBoard, tipo: ShapeKind) -> None:
        board.execute(ShapeCommand(Shape(tipo, (40, 40), (200, 180), ROJO, 3)))
        assert not np.array_equal(board.image(), np.full_like(board.image(), 255))


class TestSerializacion:
    def test_ida_y_vuelta_de_trazo(self) -> None:
        original = trazo()
        recuperado = command_from_dict(original.to_dict())
        assert isinstance(recuperado, StrokeCommand)
        assert recuperado.stroke == original.stroke

    def test_ida_y_vuelta_de_figura(self) -> None:
        original = ShapeCommand(Shape(ShapeKind.CIRCLE, (10, 10), (50, 50), ROJO, 2))
        recuperado = command_from_dict(original.to_dict())
        assert isinstance(recuperado, ShapeCommand)
        assert recuperado.shape.kind is ShapeKind.CIRCLE

    def test_ida_y_vuelta_de_limpiar(self) -> None:
        recuperado = command_from_dict(ClearCommand(Color(1, 2, 3)).to_dict())
        assert isinstance(recuperado, ClearCommand)

    def test_el_borrado_conserva_su_tipo(self) -> None:
        original = EraseCommand(Stroke(((1, 1), (2, 2)), ROJO, 9))
        assert isinstance(command_from_dict(original.to_dict()), EraseCommand)

    def test_tipo_desconocido_falla(self) -> None:
        with pytest.raises(BoardError):
            command_from_dict({"type": "cohete"})

    def test_datos_incompletos_fallan(self) -> None:
        with pytest.raises(BoardError):
            command_from_dict({"type": "stroke"})


class TestValidaciones:
    def test_color_fuera_de_rango(self) -> None:
        with pytest.raises(ValueError):
            Color(300, 0, 0)

    def test_color_desde_hex(self) -> None:
        assert Color.from_hex("#ff8000") == Color(255, 128, 0)

    def test_trazo_sin_puntos(self) -> None:
        with pytest.raises(ValueError):
            Stroke((), ROJO, 3)

    def test_grosor_invalido(self) -> None:
        with pytest.raises(ValueError):
            Stroke(((1, 1),), ROJO, 0)
