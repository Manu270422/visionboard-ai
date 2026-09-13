# Formato de proyecto `.vbai`

Un proyecto de VisionBoard es un archivo JSON en UTF-8. No guarda la imagen
final: guarda **la lista de acciones** que la producen. Por eso pesa kilobytes
en vez de megabytes y, sobre todo, permite seguir deshaciendo y editando
después de reabrirlo.

## Estructura

```json
{
  "format": "visionboard-project",
  "version": 1,
  "created_at": "2026-09-13T10:24:00",
  "canvas": {
    "width": 1280,
    "height": 720,
    "background": { "r": 255, "g": 255, "b": 255 }
  },
  "commands": [
    {
      "type": "stroke",
      "stroke": {
        "points": [[120, 200], [128, 214], [140, 230]],
        "color": { "r": 24, "g": 28, "b": 36 },
        "width": 6
      }
    },
    {
      "type": "shape",
      "shape": {
        "kind": "rectangle",
        "start": [300, 180],
        "end": [520, 360],
        "color": { "r": 46, "g": 124, "b": 214 },
        "width": 4,
        "filled": false
      }
    }
  ]
}
```

## Campos

| Campo | Tipo | Descripción |
|---|---|---|
| `format` | string | Siempre `visionboard-project`. Distingue el archivo de cualquier otro JSON |
| `version` | entero | Versión del formato. Si no coincide, la carga se rechaza |
| `created_at` | string | Fecha ISO 8601. Informativo |
| `canvas.width/height` | entero | Tamaño del lienzo en píxeles |
| `canvas.background` | objeto RGB | Color de fondo, necesario para reproducir los borrados |
| `commands` | lista | Acciones en orden de aplicación |

## Tipos de comando

| `type` | Contenido | Qué hace |
|---|---|---|
| `stroke` | `stroke` | Polilínea a mano alzada |
| `erase` | `stroke` | Igual que `stroke`, pero con el color de fondo |
| `shape` | `shape` | Figura: `line`, `rectangle`, `circle`, `arrow` |
| `clear` | `background` | Rellena el lienzo completo |

Las coordenadas son píxeles absolutos del lienzo. Al abrir un proyecto con otro
tamaño, la aplicación redimensiona el lienzo al del archivo: el contenido no se
escala, se vuelve a dibujar tal cual.

## Seguridad

La carga nunca usa `pickle` ni `eval`. Cada comando se reconstruye desde una
tabla explícita de tipos conocidos; un `type` desconocido o unos datos
incompletos producen un `ProjectError` y el proyecto no se carga a medias.
