"""Guardado y carga de proyectos `.vbai`.

Formato propio, documentado en `docs/PROJECT_FORMAT.md`. Es JSON plano con la
lista de comandos: pesa poquísimo comparado con un PNG y, sobre todo, es
**editable y reproducible** (puedo deshacer después de reabrir el proyecto,
cosa imposible si solo guardara la imagen final).

No uso `pickle` a propósito: deserializar un pickle ejecuta código, y un
archivo de proyecto puede venir de otra persona.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.board.commands import Command, command_from_dict
from app.board.strokes import Color
from app.utils.exceptions import BoardError, ProjectError
from app.utils.logging_config import get_logger
from app.utils.paths import DRAWINGS_DIR, PROJECT_EXTENSION, prepare_output_path, unique_path

logger = get_logger(__name__)

PROJECT_FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class Project:
    """Contenido de un archivo de proyecto ya validado."""

    width: int
    height: int
    background: Color
    commands: tuple[Command, ...]
    created_at: str = ""

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height


def default_project_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return unique_path(DRAWINGS_DIR, f"proyecto_{stamp}", PROJECT_EXTENSION)


def save_project(
    path: str | Path | None,
    *,
    width: int,
    height: int,
    background: Color,
    commands: list[Command] | tuple[Command, ...],
    overwrite: bool = True,
) -> Path:
    """Serializo los comandos activos a un archivo `.vbai`."""
    target = (
        default_project_path()
        if path is None
        else prepare_output_path(path, expected_suffix=PROJECT_EXTENSION, overwrite=overwrite)
    )

    serialized = [command.to_dict() for command in commands]
    payload = {
        "format": "visionboard-project",
        "version": PROJECT_FORMAT_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "canvas": {
            "width": int(width),
            "height": int(height),
            "background": background.to_dict(),
        },
        "commands": serialized,
    }

    temporary = target.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(target)  # Escritura atómica: nunca dejo un archivo a medias.
    except OSError as error:
        raise ProjectError(f"No pude guardar el proyecto en '{target}': {error}") from error

    logger.info("Proyecto guardado en %s (%d comandos)", target, len(serialized))
    return target


def load_project(path: str | Path) -> Project:
    """Leo y valido un archivo `.vbai`.

    Valido en orden: existe, es JSON, tiene el formato esperado, la versión es
    compatible y cada comando se puede reconstruir. Si algo falla lanzo
    `ProjectError` con el motivo, en vez de dejar la pizarra a medio cargar.
    """
    source = Path(path).expanduser()

    if not source.is_file():
        raise ProjectError(f"No existe el archivo de proyecto '{source}'.")

    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ProjectError(f"El proyecto '{source}' está corrupto: {error}") from error
    except OSError as error:
        raise ProjectError(f"No pude leer '{source}': {error}") from error

    if not isinstance(raw, dict) or raw.get("format") != "visionboard-project":
        raise ProjectError(f"'{source}' no es un proyecto de VisionBoard.")

    version = raw.get("version")
    if version != PROJECT_FORMAT_VERSION:
        raise ProjectError(
            f"Versión de proyecto no compatible: {version} (esperaba {PROJECT_FORMAT_VERSION})."
        )

    canvas = raw.get("canvas")
    if not isinstance(canvas, dict):
        raise ProjectError("El proyecto no describe el lienzo.")

    try:
        width = int(canvas["width"])
        height = int(canvas["height"])
        background = Color.from_dict(canvas["background"])
    except (KeyError, TypeError, ValueError) as error:
        raise ProjectError(f"Datos de lienzo inválidos: {error}") from error

    raw_commands = raw.get("commands")
    if not isinstance(raw_commands, list):
        raise ProjectError("El proyecto no contiene una lista de comandos.")

    try:
        commands = tuple(command_from_dict(item) for item in raw_commands)
    except BoardError as error:
        raise ProjectError(f"Comando inválido en el proyecto: {error}") from error

    logger.info("Proyecto cargado desde %s (%d comandos)", source, len(commands))
    return Project(
        width=width,
        height=height,
        background=background,
        commands=commands,
        created_at=str(raw.get("created_at", "")),
    )
