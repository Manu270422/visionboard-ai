# VisionBoard AI

Pizarrón virtual inteligente controlado por gestos de la mano. La cámara detecta
mi mano en tiempo real con MediaPipe, un clasificador traduce la pose de los
dedos a un gesto y ese gesto se convierte en una acción de dibujo. Puedo
escribir en la pizarra con el dedo índice en el aire, sin tocar la pantalla.

---

## Características

- Detección de mano en tiempo real con MediaPipe (21 landmarks).
- Seis gestos reconocidos: dibujar, seleccionar, borrar, pausar, confirmar y ajustar grosor.
- Motor de dibujo propio, independiente de la interfaz gráfica.
- Deshacer y rehacer basados en comandos, no en copias de imagen.
- Herramientas: lápiz, borrador, selección, línea, rectángulo, círculo y flecha.
- Paleta de colores y grosor ajustable (por interfaz o con el gesto de pinza).
- Exportación a PNG y formato de proyecto propio `.vbai` reabrible y editable.
- Captura y detección en un hilo aparte: la interfaz nunca se congela.
- Modo ratón: la aplicación funciona completa aunque no haya cámara.
- 106 pruebas automatizadas con pytest.

## Stack

Python 3.12 · OpenCV · MediaPipe · NumPy · PySide6 · pytest · Ruff · Black · mypy

## Instalación

```bash
git clone <url-del-repositorio>
cd visionboard-ai

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Para desarrollar y ejecutar las pruebas:

```bash
pip install -r requirements-dev.txt
```

## Ejecución

```bash
python -m app.main
```

Opciones disponibles:

| Opción | Qué hace |
|---|---|
| `--camera 1` | Usa otra cámara cuando hay varias conectadas |
| `--no-camera` | Arranca solo con ratón, sin abrir la webcam |
| `--width 1920 --height 1080` | Cambia el tamaño del lienzo |
| `--log-level DEBUG` | Sube el detalle del log |

## Gestos

| Gesto | Pose | Acción |
|---|---|---|
| ☝️ | Índice levantado | Dibujar con la herramienta activa |
| ✌️ | Índice y medio | Mover el cursor sin pintar |
| ✊ | Puño | Borrador temporal |
| 🖐️ | Mano abierta | Pausar la interacción |
| 👍 | Pulgar arriba | Confirmar el trazo o figura en curso |
| 🤏 | Pinza índice-pulgar | Ajustar el grosor según la apertura |

Un gesto solo se acepta después de verse en varios frames seguidos, para que un
frame ruidoso no cambie de herramienta en mitad de un trazo.

## Atajos de teclado

| Atajo | Acción |
|---|---|
| `Ctrl+Z` / `Ctrl+Y` | Deshacer / rehacer |
| `Ctrl+S` | Guardar proyecto `.vbai` |
| `Ctrl+E` | Exportar PNG |
| `Ctrl+O` | Abrir proyecto |
| `Ctrl+Shift+C` | Limpiar la pizarra |
| `P` `E` `S` `L` `R` `C` `F` | Lápiz, borrador, selección, línea, rectángulo, círculo, flecha |

## Arquitectura

El flujo de datos es una sola dirección, sin ciclos:

```
Cámara ──► Hilo de visión ──► Detector ──► Clasificador ──► Acción
                                                              │
                        Interfaz ◄── Pizarra ◄── Herramienta ◄┘
```

Cada capa depende solo de la siguiente y las fronteras son dataclasses propias:

- **`app/camera/`** abre y libera la webcam.
- **`app/vision/`** es el único lugar que conoce MediaPipe; entrega `DetectionResult`.
- **`app/gestures/`** convierte landmarks en un `Gesture` y este en un `BoardAction`.
- **`app/tools/`** traduce eventos de puntero en `Command`.
- **`app/board/`** aplica comandos sobre un lienzo NumPy. No conoce Qt.
- **`app/ui/`** solo muestra; la lógica vive en `BoardController`.

El detalle está en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Estructura del proyecto

```
visionboard-ai/
├── app/
│   ├── main.py              Punto de entrada
│   ├── config/              Ajustes tipados y persistencia JSON
│   ├── camera/              CameraManager
│   ├── vision/              Landmarks, geometría, detector, suavizado, overlay
│   ├── gestures/            Características, reglas, clasificador, acciones
│   ├── board/               Trazos, renderer, comandos, historial, motor
│   ├── tools/               Lápiz, borrador, selección, figuras, registro
│   ├── services/            Exportación, proyectos, rendimiento
│   ├── ui/                  Tema, hilo de visión, controlador, widgets
│   └── utils/               Errores, rutas, logging
├── assets/                  Recursos estáticos
├── data/                    Dibujos, configuración y logs generados
├── docs/                    Documentación técnica
├── tests/                   Suite de pytest
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Pruebas y calidad

