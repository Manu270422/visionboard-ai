"""Lectura y escritura de la configuración en disco.

Separo la persistencia de las dataclasses: `settings.py` define QUÉ se
configura y este módulo se encarga de CÓMO se guarda.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config.settings import AppSettings
from app.utils.exceptions import ConfigError
from app.utils.logging_config import get_logger
from app.utils.paths import DEFAULT_CONFIG_FILE, ensure_directory

logger = get_logger(__name__)


def load_settings(path: Path | None = None) -> AppSettings:
    """Cargo la configuración; si algo falla vuelvo a los valores por defecto.

    Decido no propagar el error hacia arriba porque un archivo corrupto no
    debería impedirme abrir la aplicación: aviso por log y sigo con defaults.
    """
    target = Path(path or DEFAULT_CONFIG_FILE)

    if not target.exists():
        logger.info("No hay configuración previa en %s; uso valores por defecto.", target)
        return AppSettings()

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        settings = AppSettings.from_dict(raw)
    except json.JSONDecodeError as error:
        logger.warning("Configuración corrupta (%s); uso valores por defecto.", error)
        return AppSettings()
    except (ConfigError, TypeError, ValueError) as error:
        logger.warning("Configuración inválida (%s); uso valores por defecto.", error)
        return AppSettings()
    except OSError as error:
        logger.warning("No pude leer la configuración (%s); uso valores por defecto.", error)
        return AppSettings()

    logger.info("Configuración cargada desde %s", target)
    return settings


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    """Guardo la configuración con escritura atómica.

    Escribo primero en un archivo temporal y luego lo reemplazo: si la app se
    cierra a mitad del guardado, no me quedo con un JSON a medias.
    """
    target = Path(path or DEFAULT_CONFIG_FILE)
    ensure_directory(target.parent)

    settings.validate()
    temporary = target.with_suffix(".tmp")

    try:
        temporary.write_text(
            json.dumps(settings.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(target)
    except OSError as error:
        raise ConfigError(f"No pude guardar la configuración en '{target}': {error}") from error

    logger.info("Configuración guardada en %s", target)
    return target
