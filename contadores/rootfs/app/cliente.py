"""Conexión TCP persistente con un conversor USR-DR134 (puente transparente).

Una conexión por conversor, reutilizada: el DR134 solo admite 4 clientes.
Los módulos que cuelgan del mismo conversor comparten cliente y sus
consultas van en serie (lock): el DR134 reenvía lo que llega del bus a
todos sus clientes TCP, así que con una conexión por módulo se pisarían
las respuestas. Entre tramas se guarda un silencio (`pausa_s`), que es lo
que delimita las tramas en Modbus RTU.

Ante cualquier fallo se cierra y se lanza ErrorConexion; el bucle del módulo
reintenta en su siguiente ciclo (el intervalo ya hace de espera).

Nota: una excepción Modbus (5 bytes) no completa el readexactly y acaba en
timeout; se pierde ese ciclo, aceptado por diseño (la trama pedida es fija).
"""
import asyncio


class ErrorConexion(Exception):
    pass


class ClienteDR134:
    def __init__(self, host: str, puerto: int, timeout_s: float = 3.0, pausa_s: float = 0.05):
        self.host = host
        self.puerto = puerto
        self.timeout_s = timeout_s
        self.pausa_s = pausa_s
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._bus_libre_en = 0.0  # instante (reloj del loop) desde el que se puede emitir

    @property
    def conectado(self) -> bool:
        return self._writer is not None

    async def cerrar(self) -> None:
        # Espera a la consulta en curso: puede ser la de otro módulo.
        async with self._lock:
            await self._cerrar()

    async def _cerrar(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError:
                pass
            self._reader = self._writer = None

    async def consultar(self, peticion: bytes, n_respuesta: int) -> bytes:
        async with self._lock:
            loop = asyncio.get_running_loop()
            espera = self._bus_libre_en - loop.time()
            if espera > 0:
                await asyncio.sleep(espera)
            try:
                if self._writer is None:
                    self._reader, self._writer = await asyncio.wait_for(
                        asyncio.open_connection(self.host, self.puerto), self.timeout_s
                    )
                self._writer.write(peticion)
                await asyncio.wait_for(self._writer.drain(), self.timeout_s)
                return await asyncio.wait_for(self._reader.readexactly(n_respuesta), self.timeout_s)
            except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as e:
                await self._cerrar()
                raise ErrorConexion(f"{self.host}:{self.puerto}: {e!r}") from e
            finally:
                self._bus_libre_en = loop.time() + self.pausa_s
