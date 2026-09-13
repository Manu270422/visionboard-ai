"""Jerarquía de errores propia de VisionBoard AI.

Defino mis propias excepciones para no tener que atrapar `Exception` a lo bruto:
así cada capa captura exactamente lo que sabe manejar y deja subir lo demás.
"""

from __future__ import annotations


class VisionBoardError(Exception):
    """Raíz de todos mis errores. Si atrapo esta, atrapo solo lo mío."""


class CameraError(VisionBoardError):
    """La cámara no se pudo abrir, está ocupada o no tengo permisos."""


class FrameError(CameraError):
    """Leí un frame inválido o vacío desde la cámara."""


class VisionError(VisionBoardError):
    """Fallo del detector de manos (MediaPipe no disponible o frame inválido)."""


class BoardError(VisionBoardError):
    """Operación inválida sobre la pizarra (tamaño, comando corrupto, etc.)."""


class ExportError(VisionBoardError):
    """No pude exportar la imagen: ruta inválida, permisos o disco lleno."""


class ProjectError(VisionBoardError):
    """El archivo de proyecto está corrupto o tiene una versión que no entiendo."""


class ConfigError(VisionBoardError):
    """La configuración guardada no es válida y no la puedo cargar."""
