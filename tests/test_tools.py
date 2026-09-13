"""Pruebas de las herramientas de dibujo."""

from __future__ import annotations

import pytest

from app.board.commands import EraseCommand, ShapeCommand, StrokeCommand
from app.board.strokes import ShapeKind
from app.tools.base import ToolContext, ToolId
from app.tools.freehand import EraserTool, PencilTool
from app.tools.registry import ToolRegistry, build_default_registry
from app.tools.selector import Selection, SelectorTool
from app.tools.shapes import ShapeTool


class TestLapiz:
    def test_produce_un_trazo(self, context: ToolContext) -> None:
        lapiz = PencilTool()
        lapiz.press((10, 10), context)
        lapiz.move((60, 40), context)
        comando = lapiz.release(context)
        assert isinstance(comando, StrokeCommand)
        assert len(comando.stroke.points) == 2

    def test_filtra_puntos_demasiado_cercanos(self, context: ToolContext) -> None:
        """Sin este filtro, un dedo quieto generaría decenas de puntos iguales."""
        lapiz = PencilTool()
        lapiz.press((10, 10), context)
        for _ in range(20):
            lapiz.move((10, 11), context)
        comando = lapiz.release(context)
        assert isinstance(comando, StrokeCommand)
        assert len(comando.stroke.points) == 1

    def test_soltar_sin_presionar_no_hace_nada(self, context: ToolContext) -> None:
        assert PencilTool().release(context) is None

    def test_la_vista_previa_existe_mientras_dibujo(self, context: ToolContext) -> None:
        lapiz = PencilTool()
        assert lapiz.preview(context) is None
        lapiz.press((5, 5), context)
        assert lapiz.preview(context) is not None

    def test_cancelar_descarta_el_trazo(self, context: ToolContext) -> None:
        lapiz = PencilTool()
        lapiz.press((5, 5), context)
        lapiz.cancel()
        assert not lapiz.is_active
        assert lapiz.release(context) is None

    def test_usa_el_color_y_grosor_del_contexto(self, context: ToolContext) -> None:
        lapiz = PencilTool()
        lapiz.press((1, 1), context)
        comando = lapiz.release(context)
        assert isinstance(comando, StrokeCommand)
        assert comando.stroke.color == context.color
        assert comando.stroke.width == context.width


class TestBorrador:
    def test_pinta_con_el_fondo_y_mas_grueso(self, context: ToolContext) -> None:
        borrador = EraserTool()
        borrador.press((10, 10), context)
        borrador.move((80, 80), context)
        comando = borrador.release(context)
        assert isinstance(comando, EraseCommand)
        assert comando.stroke.color == context.background
        assert comando.stroke.width > context.width


class TestFiguras:
    def test_rectangulo_desde_dos_puntos(self, context: ToolContext) -> None:
        herramienta = ShapeTool(ShapeKind.RECTANGLE)
        herramienta.press((10, 10), context)
        herramienta.move((100, 80), context)
        comando = herramienta.release(context)
        assert isinstance(comando, ShapeCommand)
        assert comando.shape.start == (10, 10)
        assert comando.shape.end == (100, 80)

    def test_sin_arrastre_no_hay_figura(self, context: ToolContext) -> None:
        herramienta = ShapeTool(ShapeKind.CIRCLE)
        herramienta.press((10, 10), context)
        assert herramienta.release(context) is None

    def test_cada_tipo_tiene_su_identificador(self) -> None:
        assert ShapeTool(ShapeKind.LINE).id is ToolId.LINE
        assert ShapeTool(ShapeKind.ARROW).id is ToolId.ARROW


class TestSeleccion:
    def test_normaliza_el_rectangulo(self) -> None:
        seleccion = Selection.from_points((100, 90), (10, 20))
        assert (seleccion.left, seleccion.top) == (10, 20)
        assert seleccion.width == 90 and seleccion.height == 70

    def test_no_genera_comandos(self, context: ToolContext) -> None:
        herramienta = SelectorTool()
        herramienta.press((10, 10), context)
        herramienta.move((60, 60), context)
        assert herramienta.release(context) is None
        assert herramienta.selection is not None

    def test_una_seleccion_vacia_se_descarta(self, context: ToolContext) -> None:
        herramienta = SelectorTool()
        herramienta.press((10, 10), context)
        herramienta.release(context)
        assert herramienta.selection is None


class TestRegistro:
    def test_registra_todas_las_herramientas(self) -> None:
        registro = build_default_registry()
        assert set(registro.available()) == set(ToolId)

    def test_devuelve_siempre_la_misma_instancia(self) -> None:
        registro = build_default_registry()
        assert registro.get(ToolId.PENCIL) is registro.get(ToolId.PENCIL)

    def test_herramienta_no_registrada_falla(self) -> None:
        with pytest.raises(KeyError):
            ToolRegistry().get(ToolId.PENCIL)

    def test_puedo_registrar_una_herramienta_propia(self) -> None:
        registro = build_default_registry()
        registro.register(ToolId.PENCIL, lambda: ShapeTool(ShapeKind.LINE))
        assert isinstance(registro.get(ToolId.PENCIL), ShapeTool)
