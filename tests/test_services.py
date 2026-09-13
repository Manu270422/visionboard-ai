"""Pruebas de exportación, persistencia de proyectos y configuración."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.board.canvas import DrawingBoard
from app.board.commands import StrokeCommand
from app.board.strokes import Color, Stroke
from app.config.settings import AppSettings, CameraSettings
from app.config.storage import load_settings, save_settings
from app.services.export_service import export_png
from app.services.performance import FpsMeter
from app.services.project_service import load_project, save_project
from app.utils.exceptions import ConfigError, ExportError, ProjectError

ROJO = Color(255, 0, 0)


def trazo() -> StrokeCommand:
    return StrokeCommand(Stroke(((5, 5), (50, 50)), ROJO, 3))


class TestExportacion:
    def test_escribe_el_archivo(self, board: DrawingBoard, tmp_path: Path) -> None:
        board.execute(trazo())
        destino = export_png(board.snapshot(), tmp_path / "dibujo.png")
        assert destino.exists() and destino.stat().st_size > 0

    def test_corrige_la_extension(self, board: DrawingBoard, tmp_path: Path) -> None:
        destino = export_png(board.snapshot(), tmp_path / "dibujo.txt")
        assert destino.suffix == ".png"

    def test_crea_el_directorio_padre(self, board: DrawingBoard, tmp_path: Path) -> None:
        destino = export_png(board.snapshot(), tmp_path / "nueva" / "sub" / "d.png")
        assert destino.exists()

    def test_no_sobrescribe_si_no_lo_pido(self, board: DrawingBoard, tmp_path: Path) -> None:
        ruta = tmp_path / "dibujo.png"
        export_png(board.snapshot(), ruta)
        with pytest.raises(ExportError):
            export_png(board.snapshot(), ruta, overwrite=False)

    def test_rechaza_un_lienzo_invalido(self, tmp_path: Path) -> None:
        with pytest.raises(ExportError):
            export_png(np.zeros((10, 10), dtype=np.uint8), tmp_path / "x.png")


class TestProyectos:
    def test_ida_y_vuelta_completa(self, board: DrawingBoard, tmp_path: Path) -> None:
        """Guardo, cargo y compruebo que el lienzo renderizado es idéntico."""
        board.execute(trazo())
        esperado = board.snapshot()

        ruta = save_project(
            tmp_path / "p.vbai",
            width=board.width,
            height=board.height,
            background=board.background,
            commands=list(board.history.active),
        )

        proyecto = load_project(ruta)
        otra = DrawingBoard()
        otra.resize(proyecto.width, proyecto.height)
        otra.load_commands(list(proyecto.commands))

        assert np.array_equal(otra.image(), esperado)

    def test_archivo_inexistente(self, tmp_path: Path) -> None:
        with pytest.raises(ProjectError):
            load_project(tmp_path / "no_existe.vbai")

    def test_json_corrupto(self, tmp_path: Path) -> None:
        ruta = tmp_path / "roto.vbai"
        ruta.write_text("{ esto no es json", encoding="utf-8")
        with pytest.raises(ProjectError):
            load_project(ruta)

    def test_formato_ajeno(self, tmp_path: Path) -> None:
        ruta = tmp_path / "otro.vbai"
        ruta.write_text(json.dumps({"format": "otra-cosa"}), encoding="utf-8")
        with pytest.raises(ProjectError):
            load_project(ruta)

    def test_version_incompatible(self, tmp_path: Path) -> None:
        ruta = tmp_path / "futuro.vbai"
        ruta.write_text(
            json.dumps({"format": "visionboard-project", "version": 99}), encoding="utf-8"
        )
        with pytest.raises(ProjectError):
            load_project(ruta)

    def test_comando_corrupto(self, tmp_path: Path) -> None:
        ruta = tmp_path / "malo.vbai"
        ruta.write_text(
            json.dumps(
                {
                    "format": "visionboard-project",
                    "version": 1,
                    "canvas": {"width": 100, "height": 100, "background": {"r": 1, "g": 1, "b": 1}},
                    "commands": [{"type": "desconocido"}],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ProjectError):
            load_project(ruta)


class TestConfiguracion:
    def test_ida_y_vuelta(self, tmp_path: Path) -> None:
        ajustes = AppSettings(camera=CameraSettings(index=2, width=640, height=480))
        ruta = save_settings(ajustes, tmp_path / "settings.json")
        cargado = load_settings(ruta)
        assert cargado.camera.index == 2
        assert cargado.camera.width == 640

    def test_sin_archivo_usa_defaults(self, tmp_path: Path) -> None:
        assert load_settings(tmp_path / "no_existe.json").camera.index == 0

    def test_archivo_corrupto_no_rompe_el_arranque(self, tmp_path: Path) -> None:
        ruta = tmp_path / "roto.json"
        ruta.write_text("no soy json", encoding="utf-8")
        assert isinstance(load_settings(ruta), AppSettings)

    def test_ignora_claves_desconocidas(self, tmp_path: Path) -> None:
        ruta = tmp_path / "viejo.json"
        ruta.write_text(
            json.dumps({"version": 1, "camera": {"index": 1, "ajuste_viejo": True}}),
            encoding="utf-8",
        )
        assert load_settings(ruta).camera.index == 1

    def test_los_colores_vuelven_como_tupla(self, tmp_path: Path) -> None:
        """JSON no tiene tuplas; si no convierto, los comandos fallan después."""
        ruta = save_settings(AppSettings(), tmp_path / "s.json")
        assert isinstance(load_settings(ruta).board.background, tuple)

    def test_validacion_detecta_valores_imposibles(self) -> None:
        with pytest.raises(ConfigError):
            AppSettings(camera=CameraSettings(index=-1)).validate()


class TestRendimiento:
    def test_necesita_dos_marcas(self) -> None:
        medidor = FpsMeter()
        assert medidor.tick(0.0) == 0.0

    def test_calcula_los_fps(self) -> None:
        medidor = FpsMeter()
        for i in range(11):
            medidor.tick(i * 0.1)  # Un frame cada 100 ms = 10 FPS.
        assert medidor.fps == pytest.approx(10.0, abs=0.1)

    def test_reset_limpia_la_ventana(self) -> None:
        medidor = FpsMeter()
        medidor.tick(0.0)
        medidor.tick(0.1)
        medidor.reset()
        assert medidor.fps == 0.0
