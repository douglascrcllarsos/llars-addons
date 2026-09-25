import json

import estado_store


def test_inexistente_devuelve_vacio_sin_corrupcion(tmp_path):
    estado, corrupto = estado_store.cargar(str(tmp_path / "no-existe.json"))
    assert estado == {"version": 1, "modulos": {}}
    assert not corrupto


def test_ida_y_vuelta(tmp_path):
    ruta = str(tmp_path / "estado.json")
    d = {"version": 1, "modulos": {"sm": {"ultimo_corte_ts": None, "canales": {"A3": {"pulsos_acum": 18, "ultima_lectura": 18}}}}}
    estado_store.guardar(d, ruta)
    cargado, corrupto = estado_store.cargar(ruta)
    assert cargado == d and not corrupto
    assert not (tmp_path / "estado.json.tmp").exists()


def test_corrupto_se_aparta_y_se_avisa(tmp_path):
    ruta = tmp_path / "estado.json"
    ruta.write_text("{esto no es json", encoding="utf-8")
    estado, corrupto = estado_store.cargar(str(ruta))
    assert estado == {"version": 1, "modulos": {}}
    assert corrupto
    assert not ruta.exists()  # apartado, no borrado
    apartados = list(tmp_path.glob("estado.json.corrupto-*"))
    assert len(apartados) == 1


def test_version_desconocida_es_corrupto(tmp_path):
    ruta = tmp_path / "estado.json"
    ruta.write_text(json.dumps({"version": 99}), encoding="utf-8")
    estado, corrupto = estado_store.cargar(str(ruta))
    assert corrupto and estado["modulos"] == {}


def test_pulsos_acum_no_entero_es_corrupto(tmp_path):
    ruta = tmp_path / "estado.json"
    d = {"version": 1, "modulos": {"sm": {"canales": {"A3": {"pulsos_acum": "x", "ultima_lectura": 18}}}}}
    ruta.write_text(json.dumps(d), encoding="utf-8")
    estado, corrupto = estado_store.cargar(str(ruta))
    assert estado == {"version": 1, "modulos": {}}
    assert corrupto
    assert not ruta.exists()  # apartado, no borrado
    apartados = list(tmp_path.glob("estado.json.corrupto-*"))
    assert len(apartados) == 1
