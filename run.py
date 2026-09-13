"""Lanzador para el ejecutable empaquetado.

PyInstaller analiza el script que le indico como punto de entrada y resuelve
sus imports a partir de la carpeta donde vive ese script. Si le apuntara
directamente a `app/main.py`, la carpeta base sería `app/` y `import app...`
dejaría de encontrar el paquete. Por eso este archivo vive en la raíz del
proyecto y solo reexporta `main`.
"""

from __future__ import annotations

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
