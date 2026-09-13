# Arquitectura de VisionBoard AI

Documento donde dejo escrito **por qué** el proyecto está organizado así, para
cuando lo abra dentro de unos meses y no me acuerde.

## Principio que gobierna todo

Cada capa conoce únicamente a la siguiente, y las fronteras entre capas son
dataclasses propias, nunca tipos de una librería externa. Esto tiene tres
consecuencias prácticas:

1. MediaPipe aparece en **un solo archivo** (`vision/hand_detector.py`).
2. El motor de dibujo no importa PySide6, así que se puede probar sin ventana.
3. La interfaz no calcula nada: pregunta y muestra.

## Flujo de datos

```
┌──────────────┐   BGR    ┌──────────────┐   RGB    ┌──────────────────┐
│ CameraManager│ ───────► │ VisionWorker │ ───────► │   HandDetector   │
│  (OpenCV)    │          │  (QThread)   │          │   (MediaPipe)    │
└──────────────┘          └──────┬───────┘          └────────┬─────────┘
                                 │                           │
                                 │        DetectionResult    │
                                 │ ◄─────────────────────────┘
                                 │
                          FramePacket (señal Qt)
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ BoardController  │
                        └────────┬─────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
  GestureClassifier      GestureStabilizer        resolve_action
   (reglas + prioridad)   (N frames iguales)      (Gesture → Action)
          │                                              │
          └──────────────────────┬───────────────────────┘
                                 ▼
                        ┌──────────────────┐
                        │      Tool        │  press / move / release
                        └────────┬─────────┘
                                 │ Command
                                 ▼
                        ┌──────────────────┐
                        │  DrawingBoard    │  lienzo NumPy + HistoryStack
                        └────────┬─────────┘
                                 │ ndarray RGB
                                 ▼
                        ┌──────────────────┐
                        │    BoardView     │  QImage → pantalla
                        └──────────────────┘
```

## Responsabilidad de cada módulo

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `utils/exceptions` | Jerarquía de errores propia | — |
| `utils/paths` | Rutas del proyecto y validación de escritura | exceptions |
| `utils/logging_config` | Logging con archivo rotativo | paths |
| `config/settings` | Ajustes tipados y su validación | exceptions |
| `config/storage` | Cargar y guardar la configuración (JSON atómico) | settings |
| `camera/camera_manager` | Abrir, leer, espejar y liberar la webcam | config, OpenCV |
| `vision/landmarks` | `Point`, `HandLandmarks`, `DetectionResult` | — |
| `vision/geometry` | Distancias, escala, dedos estirados, pinza, mapeo | landmarks |
| `vision/smoothing` | Filtro EMA del puntero | — |
| `vision/hand_detector` | Envoltura de MediaPipe | landmarks, config |
| `vision/overlay` | Dibuja el esqueleto en el preview | landmarks, OpenCV |
| `gestures/features` | Snapshot numérico de la mano | geometry |
| `gestures/rules` | Una clase por gesto, con prioridad | features |
| `gestures/classifier` | Evalúa reglas y estabiliza en el tiempo | rules |
| `gestures/actions` | Mapa gesto → acción | gesture_types |
| `board/strokes` | Color, trazo, figura (datos puros) | — |
| `board/renderer` | Rasteriza sobre NumPy | strokes, OpenCV |
| `board/commands` | Patrón Command serializable | renderer |
| `board/history` | Deshacer/rehacer con cursor | commands |
| `board/canvas` | Motor de dibujo | renderer, history |
| `tools/*` | Strategy: eventos de puntero → comandos | board |
| `services/*` | PNG, proyectos `.vbai`, FPS | board |
| `ui/*` | Presentación y cableado de señales | todo lo anterior |

## Decisiones de diseño

### 1. Deshacer por comandos, no por bitmaps

Un lienzo de 1280×720×3 pesa 2.6 MB. Con 300 pasos de historial serían ~800 MB
de memoria. Guardando el comando (puntos, color, grosor) el historial pesa
kilobytes y deshacer es re-renderizar la lista activa sobre un lienzo limpio,
que en OpenCV cuesta pocos milisegundos.

Beneficio extra: un comando serializable es exactamente lo que necesita el
formato de proyecto y, más adelante, el reconocimiento de figuras.

### 2. Reglas de gestos como clases con prioridad

La alternativa era un `if/elif` de seis ramas. El problema no es la estética:
varias poses se **solapan**. Una pinza tiene el índice casi estirado, así que
debe evaluarse antes que "dibujar". Con prioridades explícitas ese orden es un
dato visible y no un accidente del orden en que escribí los `if`.

Agregar un gesto nuevo = una clase más y `classifier.register(...)`.

### 3. Estabilizador temporal

MediaPipe cambia de opinión entre frames. Sin histéresis, un frame ruidoso en
mitad de un trazo cambiaría de herramienta. El estabilizador exige N lecturas
iguales seguidas (3 por defecto) antes de aceptar un gesto: a 30 FPS eso son
100 ms, imperceptible al usar, suficiente para filtrar el ruido.

### 4. Hilo aparte para cámara y detección

Leer un frame y pasarlo por MediaPipe cuesta entre 20 y 60 ms. En el hilo de la
interfaz eso bloquearía el repintado y la ventana se sentiría trabada. El
`VisionWorker` es un `QThread` que emite señales; Qt las entrega de forma segura
al hilo principal, así que no necesito mutexes.

### 5. Normalizar por el tamaño de la mano

Todos los umbrales de gestos se dividen entre `hand_scale` (muñeca → nudillo
medio). Sin eso, una pinza lejos de la cámara nunca se detectaría, porque en
píxeles todo es más pequeño.

### 6. Entrada de ratón además de gestos

`BoardView` emite eventos de puntero que el controlador trata igual que los
del dedo. Así la aplicación es usable sin webcam y toda la cadena de dibujo se
puede ejercitar en pruebas y en máquinas sin cámara.

## Riesgos técnicos y cómo los manejo

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Cámara ocupada o inexistente | La app no arranca | `CameraError` con mensaje claro; la ventana sigue usable con ratón |
| MediaPipe no instalado | Fallo al importar | Import perezoso convertido en `VisionError` legible |
| Temblor del dedo | Trazos dentados | Filtro EMA + filtro de distancia mínima entre puntos |
| Gestos ambiguos | Acciones no deseadas | Prioridades explícitas + estabilizador de N frames |
| FPS bajos | Trazo entrecortado | `model_complexity=0`, buffer de cámara en 1, una sola conversión BGR→RGB por frame |
| Cámara sin liberar al cerrar | Webcam bloqueada | `closeEvent` para el hilo y libera antes de destruir widgets |
| Archivo de proyecto corrupto o malicioso | Fallo o ejecución de código | JSON validado por campos, tabla explícita de tipos, nunca `pickle` ni `eval` |
| Sobrescritura accidental de archivos | Pérdida de trabajo | `prepare_output_path` valida extensión, crea directorios y respeta `overwrite` |

## Preparado para la fase de IA

Lo que ya está listo para enchufar modelos sin reescribir nada:

- Los trazos son listas de puntos con timestamp implícito de orden: entrada
  directa para un clasificador de figuras o de escritura.
- `SelectorTool` delimita la región a analizar.
- `Command` es serializable, así que un modelo puede **sustituir** un
  `StrokeCommand` imperfecto por un `ShapeCommand` perfecto y el historial lo
  trata igual que cualquier otra acción.
- El registro de herramientas y el registro de reglas de gestos aceptan
  elementos nuevos en caliente.
