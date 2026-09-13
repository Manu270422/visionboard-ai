"""Pruebas de la geometría de la mano y del filtro de suavizado."""

from __future__ import annotations

import pytest
from conftest import make_hand, make_pinch_hand

from app.vision import geometry
from app.vision.landmarks import Finger, LandmarkIndex, Point
from app.vision.smoothing import PointSmoother


class TestDistancias:
    def test_distancia_simple(self) -> None:
        assert geometry.distance(Point(0, 0), Point(3, 4)) == pytest.approx(5.0)

    def test_punto_medio(self) -> None:
        medio = geometry.midpoint(Point(0, 0), Point(2, 4))
        assert (medio.x, medio.y) == (1.0, 2.0)

    def test_escala_de_mano_nunca_es_cero(self) -> None:
        """Una mano degenerada no debe provocar una división por cero."""
        degenerada = make_hand()
        puntos = list(degenerada.points)
        puntos[int(LandmarkIndex.MIDDLE_MCP)] = puntos[int(LandmarkIndex.WRIST)]
        plana = type(degenerada)(tuple(puntos), degenerada.handedness, degenerada.score)
        assert geometry.hand_scale(plana) > 0


class TestDedosEstirados:
    def test_indice_estirado(self) -> None:
        mano = make_hand(index=True)
        assert geometry.is_finger_extended(mano, Finger.INDEX)

    def test_indice_recogido(self) -> None:
        assert not geometry.is_finger_extended(make_hand(), Finger.INDEX)

    def test_pulgar_abierto_y_cerrado(self) -> None:
        assert geometry.is_finger_extended(make_hand(thumb=True), Finger.THUMB)
        assert not geometry.is_finger_extended(make_hand(), Finger.THUMB)

    def test_mano_abierta_reporta_cinco_dedos(self) -> None:
        mano = make_hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
        estado = geometry.extended_fingers(mano)
        assert sum(estado.values()) == 5

    def test_puño_no_reporta_dedos(self) -> None:
        assert sum(geometry.extended_fingers(make_hand()).values()) == 0


class TestPinza:
    def test_pinza_cerrada_da_valor_bajo(self) -> None:
        assert geometry.pinch_ratio(make_pinch_hand()) < 0.35

    def test_mano_abierta_da_valor_alto(self) -> None:
        mano = make_hand(thumb=True, index=True, middle=True, ring=True, pinky=True)
        assert geometry.pinch_ratio(mano) > 0.35

    def test_la_pinza_es_independiente_de_la_distancia(self) -> None:
        """Alejar la mano de la cámara no debe cambiar el ratio de pinza."""
        cercana = make_pinch_hand()
        lejana_puntos = tuple(Point(p.x * 0.5, p.y * 0.5, p.z) for p in cercana.points)
        lejana = type(cercana)(lejana_puntos, cercana.handedness, cercana.score)
        assert geometry.pinch_ratio(lejana) == pytest.approx(
            geometry.pinch_ratio(cercana), abs=1e-6
        )


class TestMapeoALienzo:
    def test_el_centro_cae_en_el_centro(self) -> None:
        # El lienzo va de 0 a ancho-1, así que el centro exacto es 639/2 = 319.5
        # y el redondeo lo lleva a 320.
        x, y = geometry.map_to_canvas(Point(0.5, 0.5), 640, 480, margin=0.1)
        assert (x, y) == (320, 240)

    def test_el_margen_alcanza_las_esquinas(self) -> None:
        """Con margen 0.1, el punto 0.1 debe llegar al borde del lienzo."""
        assert geometry.map_to_canvas(Point(0.1, 0.1), 640, 480, margin=0.1) == (0, 0)
        assert geometry.map_to_canvas(Point(0.9, 0.9), 640, 480, margin=0.1) == (639, 479)

    def test_fuera_de_rango_se_recorta(self) -> None:
        assert geometry.map_to_canvas(Point(-1.0, 2.0), 640, 480) == (0, 479)


class TestSuavizado:
    def test_la_primera_muestra_pasa_sin_filtrar(self) -> None:
        assert PointSmoother(0.3).update(10, 20) == (10.0, 20.0)

    def test_el_filtro_converge_al_objetivo(self) -> None:
        filtro = PointSmoother(0.5)
        filtro.update(0, 0)
        for _ in range(30):
            x, _y = filtro.update(100, 100)
        assert x == pytest.approx(100, abs=0.5)

    def test_reset_olvida_la_posicion_anterior(self) -> None:
        filtro = PointSmoother(0.2)
        filtro.update(0, 0)
        filtro.reset()
        assert filtro.update(50, 50) == (50.0, 50.0)

    def test_alpha_invalido_falla_al_construir(self) -> None:
        with pytest.raises(ValueError):
            PointSmoother(0.0)
