"""Hilo de captura y detección.

Esta es la decisión de arquitectura que hace que la aplicación se sienta
fluida: leer un frame y pasarlo por MediaPipe cuesta entre 20 y 60 ms. Si eso
pasara en el hilo de la interfaz, Qt no podría repintar y la ventana se
congelaría en cada frame.

Por eso la cámara y la detección viven en un QThread y se comunican con la
interfaz solo por señales, que Qt entrega de forma segura al hilo principal.
"""

from __future__ import annotations

import cv2
from PySide6.QtCore import QObject, QThread, Signal

from app.camera.camera_manager import CameraManager
from app.config.settings import AppSettings
from app.services.performance import FpsMeter, Stopwatch
from app.utils.exceptions import CameraError, FrameError, VisionError
from app.utils.logging_config import get_logger
from app.vision.frame import FramePacket
from app.vision.hand_detector import HandDetector

logger = get_logger(__name__)

#: Frames fallidos seguidos que tolero antes de declarar la cámara caída.
_MAX_CONSECUTIVE_FAILURES = 15


class VisionWorker(QThread):
    """Captura, detecta y emite paquetes de frame hasta que le pido parar."""

    frameReady = Signal(object)  # FramePacket
    cameraOpened = Signal(int, int)  # ancho, alto reales
    failed = Signal(str)  # mensaje de error legible

    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._camera = CameraManager(settings.camera)
        self._detector = HandDetector(settings.vision)
        self._fps = FpsMeter(window=30)
        self._running = False

    # ------------------------------------------------------------------ API

    def stop(self) -> None:
        """Pido al bucle que termine y espero a que el hilo cierre de verdad.

        Es importante esperar: si la ventana se destruye mientras el hilo sigue
        leyendo, Qt aborta el proceso y la cámara queda tomada por el sistema.
        """
        self._running = False
        if self.isRunning():
            self.wait(3000)

    # ----------------------------------------------------------------- ciclo

    def run(self) -> None:  # noqa: D102 - el ciclo se documenta por dentro
        """Bucle del hilo: abrir, capturar, detectar, emitir, liberar."""
        try:
            self._camera.open()
            self._detector.open()
        except (CameraError, VisionError) as error:
            logger.error("No pude iniciar la captura: %s", error)
            self.failed.emit(str(error))
            self._shutdown()
            return

        self.cameraOpened.emit(self._camera.actual_width, self._camera.actual_height)
        self._running = True
        failures = 0

        # Intervalo objetivo entre frames; si el procesamiento ya tardó más,
        # no duermo nada y dejo que el hilo siga a su ritmo real.
        interval_ms = max(1, int(1000 / max(1, self._settings.camera.fps)))

        while self._running:
            try:
                bgr = self._camera.read()
                failures = 0
            except FrameError as error:
                failures += 1
                if failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.error("Cámara perdida tras %d fallos: %s", failures, error)
                    self.failed.emit("Se perdió la señal de la cámara.")
                    break
                self.msleep(interval_ms)
                continue
            except CameraError as error:
                self.failed.emit(str(error))
                break

            with Stopwatch() as watch:
                # Convierto una sola vez: este mismo array RGB lo reutilizo
                # para detectar y para mostrar el preview en la interfaz.
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                try:
                    detection = self._detector.process(rgb)
                except VisionError as error:
                    logger.warning("Frame descartado por el detector: %s", error)
                    continue

            packet = FramePacket(
                frame_rgb=rgb,
                detection=detection,
                fps=self._fps.tick(),
                process_ms=watch.elapsed_ms,
            )
            self.frameReady.emit(packet)

            remaining = interval_ms - int(watch.elapsed_ms)
            if remaining > 0:
                self.msleep(remaining)

        self._shutdown()

    def _shutdown(self) -> None:
        """Libero cámara y modelo pase lo que pase."""
        self._running = False
        self._detector.close()
        self._camera.release()
        logger.info("Hilo de visión finalizado.")
