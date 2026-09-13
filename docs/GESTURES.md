# Sistema de gestos

## Cómo decido si un dedo está estirado

Para los cuatro dedos largos comparo alturas: la punta (TIP) debe estar por
encima de la articulación media (PIP). En coordenadas de imagen la Y crece
hacia abajo, así que "por encima" significa `tip.y < pip.y - margen`.

El pulgar no se puede medir así porque se abre de lado, no hacia arriba. Para
él comparo el alcance desde la muñeca: si la punta está claramente más lejos de
la muñeca que la articulación IP, el pulgar está abierto. Esta medida funciona
igual con la mano izquierda y con la derecha, sin casos especiales.

## Normalización

Todos los umbrales se dividen entre `hand_scale`, la distancia entre la muñeca
y el nudillo del dedo medio. Sin normalizar, una pinza hecha lejos de la cámara
nunca se detectaría: en píxeles todo sería más pequeño.

## Tabla de reglas

| Prioridad | Gesto | Condición | Acción |
|---|---|---|---|
| 100 | 🤏 `PINCH` | pinza < 0.35 y anular/meñique recogidos | Ajustar grosor |
| 90 | 👍 `THUMBS_UP` | solo el pulgar estirado y apuntando arriba | Confirmar |
| 80 | ☝️ `DRAW` | índice estirado, medio/anular/meñique recogidos | Dibujar |
| 70 | ✌️ `SELECT` | índice y medio estirados, anular/meñique recogidos | Mover cursor |
| 60 | 🖐️ `OPEN_PALM` | 4 o más dedos estirados | Pausar |
| 50 | ✊ `FIST` | ningún dedo estirado | Borrador |
| — | `NONE` | no hay mano o no encaja ninguna regla | Nada |

La prioridad importa porque las poses se solapan. La pinza tiene el índice casi
estirado, así que si se evaluara después de `DRAW` nunca se reconocería.

`OPEN_PALM` pide 4 dedos y no 5 porque el pulgar es el que peor se mide cuando
la palma está de frente a la cámara.

## Estabilización

Un gesto no se acepta hasta verse en `stable_frames` lecturas seguidas (3 por
defecto). A 30 FPS son unos 100 ms: imperceptible al usar, suficiente para que
un frame ruidoso no cambie de herramienta en mitad de un trazo.

## Agregar un gesto nuevo

```python
from app.gestures.rules import GestureRule
from app.gestures.gesture_types import Gesture
from app.vision.landmarks import Finger


class ReglaCuernos(GestureRule):
    gesture = Gesture.NONE   # Antes: agregar el valor al Enum Gesture
    priority = 75            # Entre SELECT (70) y DRAW (80)

    def matches(self, snapshot) -> bool:
        return (
            snapshot.is_extended(Finger.INDEX)
            and snapshot.is_extended(Finger.PINKY)
            and not snapshot.is_extended(Finger.MIDDLE)
            and not snapshot.is_extended(Finger.RING)
        )


classifier.register(ReglaCuernos())
```

No hay que tocar el clasificador, ni el controlador, ni la interfaz. Solo
falta mapear el gesto a una acción en `gestures/actions.py`.

## Ajustes útiles

En `data/config/settings.json`, sección `gestures`:

| Ajuste | Por defecto | Para qué sirve |
|---|---|---|
| `pinch_ratio` | 0.35 | Subirlo hace la pinza más fácil de activar |
| `extended_margin` | 0.02 | Holgura al decidir si un dedo está estirado |
| `stable_frames` | 3 | Más alto = más estable pero con más retardo |
