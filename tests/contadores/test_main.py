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
        cuerpo = bytes([7, 0x03, len(datos)]) + datos
        return cuerpo + modbus.crc16(cuerpo).to_bytes(2, "little")

    async def cerrar(self):
        pass


def _mod():
    return config.validar({
        "modulos": [{
            "id": "sala", "nombre": "Sala", "host": "127.0.0.1", "puerto": 502,
            "direccion": 7,
            "canales": [{"id": "A3", "nombre": "Fría cocina", "litros_por_pulso": 1.0, "offset_litros": 500.0}],
        }],
        "intervalo_s": 30,
    }).modulos[0]


def _correr(tandas, acum, estado, tmp_path):
    pub = PubFake()
    parada = asyncio.Event()
    cli = ClienteFake(tandas + [None] * 5)

    async def caso():
        tarea = asyncio.create_task(main.bucle_modulo(
            _mod(), acum, pub, 0.01, parada, estado, str(tmp_path / "estado.json"), cliente=cli))
        while len(cli.tandas) > 5:
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
    pub = _correr([tanda], acum, estado, tmp_path)
    assert ("conexion", "sala", True) in pub.eventos
    canales = [e for e in pub.eventos if e[0] == "canal"]
    assert canales[0] == ("canal", "sala", "A3", 516.0, 16, 0.0)  # 500 + 16, caudal 0 (primera)
    assert estado["modulos"]["sala"]["canales"]["A3"]["pulsos_acum"] == 16
    assert (tmp_path / "estado.json").exists()


def test_corte_se_detecta_y_publica(tmp_path):
    acum = Acumulador({"canales": {"A3": {"pulsos_acum": 16, "ultima_lectura": 16}}})
    estado = {"version": 1, "modulos": {}}
    tanda = [0] * 16
    tanda[6] = 2  # el módulo se reinició y lleva 2
    pub = _correr([tanda], acum, estado, tmp_path)
    cortes = [e for e in pub.eventos if e[0] == "corte"]
    assert len(cortes) == 1
    canales = [e for e in pub.eventos if e[0] == "canal"]
    assert canales[0][3] == 518.0  # 500 + 16 + 2
    assert acum.ultimo_corte_ts is not None


def test_fallos_repetidos_marcan_desconectado(tmp_path):
    acum = Acumulador()
    estado = {"version": 1, "modulos": {}}
    pub = _correr([None, None, None], acum, estado, tmp_path)
    assert ("conexion", "sala", False) in pub.eventos


def test_dos_modulos_comparten_conversor_sin_pisarse(tmp_path, monkeypatch):
    # Un "DR134" fake con dos WJ69 en su bus (dir. 2 y 3). Como el real,
    # reenvía cada respuesta del bus a TODOS sus clientes TCP: con una
    # conexión por módulo, cada uno recibiría también la trama del otro.
    contadores = {2: [20 + k for k in range(16)], 3: [30 + k for k in range(16)]}
    escritores = []

    async def maneja(reader, writer):
        escritores.append(writer)
        while True:
            pet = await reader.read(64)
            if not pet:
                break
            await asyncio.sleep(0.01)  # lo que tarda el módulo en contestar
            datos = b"".join(
                (v & 0xFFFF).to_bytes(2, "big") + (v >> 16).to_bytes(2, "big")
                for v in contadores[pet[0]])
            cuerpo = bytes([pet[0], 0x03, len(datos)]) + datos
            trama = cuerpo + modbus.crc16(cuerpo).to_bytes(2, "little")
            for w in escritores:
                w.write(trama)
        writer.close()

    pub = PubFake()
    estado = {"version": 1, "modulos": {}}
    monkeypatch.setattr(main, "RUTA_ESTADO", str(tmp_path / "estado.json"))

    async def caso():
        srv = await asyncio.start_server(maneja, "127.0.0.1", 0)
        puerto = srv.sockets[0].getsockname()[1]
        canal = {"id": "A0", "nombre": "Fría", "litros_por_pulso": 1.0}
        cfg = config.validar({
            "modulos": [
                {"id": "sur_b", "nombre": "Sur B", "host": "127.0.0.1", "puerto": puerto,
                 "direccion": 2, "canales": [canal]},
                {"id": "sur_a", "nombre": "Sur A", "host": "127.0.0.1", "puerto": puerto,
                 "direccion": 3, "canales": [canal]},
            ],
            "intervalo_s": 5,
        })
        acums = {m.id: Acumulador() for m in cfg.modulos}
        parada = asyncio.Event()
        tarea = asyncio.create_task(main._correr_modulos(cfg, acums, pub, parada, estado))
        await asyncio.sleep(0.4)
        parada.set()
        await tarea
        srv.close()

    asyncio.run(caso())
    assert len(escritores) == 1  # una sola conexión TCP al conversor
    canales = {(e[1], e[2]): e[4] for e in pub.eventos if e[0] == "canal"}
    assert canales == {("sur_b", "A0"): 20, ("sur_a", "A0"): 30}
    assert ("conexion", "sur_b", True) in pub.eventos
    assert ("conexion", "sur_a", True) in pub.eventos
