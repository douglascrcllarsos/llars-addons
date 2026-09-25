from acumulador import ORDEN_CANALES, Acumulador


def test_orden_canales_del_wj69():
    assert ORDEN_CANALES[:4] == ("A0", "B0", "A1", "B1")
    assert ORDEN_CANALES[15] == "B7"
    assert len(ORDEN_CANALES) == 16


def test_primera_lectura_arranca_sin_corte():
    a = Acumulador()
    res = a.aplicar({"A3": 16}, ts=1000)
    assert res == {"corte": False, "canales": {"A3": {"delta": 0, "primera": True}}}
    assert a.pulsos("A3") == 16
    assert a.ultimo_corte_ts is None


def test_delta_normal():
    a = Acumulador({"canales": {"A3": {"pulsos_acum": 16, "ultima_lectura": 16}}})
    res = a.aplicar({"A3": 18}, ts=2000)
    assert res["canales"]["A3"] == {"delta": 2, "primera": False}
    assert not res["corte"]
    assert a.pulsos("A3") == 18


def test_reinicio_del_modulo_es_corte():
    # El módulo perdió los contadores (corte de luz) y ha contado 3 desde entonces
    a = Acumulador({"canales": {"A3": {"pulsos_acum": 700, "ultima_lectura": 700}}})
    res = a.aplicar({"A3": 3}, ts=3000)
    assert res["corte"]
    assert res["canales"]["A3"]["delta"] == 3
    assert a.pulsos("A3") == 703
    assert a.ultimo_corte_ts == 3000


def test_corte_no_confunde_canales_quietos():
    # A3 activo delata el corte; B0 estaba a 0 y sigue a 0 (0 >= 0, sin corte propio)
    a = Acumulador({"canales": {
        "A3": {"pulsos_acum": 100, "ultima_lectura": 100},
        "B0": {"pulsos_acum": 0, "ultima_lectura": 0},
    }})
    res = a.aplicar({"A3": 1, "B0": 0}, ts=4000)
    assert res["corte"]
    assert a.pulsos("A3") == 101
    assert a.pulsos("B0") == 0


def test_lectura_igual_no_cambia_nada():
    a = Acumulador({"canales": {"A3": {"pulsos_acum": 50, "ultima_lectura": 50}}})
    res = a.aplicar({"A3": 50}, ts=5000)
    assert res["canales"]["A3"]["delta"] == 0
    assert not res["corte"]


def test_a_dict_ida_y_vuelta():
    a = Acumulador()
    a.aplicar({"A0": 7, "B0": 2}, ts=6000)
    b = Acumulador(a.a_dict())
    assert b.pulsos("A0") == 7
    b.aplicar({"A0": 9, "B0": 2}, ts=7000)
    assert b.pulsos("A0") == 9