```bash
pytest              # 106 pruebas
ruff check app tests
black --check app tests
mypy app
```

Las pruebas cubren geometría, clasificación de gestos, estabilizador, historial,
herramientas, motor de dibujo, serialización y servicios. No se prueba la cámara
física: se usan manos sintéticas construidas en `tests/conftest.py`.

## Generar el ejecutable (.exe)

Para distribuir la aplicación sin que quien la reciba tenga que instalar Python
ni dependencias, se empaqueta con [PyInstaller](https://pyinstaller.org):

```bash
.venv\Scripts\activate
pip install pyinstaller
pyinstaller VisionBoardAI.spec
```

El `.exe` resultante queda en `dist/VisionBoardAI.exe` (un solo archivo, ~280
MB porque incluye MediaPipe completo). Es portable: se puede copiar a otra
carpeta o computador con Windows sin instalar nada más. La primera vez que se
abre tarda unos segundos en arrancar porque se descomprime a una carpeta
temporal; las siguientes veces es más rápido.

`app/utils/paths.py` detecta cuando corre empaquetado (`sys.frozen`) y guarda
`data/` (configuración, dibujos, logs) junto al `.exe` en vez de en una carpeta
temporal que se borraría al cerrar la aplicación.

## Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| "No pude abrir la cámara 0" | Otra aplicación la está usando o falta permiso | Cierra Zoom/Teams/navegador y revisa los permisos de cámara del sistema |
| La ventana abre pero el preview está negro | Índice de cámara equivocado | Prueba `--camera 1`, `--camera 2` |
| El gesto no se reconoce | Poca luz o mano fuera del encuadre | Mejora la iluminación y mantén la mano dentro del cuadro |
| El trazo tiembla | Suavizado bajo | Sube `vision.smoothing` en `data/config/settings.json` |
| No llego a las esquinas | Margen activo muy alto | Baja `vision.active_margin` |
| Pocos FPS | Modelo pesado o resolución alta | Deja `vision.model_complexity` en 0 y baja la resolución de cámara |
| `ModuleNotFoundError: mediapipe` | Entorno virtual sin activar | Activa `.venv` y reinstala los requirements |

## Roadmap

- [x] **Fase 1** · Estructura, configuración, cámara y ventana
- [x] **Fase 2** · MediaPipe, landmarks y detección
- [x] **Fase 3** · Clasificación de gestos y feedback visual
- [x] **Fase 4** · Pizarra, dibujo, borrador, colores y grosor
- [x] **Fase 5** · Herramientas, figuras, selección, deshacer y rehacer
- [x] **Fase 6** · Exportación, persistencia y configuración
- [x] **Fase 7** · Testing, logging, rendimiento y documentación
- [x] **Fase 8** · Funciones de IA: reconocimiento de figuras y conversión de trazos imperfectos a figuras perfectas

### Fase 8 en detalle

`app/ai/shape_recognizer.py` analiza un `Stroke` con geometría clásica de
OpenCV (`fitLine`, `approxPolyDP`, `minEnclosingCircle`) y decide si se parece
lo bastante a una línea, un círculo o un rectángulo. No hay modelo entrenado:
con trazos de unos pocos cientos de puntos, ajustar geometría es más rápido,
más predecible y no añade dependencias nuevas.

Para usarlo: selecciona la región con la herramienta de selección (`S`) y pulsa
**"Reconocer figura ✨"** en el panel lateral (o `Ctrl+Shift+A`). Cada trazo que
quede completamente dentro de la selección y se parezca a una figura conocida
se sustituye por su `ShapeCommand` equivalente, conservando color y grosor; el
resto de trazos queda intacto. La sustitución es un paso más del historial, así
que `Ctrl+Z` la deshace igual que cualquier otra acción.

La escritura a texto queda fuera de esta fase: reconocer letras a mano alzada
con calidad aceptable pide un modelo de OCR (una dependencia nueva y bastante
más pesada), y el resto de la arquitectura de la Fase 8 ya deja el terreno
listo para añadirlo el día que se decida pagar ese costo.

## Licencia

MIT. Ver [LICENSE](LICENSE).
