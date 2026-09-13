"""Tema visual de la aplicación.

Defino los colores como constantes y genero la hoja de estilos desde ellas.
Así no repito hexadecimales por toda la interfaz y cambiar el tema es cambiar
seis valores.

La idea del diseño: el lienzo es claro y ocupa el centro; todo el "instrumento"
que lo rodea es oscuro y silencioso, y un único acento turquesa indica cuándo
el seguimiento de la mano está vivo. El color solo aparece donde significa algo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Palette:
    """Paleta base de la interfaz."""

    deep: str = "#0E1116"  # Fondo de la ventana.
    surface: str = "#161B22"  # Paneles.
    raised: str = "#1F2630"  # Botones y campos.
    line: str = "#2C3542"  # Bordes y separadores.
    text: str = "#E4E9F0"
    muted: str = "#8A97A8"
    accent: str = "#4ED6B8"  # Seguimiento activo.
    alert: str = "#E0793F"  # Cámara caída o error.


PALETTE = Palette()

# Tamaños que reutilizo en varios widgets.
RAIL_WIDTH = 64
PANEL_WIDTH = 260
PREVIEW_HEIGHT = 150


def stylesheet(palette: Palette = PALETTE) -> str:
    """Hoja de estilos global de Qt.

    Uso propiedades dinámicas (`[role="tool"]`) en lugar de un estilo por
    widget para no tener que tocar el QSS cada vez que agrego un botón.
    """
    return f"""
    QWidget {{
        background-color: {palette.deep};
        color: {palette.text};
        font-family: "Inter", "Segoe UI", "DejaVu Sans", sans-serif;
        font-size: 13px;
    }}

    /* Etiquetas y casillas heredan el fondo de su panel: si les dejo el color
       base de la ventana, parecen campos de texto en vez de texto. */
    QLabel, QCheckBox, QSlider {{
        background-color: transparent;
    }}

    QFrame#panel {{
        background-color: {palette.surface};
        border: none;
    }}

    QFrame#rail {{
        background-color: {palette.surface};
        border-right: 1px solid {palette.line};
    }}

    QLabel#sectionTitle {{
        color: {palette.muted};
        font-size: 12px;
        padding: 2px 0 6px 0;
    }}

    QLabel#gestureGlyph {{
        font-size: 34px;
        color: {palette.accent};
    }}

    QLabel#gestureName {{
        font-size: 16px;
        color: {palette.text};
    }}

    QLabel#metric {{
        color: {palette.muted};
        font-size: 12px;
    }}

    QLabel#preview {{
        background-color: #0A0D11;
        border: 1px solid {palette.line};
        border-radius: 6px;
        color: {palette.muted};
    }}

    QPushButton {{
        background-color: {palette.raised};
        color: {palette.text};
        border: 1px solid {palette.line};
        border-radius: 6px;
        padding: 7px 10px;
    }}

    QPushButton:hover {{
        border-color: {palette.accent};
    }}

    QPushButton:pressed {{
        background-color: {palette.line};
    }}

    QPushButton:disabled {{
        color: #55606E;
        border-color: #222932;
    }}

    QPushButton[role="tool"] {{
        font-size: 18px;
        padding: 0;
        min-width: 44px;
        min-height: 44px;
        max-width: 44px;
        max-height: 44px;
    }}

    QPushButton[role="tool"]:checked {{
        background-color: {palette.accent};
        color: {palette.deep};
        border-color: {palette.accent};
    }}

    /* El tamaño de una muestra lo fijo aquí y no con setFixedSize: cuando hay
       hoja de estilos, Qt calcula el tamaño desde el QSS y esta regla gana. */
    QPushButton[role="swatch"] {{
        min-width: 28px;
        min-height: 28px;
        max-width: 28px;
        max-height: 28px;
        padding: 0;
        border-radius: 16px;
        border: 2px solid {palette.line};
    }}

    QPushButton[role="swatch"]:checked {{
        border: 2px solid {palette.accent};
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {palette.line};
        border-radius: 2px;
    }}

    QSlider::handle:horizontal {{
        background: {palette.accent};
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}

    QCheckBox {{
        color: {palette.muted};
        spacing: 8px;
    }}

    QStatusBar {{
        background-color: {palette.surface};
        color: {palette.muted};
        border-top: 1px solid {palette.line};
    }}

    QToolTip {{
        background-color: {palette.raised};
        color: {palette.text};
        border: 1px solid {palette.line};
        padding: 4px;
    }}
    """
