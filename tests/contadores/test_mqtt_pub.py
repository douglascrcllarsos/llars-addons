import json

import config
import mqtt_pub


def _cfg():
    return config.validar({
        "modulos": [{
            "id": "sala", "nombre": "Sala de contadores", "host": "192.168.1.50",
            "puerto": 502, "direccion": 4,
            "canales": [
                {"id": "A3", "nombre": "Agua fría cocina", "litros_por_pulso": 1.0, "offset_litros": 500.0},
                {"id": "B3", "nombre": "Agua caliente cocina", "litros_por_pulso": 1.0, "offset_litros": 0.0},
            ],
        }],
        "intervalo_s": 30,
    })


def test_solo_canales_declarados():
    mensajes = mqtt_pub.mensajes_descubrimiento(_cfg())
    # 3 sensores por canal declarado + conexión + último corte por módulo
    assert len(mensajes) == 3 * 2 + 2
    topics = [t for t, _ in mensajes]
    assert not any("/a0_" in t or "_a0_" in t for t in topics)


def test_payload_litros():
    mensajes = dict(mqtt_pub.mensajes_descubrimiento(_cfg()))
    topic = "homeassistant/sensor/llars_contadores_sala_a3_litros/config"
    p = json.loads(mensajes[topic])
    assert p["name"] == "Agua fría cocina"
    assert p["unique_id"] == "llars_contadores_sala_a3_litros"
    assert p["state_topic"] == "llars_contadores/sala/A3/litros"
    assert p["availability_topic"] == mqtt_pub.TOPIC_DISPONIBLE
    assert p["device_class"] == "water"
    assert p["state_class"] == "total_increasing"
    assert p["unit_of_measurement"] == "L"
    assert p["device"]["identifiers"] == ["llars_contadores_sala"]
    assert p["device"]["name"] == "Sala de contadores"


def test_payload_modulo():
    mensajes = dict(mqtt_pub.mensajes_descubrimiento(_cfg()))
    con = json.loads(mensajes["homeassistant/binary_sensor/llars_contadores_sala_conexion/config"])
    assert con["device_class"] == "connectivity"
    assert con["state_topic"] == "llars_contadores/sala/conexion"
    corte = json.loads(mensajes["homeassistant/sensor/llars_contadores_sala_ultimo_corte/config"])
    assert corte["device_class"] == "timestamp"


def test_num_fmt():
    assert mqtt_pub.num_fmt(628.0) == "628"
    assert mqtt_pub.num_fmt(1.256) == "1.26"
    assert mqtt_pub.num_fmt(0.0) == "0"
