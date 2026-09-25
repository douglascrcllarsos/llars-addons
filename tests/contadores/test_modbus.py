import pytest

import modbus


def test_crc16_vector_conocido():
    # Vector clásico de Modbus: 01 03 00 00 00 01 -> CRC 0x0A84 (en trama: 84 0A)
    assert modbus.crc16(bytes.fromhex("010300000001")) == 0x0A84


def test_peticion_fc03_wj69():
    # Ejemplo del datasheet WJ69: leer A0 = 01 03 00 20 00 02 + CRC
    trama = modbus.peticion_fc03(1, 32, 2)
    assert trama[:6] == bytes.fromhex("010300200002")
    assert len(trama) == 8
    crc = int.from_bytes(trama[6:], "little")
    assert crc == modbus.crc16(trama[:6])


def _respuesta(direccion: int, datos: bytes) -> bytes:
    cuerpo = bytes([direccion, 0x03, len(datos)]) + datos
    return cuerpo + modbus.crc16(cuerpo).to_bytes(2, "little")


def test_parsear_fc03_y_cdab_datasheet():
    # Respuesta del datasheet para A0: CA 90 FF FF = 0xFFFFCA90 (CDAB)
    regs = modbus.parsear_fc03(_respuesta(1, bytes.fromhex("CA90FFFF")), 1, 2)
    assert regs == [0xCA90, 0xFFFF]
    assert modbus.contadores_cdab(regs) == [0xFFFFCA90]


def test_parsear_16_contadores():
    datos = b"".join(
        (v & 0xFFFF).to_bytes(2, "big") + (v >> 16).to_bytes(2, "big")
        for v in range(100, 116)
    )
    regs = modbus.parsear_fc03(_respuesta(4, datos), 4, 32)
    assert modbus.contadores_cdab(regs) == list(range(100, 116))


@pytest.mark.parametrize(
    "trama, motivo",
    [
        (b"\x01\x03", "corta"),
        (_respuesta(2, bytes(8)), "otra dirección"),  # se parsea pidiendo dir 1
        (b"\x01\x83\x02\xc0\xf1", "excepción modbus"),
        (_respuesta(1, bytes(8))[:-1] + bytes([_respuesta(1, bytes(8))[-1] ^ 0xFF]), "crc malo"),
    ],
)
def test_parsear_rechaza(trama, motivo):
    with pytest.raises(modbus.RespuestaInvalida):
        modbus.parsear_fc03(trama, 1, 4)


def test_longitud_respuesta():
    assert modbus.longitud_respuesta(32) == 3 + 64 + 2
