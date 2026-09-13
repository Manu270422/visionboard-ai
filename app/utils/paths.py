"""Rutas del proyecto y validación de rutas de escritura.

Centralizo aquí el cálculo de directorios porque no quiero rutas relativas
regadas por todo el código: si mañana muevo `data/`, lo cambio en un solo lugar.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.utils.exceptions import ExportError


def _project_root() -> Path:
    """Calculo la raíz del proyecto, también quando corro como .exe.

    Empaquetado con PyInstaller, `__file__` apunta a la carpeta temporal donde
    se descomprime el ejecutable (se borra al cerrar la app), así que guardar
    ahí perdería la configuración y los dibujos en cada sesión. `sys.frozen` es
    la bandera que PyInstaller pone en tiempo de ejecución para detectar justo
    este caso; en ese escenario uso la carpeta donde vive el .exe en disco.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # Subo tres niveles desde este archivo (utils -> app -> raíz del proyecto).
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT: Path = _project_root()

DATA_DIR: Path = PROJECT_ROOT / "data"
DRAWINGS_DIR: Path = DATA_DIR / "drawings"
CONFIG_DIR: Path = DATA_DIR / "config"
LOGS_DIR: Path = DATA_DIR / "logs"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"

DEFAULT_CONFIG_FILE: Path = CONFIG_DIR / "settings.json"

PROJECT_EXTENSION = ".vbai"
IMAGE_EXTENSION = ".png"


def ensure_directory(path: Path) -> Path:
    """Creo el directorio si no existe y devuelvo su ruta ya resuelta."""
    path = Path(path).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:  # permisos, disco lleno, ruta inválida
        raise ExportError(f"No pude crear el directorio '{path}': {error}") from error
    return path.resolve()


def prepare_output_path(
    path: str | Path,
    *,
    expected_suffix: str,
    overwrite: bool = True,
) -> Path:
    """Valido una ruta de salida antes de escribir en ella.

    Hago tres cosas que me evitan sorpresas: normalizo la extensión, creo el
    directorio padre y bloqueo la sobrescritura accidental cuando no la pedí.
    """
    candidate = Path(path).expanduser()

    if candidate.suffix.lower() != expected_suffix:
        candidate = candidate.with_suffix(expected_suffix)

    if candidate.is_dir():
        raise ExportError(f"'{candidate}' es un directorio, no un archivo.")

    ensure_directory(candidate.parent)
    resolved = candidate.resolve()

    if resolved.exists() and not overwrite:
        raise ExportError(f"El archivo '{resolved}' ya existe y no pedí sobrescribirlo.")

    return resolved


def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    """Genero un nombre libre tipo `dibujo.png`, `dibujo_1.png`, `dibujo_2.png`."""
    ensure_directory(directory)
    candidate = directory / f"{stem}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate
