"""Configuración tipada de la aplicación.

Uso dataclasses en vez de diccionarios sueltos porque así el autocompletado y
mypy me avisan si escribo mal un parámetro, y cada grupo de ajustes vive junto
al subsistema al que pertenece (cámara, visión, gestos, pizarra).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

from app.utils.exceptions import ConfigError

SETTINGS_VERSION = 1


@dataclass(slots=True)
class CameraSettings:
    """Todo lo que necesito para abrir y leer la cámara."""

    index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    mirror: bool = True  # Espejo: si muevo la mano a la derecha, el cursor va a la derecha.
    warmup_frames: int = 5  # Descarto los primeros frames, suelen venir negros.

    def validate(self) -> None:
        if self.index < 0:
            raise ConfigError("El índice de cámara no puede ser negativo.")
        if self.width < 160 or self.height < 120:
            raise ConfigError("La resolución de cámara es demasiado pequeña.")
        if not 1 <= self.fps <= 120:
            raise ConfigError("Los FPS de cámara deben estar entre 1 y 120.")


@dataclass(slots=True)
class VisionSettings:
    """Parámetros de MediaPipe y del suavizado del puntero."""

    max_hands: int = 1
    detection_confidence: float = 0.6
    tracking_confidence: float = 0.6
    model_complexity: int = 0  # 0 es el más rápido; me interesa tiempo real.
    smoothing: float = 0.35  # Peso del punto nuevo en el filtro exponencial.
    active_margin: float = 0.12  # Recorto bordes para alcanzar toda la pizarra.

    def validate(self) -> None:
        if not 1 <= self.max_hands <= 2:
            raise ConfigError("Solo manejo una o dos manos.")
        for name in ("detection_confidence", "tracking_confidence", "smoothing"):
            value = getattr(self, name)
            if not 0.0 < value <= 1.0:
                raise ConfigError(f"'{name}' debe estar entre 0 y 1.")
        if not 0.0 <= self.active_margin < 0.4:
            raise ConfigError("El margen activo debe estar entre 0 y 0.4.")


@dataclass(slots=True)
class GestureSettings:
    """Umbrales de la clasificación de gestos y de su estabilización."""

    pinch_ratio: float = 0.35  # Distancia pulgar-índice relativa al tamaño de la mano.
    extended_margin: float = 0.02  # Holgura para decidir si un dedo está estirado.
    stable_frames: int = 3  # Frames iguales seguidos antes de aceptar un gesto.

    def validate(self) -> None:
        if not 0.05 <= self.pinch_ratio <= 1.0:
            raise ConfigError("El umbral de pinza está fuera de rango.")
        if self.stable_frames < 1:
            raise ConfigError("Necesito al menos 1 frame para estabilizar un gesto.")


@dataclass(slots=True)
class BoardSettings:
    """Tamaño y valores por defecto del lienzo."""

    width: int = 1280
    height: int = 720
    background: tuple[int, int, int] = (255, 255, 255)
    default_color: tuple[int, int, int] = (24, 28, 36)
    default_thickness: int = 6
    eraser_multiplier: float = 4.0
    history_limit: int = 300

    def validate(self) -> None:
        if self.width < 320 or self.height < 240:
            raise ConfigError("La pizarra es demasiado pequeña.")
        if self.default_thickness < 1:
            raise ConfigError("El grosor mínimo es 1 píxel.")
        if self.history_limit < 10:
            raise ConfigError("El historial debe permitir al menos 10 acciones.")


@dataclass(slots=True)
class UISettings:
    """Preferencias de la interfaz que quiero recordar entre sesiones."""

    show_landmarks: bool = True
    show_preview: bool = True
    show_fps: bool = True
    theme: str = "dark"


@dataclass(slots=True)
class AppSettings:
    """Configuración completa: es lo único que paso por la aplicación."""

    version: int = SETTINGS_VERSION
    camera: CameraSettings = field(default_factory=CameraSettings)
    vision: VisionSettings = field(default_factory=VisionSettings)
    gestures: GestureSettings = field(default_factory=GestureSettings)
    board: BoardSettings = field(default_factory=BoardSettings)
    ui: UISettings = field(default_factory=UISettings)

    def validate(self) -> None:
        """Valido todos los sub-bloques de una sola pasada."""
        self.camera.validate()
        self.vision.validate()
        self.gestures.validate()
        self.board.validate()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        """Reconstruyo la configuración ignorando claves que ya no existen.

        Prefiero ser tolerante al leer: si añado o quito un ajuste en el futuro,
        un archivo viejo debe seguir cargando en vez de romper la aplicación.
        """
        if not isinstance(data, dict):
            raise ConfigError("El archivo de configuración no contiene un objeto JSON.")

        sub_types = {
            "camera": CameraSettings,
            "vision": VisionSettings,
            "gestures": GestureSettings,
            "board": BoardSettings,
            "ui": UISettings,
        }

        kwargs: dict[str, Any] = {"version": int(data.get("version", SETTINGS_VERSION))}
        for key, dataclass_type in sub_types.items():
            raw = data.get(key) or {}
            if not isinstance(raw, dict):
                raise ConfigError(f"La sección '{key}' de la configuración es inválida.")
            valid_names = {f.name for f in fields(dataclass_type)}
            filtered = {k: v for k, v in raw.items() if k in valid_names}
            kwargs[key] = _coerce(dataclass_type, filtered)

        settings = cls(**kwargs)
        settings.validate()
        return settings


def _coerce(dataclass_type: type, values: dict[str, Any]) -> Any:
    """Convierto listas de JSON a tuplas donde la dataclass espera tuplas.

    JSON no tiene tuplas, así que los colores vuelven como listas; si no los
    convierto, las comparaciones y el hash de los comandos fallan más adelante.
    """
    fixed: dict[str, Any] = {}
    for f in fields(dataclass_type):
        if f.name not in values:
            continue
        value = values[f.name]
        if isinstance(value, list):
            value = tuple(value)
        fixed[f.name] = value
    return dataclass_type(**fixed)
