import asyncio

import pytest

from cliente import ClienteDR134, ErrorConexion


async def _servidor(respuestas: list[bytes]):
    """Servidor fake: por cada petición recibida envía la siguiente respuesta."""
    recibidas = []

    async def maneja(reader, writer):
        while respuestas:
            datos = await reader.read(64)
            if not datos:
                break
            recibidas.append(datos)
            writer.write(respuestas.pop(0))
            await writer.drain()
        writer.close()

    srv = await asyncio.start_server(maneja, "127.0.0.1", 0)
    puerto = srv.sockets[0].getsockname()[1]
    return srv, puerto, recibidas


def test_consulta_y_reuso_de_conexion():
    async def caso():
        srv, puerto, recibidas = await _servidor([b"\x01" * 8, b"\x02" * 8])
        cli = ClienteDR134("127.0.0.1", puerto, timeout_s=1.0)
        r1 = await cli.consultar(b"peticion-1", 8)
        r2 = await cli.consultar(b"peticion-2", 8)
        assert (r1, r2) == (b"\x01" * 8, b"\x02" * 8)
        assert cli.conectado
        assert recibidas == [b"peticion-1", b"peticion-2"]
        await cli.cerrar()
        srv.close()
        await srv.wait_closed()

    asyncio.run(caso())


def test_timeout_cierra_y_lanza():
    async def caso():
        srv, puerto, _ = await _servidor([])  # jamás responde
        cli = ClienteDR134("127.0.0.1", puerto, timeout_s=0.2)
        with pytest.raises(ErrorConexion):
            await cli.consultar(b"hola", 8)
        assert not cli.conectado
        srv.close()
        await srv.wait_closed()

    asyncio.run(caso())


def test_reconecta_tras_caida():
    async def caso():
        srv1, puerto, _ = await _servidor([b"\x0a" * 8])
        cli = ClienteDR134("127.0.0.1", puerto, timeout_s=0.5)
        assert await cli.consultar(b"a", 8) == b"\x0a" * 8
        srv1.close()
        await srv1.wait_closed()
        with pytest.raises(ErrorConexion):
            await cli.consultar(b"b", 8)
        # el DR134 "vuelve" en el mismo puerto
        srv2 = await asyncio.start_server(
            lambda r, w: _responde(r, w, b"\x0b" * 8), "127.0.0.1", puerto)
        assert await cli.consultar(b"c", 8) == b"\x0b" * 8
        await cli.cerrar()
        srv2.close()
        await srv2.wait_closed()

    async def _responde(reader, writer, resp):
        await reader.read(64)
        writer.write(resp)
        await writer.drain()
        writer.close()  # cierra para que wait_closed() no cuelgue esperando al peer

    asyncio.run(caso())


def test_puerto_cerrado_lanza():
    async def caso():
        cli = ClienteDR134("127.0.0.1", 1, timeout_s=0.5)
        with pytest.raises(ErrorConexion):
            await cli.consultar(b"x", 8)

    asyncio.run(caso())


def test_eof_a_mitad_de_trama_lanza():
    async def caso():
        async def maneja(reader, writer):
            await reader.read(64)
            writer.write(b"\x01\x03")  # menos bytes de los pedidos
            await writer.drain()
            writer.close()

        srv = await asyncio.start_server(maneja, "127.0.0.1", 0)
        puerto = srv.sockets[0].getsockname()[1]
        cli = ClienteDR134("127.0.0.1", puerto, timeout_s=1.0)
        with pytest.raises(ErrorConexion):
            await cli.consultar(b"peticion", 8)
        assert not cli.conectado
        srv.close()
        await srv.wait_closed()

    asyncio.run(caso())


async def _bus_lento(retardo_s: float):
    """Bus fake: contesta a cada petición, tras `retardo_s`, con su primer
    byte repetido 8 veces. Anota lo recibido y los instantes de E/S."""
    recibidas, t_respuesta, t_peticion = [], [], []
    loop = asyncio.get_running_loop()

    async def maneja(reader, writer):
        while True:
            datos = await reader.read(64)
            if not datos:
                break
            t_peticion.append(loop.time())
            recibidas.append(datos)
            await asyncio.sleep(retardo_s)
            writer.write(datos[:1] * 8)
            await writer.drain()
            t_respuesta.append(loop.time())
        writer.close()

    srv = await asyncio.start_server(maneja, "127.0.0.1", 0)
    puerto = srv.sockets[0].getsockname()[1]
    return srv, puerto, recibidas, t_peticion, t_respuesta


def test_consultas_concurrentes_no_se_pisan():
    # Dos módulos colgando del mismo conversor comparten cliente: la segunda
    # petición no puede salir al bus hasta que la primera tenga su respuesta.
    async def caso():
        srv, puerto, recibidas, _, _ = await _bus_lento(0.05)
        cli = ClienteDR134("127.0.0.1", puerto, timeout_s=1.0, pausa_s=0)
        r2, r3 = await asyncio.gather(
            cli.consultar(b"\x02-sur-b", 8), cli.consultar(b"\x03-sur-a", 8))
        assert (r2, r3) == (b"\x02" * 8, b"\x03" * 8)
        assert recibidas == [b"\x02-sur-b", b"\x03-sur-a"]
        await cli.cerrar()
        srv.close()
        await srv.wait_closed()

    asyncio.run(caso())


def test_cerrar_no_corta_una_consulta_ajena_en_curso():
    # Un módulo que descarta su trama cierra la conexión compartida: no debe
    # tumbar la lectura que el otro módulo tiene a medias.
    async def caso():
        srv, puerto, _, _, _ = await _bus_lento(0.1)
        cli = ClienteDR134("127.0.0.1", puerto, timeout_s=1.0, pausa_s=0)
        consulta = asyncio.create_task(cli.consultar(b"\x02-sur-b", 8))
        await asyncio.sleep(0.03)  # la petición ya está en el bus
        await cli.cerrar()
        assert await consulta == b"\x02" * 8
        assert not cli.conectado
        srv.close()
        await srv.wait_closed()

    asyncio.run(caso())


def test_silencio_en_el_bus_entre_tramas():
    # Modbus RTU delimita las tramas por silencio: tras una respuesta, la
    # siguiente petición espera `pausa_s` aunque se pida de inmediato.
    async def caso():
        srv, puerto, _, t_peticion, t_respuesta = await _bus_lento(0)
        cli = ClienteDR134("127.0.0.1", puerto, timeout_s=1.0, pausa_s=0.05)
        await cli.consultar(b"\x02-sur-b", 8)
        await cli.consultar(b"\x03-sur-a", 8)
        assert t_peticion[1] - t_respuesta[0] >= 0.045
        await cli.cerrar()
        srv.close()
        await srv.wait_closed()

    asyncio.run(caso())
