import pytest

import config


def _crudo():
    return {
        "modulos": [
            {
                "id": "sala",
                "nombre": "Sala de contadores",
                "host": "192.168.1.50",
                "puerto": 502,
                "direccion": 7,
                "canales": [
                    {"id": "A3", "nombre": "Agua fría cocina", "litros_por_pulso": 1.0, "offset_litros": 500.0},
                ],
            }
        ],
        "intervalo_s": 30,
    }


def test_config_valida():
    cfg = config.validar(_crudo())
    assert cfg.intervalo_s == 30
    (m,) = cfg.modulos
    assert (m.id, m.host, m.puerto, m.direccion) == ("sala", "192.168.1.50", 502, 7)
    (c,) = m.canales
    assert (c.id, c.litros_por_pulso, c.offset_litros) == ("A3", 1.0, 500.0)


def test_sin_modulos_es_valido():
    cfg = config.validar({"modulos": [], "intervalo_s": 60})
    assert cfg.modulos == ()


@pytest.mark.parametrize(
    "romper, texto",
    [
        (lambda d: d["modulos"].append(dict(d["modulos"][0])), "repetido"),
        (lambda d: d["modulos"].append(dict(d["modulos"][0], id="sala2")), "host:puerto"),
        (lambda d: d["modulos"][0]["canales"][0].update(id="C9"), "desconocido"),
        (lambda d: d["modulos"][0]["canales"].append(dict(d["modulos"][0]["canales"][0])), "repetido"),
        (lambda d: d["modulos"][0]["canales"][0].update(litros_por_pulso=0), "litros_por_pulso"),
        (lambda d: d["modulos"][0]["canales"][0].update(offset_litros=-1), "offset_litros"),
    ],
)
def test_config_invalida(romper, texto):
    d = _crudo()
    romper(d)
    with pytest.raises(ValueError, match=texto):
        config.validar(d)


def test_offset_opcional_a_cero():
    d = _crudo()
    del d["modulos"][0]["canales"][0]["offset_litros"]
    cfg = config.validar(d)
    assert cfg.modulos[0].canales[0].offset_litros == 0.0
