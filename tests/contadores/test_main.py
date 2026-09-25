import asyncio

import config
import main
import modbus
from acumulador import Acumulador
from cliente import ErrorConexion


class PubFake:
    def __init__(self):
        self.eventos = []

    async def conexion(self, mod_id, ok):
        self.eventos.append(("conexion", mod_id, ok))

    async def ultimo_corte(self, mod_id, ts):
        self.eventos.append(("corte", mod_id, ts))

    async def canal(self, mod_id, canal_id, litros, pulsos, caudal):
        self.eventos.append(("canal", mod_id, canal_id, litros, pulsos, caudal))


class ClienteFake:
    """Devuelve respuestas FC03 bien formadas a partir de listas de 16 valores."""

    def __init__(self, tandas):
        self.tandas = list(tandas)

    async def consultar(self, peticion, n):
        if not self.tandas:
            raise ErrorConexion("fake agotado")
        tanda = self.tandas.pop(0)
        if tanda is None:
            raise ErrorConexion("fake caído")
        datos = b"".join(
            (v & 0xFFFF).to_bytes(2, "big") + (v >> 16).to_bytes(2, "big") for v in tanda
        )
        cuerpo = bytes([4, 0x03, len(datos)]) + datos
        return cuerpo + modbus.crc16(cuerpo).to_bytes(2, "little")

    async def cerrar(self):
        pass


def _mod():
    return config.validar({
        "modulos": [{
            "id": "sala", "nombre": "Sala", "host": "127.0.0.1", "puerto": 502,
            "direccion": 4,
            "canales": [{"id": "A3", "nombre": "Fría cocina", "litros_por_pulso": 1.0, "offset_litros": 610.0}],
        }],
        "intervalo_s": 30,
    }).modulos[0]


def _correr(tandas, acum, estado, tmp_path, ciclos):
    pub = PubFake()
    parada = asyncio.Event()
    cli = ClienteFake(tandas + [None] * 5)

    async def caso():
        tarea = asyncio.create_task(main.bucle_modulo(
            _mod(), acum, pub, 0.01, parada, estado, str(tmp_path / "estado.json"), cliente=cli))
        while len(cli.tandas) > 5 and ciclos:
            await asyncio.sleep(0.005)
        await asyncio.sleep(0.03)
        parada.set()
        await tarea

    asyncio.run(caso())
    return pub


def test_ciclo_normal_publica_y_persiste(tmp_path):
    # canal A3 = índice 6 (A0,B0,A1,B1,A2,B2,A3,...)
    tanda = [0] * 16
    tanda[6] = 16
    acum = Acumulador()
    estado = {"version": 1, "modulos": {}}
    pub = _correr([tanda], acum, estado, tmp_path, ciclos=1)
    assert ("conexion", "sala", True) in pub.eventos
    canales = [e for e in pub.eventos if e[0] == "canal"]
    assert canales[0] == ("canal", "sala", "A3", 626.0, 16, 0.0)  # 610 + 16, caudal 0 (primera)
    assert estado["modulos"]["sala"]["canales"]["A3"]["pulsos_acum"] == 16
    assert (tmp_path / "estado.json").exists()


def test_corte_se_detecta_y_publica(tmp_path):
    acum = Acumulador({"canales": {"A3": {"pulsos_acum": 16, "ultima_lectura": 16}}})
    estado = {"version": 1, "modulos": {}}
    tanda = [0] * 16
    tanda[6] = 2  # el módulo se reinició y lleva 2
    pub = _correr([tanda], acum, estado, tmp_path, ciclos=1)
    cortes = [e for e in pub.eventos if e[0] == "corte"]
    assert len(cortes) == 1
    canales = [e for e in pub.eventos if e[0] == "canal"]
    assert canales[0][3] == 628.0  # 610 + 16 + 2
    assert acum.ultimo_corte_ts is not None


def test_fallos_repetidos_marcan_desconectado(tmp_path):
    acum = Acumulador()
    estado = {"version": 1, "modulos": {}}
    pub = _correr([None, None, None], acum, estado, tmp_path, ciclos=3)
    assert ("conexion", "sala", False) in pub.eventos
