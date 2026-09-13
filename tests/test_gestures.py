"""Pruebas del reconocimiento de gestos.

Son las pruebas más importantes del proyecto: si un gesto se confunde con
otro, la aplicación dibuja cuando no debe o borra sin que yo se lo pida.
"""

from __future__ import annotations

import pytest
from conftest import make_hand, make_pinch_hand

from app.gestures.actions import BoardAction, resolve_action
from app.gestures.classifier import GestureClassifier, GestureStabilizer
from app.gestures.gesture_types import Gesture
from app.gestures.rules import GestureRule


@pytest.fixture
def clasificador() -> GestureClassifier:
    return GestureClassifier()


class TestClasificacion:
    def test_sin_mano_devuelve_none(self, clasificador: GestureClassifier) -> None:
        lectura = clasificador.classify(None)
        assert lectura.gesture is Gesture.NONE
        assert not lectura.has_hand

    def test_indice_levantado_es_dibujar(self, clasificador: GestureClassifier) -> None:
        assert clasificador.classify(make_hand(index=True)).gesture is Gesture.DRAW

    def test_indice_y_medio_es_seleccionar(self, clasificador: GestureClassifier) -> None:
        mano = make_hand(index=True, middle=True)
        assert clasificador.classify(mano).gesture is Gesture.SELECT

    def test_puño_es_borrador(self, clasificador: GestureClassifier) -> None:
        assert clasificador.classify(make_hand()).gesture is Gesture.FIST

    def test_mano_abierta_es_pausa(self, clasificador: GestureClassifier) -> None:
        mano = make_hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
        assert clasificador.classify(mano).gesture is Gesture.OPEN_PALM

    def test_pulgar_arriba_es_confirmar(self, clasificador: GestureClassifier) -> None:
        assert clasificador.classify(make_hand(thumb=True)).gesture is Gesture.THUMBS_UP

    def test_pinza_gana_sobre_dibujar(self, clasificador: GestureClassifier) -> None:
        """La pinza tiene el índice casi estirado; su prioridad debe imponerse."""
        assert clasificador.classify(make_pinch_hand()).gesture is Gesture.PINCH

    def test_la_lectura_conserva_el_snapshot(self, clasificador: GestureClassifier) -> None:
        lectura = clasificador.classify(make_hand(index=True))
        assert lectura.snapshot is not None
        assert lectura.snapshot.extended_count == 1


class TestExtensibilidad:
    def test_puedo_registrar_una_regla_nueva(self, clasificador: GestureClassifier) -> None:
        """Compruebo que agregar un gesto no exige tocar el clasificador."""

        class ReglaTodoEsPausa(GestureRule):
            gesture = Gesture.OPEN_PALM
            priority = 999

            def matches(self, snapshot: object) -> bool:
                return True

        antes = len(clasificador.rules)
        clasificador.register(ReglaTodoEsPausa())
        assert len(clasificador.rules) == antes + 1
        assert clasificador.rules[0].priority == 999
        assert clasificador.classify(make_hand(index=True)).gesture is Gesture.OPEN_PALM


class TestEstabilizador:
    def test_necesita_varios_frames_para_confirmar(self) -> None:
        estabilizador = GestureStabilizer(required_frames=3)
        assert estabilizador.update(Gesture.DRAW) is Gesture.NONE
        assert estabilizador.update(Gesture.DRAW) is Gesture.NONE
        assert estabilizador.update(Gesture.DRAW) is Gesture.DRAW

    def test_un_frame_ruidoso_no_cambia_el_gesto(self) -> None:
        estabilizador = GestureStabilizer(required_frames=3)
        for _ in range(3):
            estabilizador.update(Gesture.DRAW)
        assert estabilizador.update(Gesture.FIST) is Gesture.DRAW
        assert estabilizador.update(Gesture.DRAW) is Gesture.DRAW

    def test_reset_vuelve_a_none(self) -> None:
        estabilizador = GestureStabilizer(1)
        estabilizador.update(Gesture.DRAW)
        estabilizador.reset()
        assert estabilizador.current is Gesture.NONE

    def test_frames_invalidos_fallan(self) -> None:
        with pytest.raises(ValueError):
            GestureStabilizer(0)


class TestAcciones:
    @pytest.mark.parametrize(
        ("gesto", "accion"),
        [
            (Gesture.DRAW, BoardAction.DRAW),
            (Gesture.FIST, BoardAction.ERASE),
            (Gesture.OPEN_PALM, BoardAction.PAUSE),
            (Gesture.THUMBS_UP, BoardAction.CONFIRM),
            (Gesture.PINCH, BoardAction.ADJUST),
            (Gesture.SELECT, BoardAction.HOVER),
            (Gesture.NONE, BoardAction.IDLE),
        ],
    )
    def test_mapeo_por_defecto(self, gesto: Gesture, accion: BoardAction) -> None:
        assert resolve_action(gesto) is accion

    def test_puedo_pasar_mi_propio_mapeo(self) -> None:
        personalizado = {Gesture.FIST: BoardAction.PAUSE}
        assert resolve_action(Gesture.FIST, personalizado) is BoardAction.PAUSE
