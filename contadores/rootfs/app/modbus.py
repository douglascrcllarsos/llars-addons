"""Framing Modbus RTU para leer el WJ69-485. Solo lectura (FC03): en este
add-on no existe la escritura al módulo por diseño (ver spec)."""

REG_CONTADORES = 32  # primer registro de los 16 contadores DI (base 0)
NUM_REGS = 32        # 16 contadores uint32 = 32 registros de 16 bits


class RespuestaInvalida(Exception):
    """La trama recibida no es una respuesta FC03 válida para lo pedido."""


def crc16(data: bytes) -> int:
    """CRC-16/MODBUS (polinomio 0xA001, inicial 0xFFFF)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def longitud_respuesta(cantidad: int) -> int:
    """Bytes totales de una respuesta FC03 de `cantidad` registros."""
    return 3 + cantidad * 2 + 2


def peticion_fc03(direccion: int, registro: int, cantidad: int) -> bytes:
    pdu = bytes([direccion, 0x03]) + registro.to_bytes(2, "big") + cantidad.to_bytes(2, "big")
    return pdu + crc16(pdu).to_bytes(2, "little")


def parsear_fc03(trama: bytes, direccion: int, cantidad: int) -> list[int]:
    """Valida y desmonta una respuesta FC03. Devuelve los registros de 16 bits."""
    if len(trama) < 5:
        raise RespuestaInvalida(f"trama de {len(trama)} bytes")
    if trama[0] != direccion:
        raise RespuestaInvalida(f"dirección {trama[0]}, esperada {direccion}")
    if trama[1] == 0x83:
        raise RespuestaInvalida(f"excepción modbus {trama[2]}")
    if trama[1] != 0x03:
        raise RespuestaInvalida(f"función {trama[1]:#x}")
    if len(trama) != longitud_respuesta(cantidad) or trama[2] != cantidad * 2:
        raise RespuestaInvalida(f"longitud {len(trama)} / byte count {trama[2]}")
    if int.from_bytes(trama[-2:], "little") != crc16(trama[:-2]):
        raise RespuestaInvalida("CRC")
    return [int.from_bytes(trama[3 + 2 * i : 5 + 2 * i], "big") for i in range(cantidad)]


def contadores_cdab(regs: list[int]) -> list[int]:
    """Pares de registros -> uint32 CDAB (palabra de menor peso primero)."""
    return [regs[2 * i] | (regs[2 * i + 1] << 16) for i in range(len(regs) // 2)]
