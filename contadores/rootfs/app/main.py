"""Llars Contadores — lectura de WJ69-485 vía DR134 y publicación MQTT.

Un bucle asyncio por módulo. La lógica delicada vive en modbus.py y
acumulador.py (puros); aquí solo se orquesta.
"""
import asyncio
import logging
import os
import signal
import time

import aiomqtt

import config as config_mod
import estado_store
import modbus
import mqtt_pub
from acumulador import ORDEN_CANALES, Acumulador
from cliente import ClienteDR134, ErrorConexion

LOG = logging.getLogger("contadores")
RUTA_ESTADO = "/data/estado.json"
FALLOS_PARA_DESCONECTADO = 3


async def _esperar(parada: asyncio.Event, segundos: float) -> None:
    try:
        await asyncio.wait_for(parada.wait(), timeout=segundos)
    except asyncio.TimeoutError:
        pass


async def bucle_modulo(mod, acum, pub, intervalo_s, parada, estado, ruta_estado, cliente=None):
    cli = cliente or ClienteDR134(mod.host, mod.puerto)
    peticion = modbus.peticion_fc03(mod.direccion, modbus.REG_CONTADORES, modbus.NUM_REGS)
    n_resp = modbus.longitud_respuesta(modbus.NUM_REGS)
    fallos = 0
    conexion_publicada: bool | None = None
    previos: dict[str, tuple[float, float]] = {}  # canal -> (litros, ts) para el caudal

    if acum.ultimo_corte_ts:
        await pub.ultimo_corte(mod.id, acum.ultimo_corte_ts)

    while not parada.is_set():
        try:
            crudo = await cli.consultar(peticion, n_resp)
            regs = modbus.parsear_fc03(crudo, mod.direccion, modbus.NUM_REGS)
            valores = modbus.contadores_cdab(regs)
        except (ErrorConexion, modbus.RespuestaInvalida) as e:
            await cli.cerrar()
            fallos += 1
            if fallos == FALLOS_PARA_DESCONECTADO:
                LOG.warning("[%s] sin lectura tras %d intentos (%s): desconectado", mod.id, fallos, e)
                await pub.conexion(mod.id, False)
                conexion_publicada = False
            await _esperar(parada, intervalo_s)
            continue

        if fallos >= FALLOS_PARA_DESCONECTADO:
            LOG.info("[%s] lectura recuperada tras %d fallos", mod.id, fallos)
        fallos = 0
        if conexion_publicada is not True:
            await pub.conexion(mod.id, True)
            conexion_publicada = True

        ahora = time.time()
        lecturas = {c.id: valores[ORDEN_CANALES.index(c.id)] for c in mod.canales}
        res = acum.aplicar(lecturas, int(ahora))

        # Persistir ANTES de publicar: lo guardado debe ser siempre >= lo
        # publicado. Si se publicara primero y el proceso muriera antes de
        # guardar, tras rearrancar se publicaría un total menor que el
        # retenido y HA (total_increasing) lo sumaría entero como pico falso.
        if res["corte"] or any(v["delta"] or v["primera"] for v in res["canales"].values()):
            estado["modulos"][mod.id] = acum.a_dict()
            estado_store.guardar(estado, ruta_estado)

        if res["corte"]:
            LOG.warning(
                "[%s] reinicio del módulo detectado (corte de alimentación): "
                "hubo un hueco de consumo sin contar; acumulado conservado", mod.id)
            await pub.ultimo_corte(mod.id, acum.ultimo_corte_ts)

        for c in mod.canales:
            pulsos = acum.pulsos(c.id)
            litros = c.offset_litros + pulsos * c.litros_por_pulso
            r = res["canales"][c.id]
            prev = previos.get(c.id)
            if prev is None or r["primera"] or res["corte"] or ahora <= prev[1]:
                caudal = 0.0
            else:
                caudal = max(0.0, (litros - prev[0]) / ((ahora - prev[1]) / 60))
            previos[c.id] = (litros, ahora)
            await pub.canal(mod.id, c.id, litros, pulsos, caudal)

        await _esperar(parada, intervalo_s)


async def _correr_modulos(cfg, acums, pub, parada, estado):
    tareas = [
        asyncio.create_task(
            bucle_modulo(m, acums[m.id], pub, cfg.intervalo_s, parada, estado, RUTA_ESTADO),
            name=f"modulo-{m.id}")
        for m in cfg.modulos
    ]
    centinela = asyncio.create_task(parada.wait())
    hechas, pendientes = await asyncio.wait([*tareas, centinela], return_when=asyncio.FIRST_COMPLETED)
    for t in pendientes:
        t.cancel()
    await asyncio.gather(*pendientes, return_exceptions=True)
    for t in hechas:
        if t is not centinela and t.exception() is not None:
            raise t.exception()


async def principal() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    cfg = config_mod.cargar()
    if not cfg.modulos:
        LOG.warning("sin módulos configurados: edita la pestaña Configuración del add-on")
    else:
        LOG.info(
            "arranque: %d módulo(s), %d canal(es) declarados, sondeo cada %d s",
            len(cfg.modulos), sum(len(m.canales) for m in cfg.modulos), cfg.intervalo_s)
        for m in cfg.modulos:
            LOG.info("  [%s] %s — %s:%d dir %d, canales %s",
                     m.id, m.nombre, m.host, m.puerto, m.direccion,
                     ",".join(c.id for c in m.canales) or "(ninguno)")

    estado, corrupto = estado_store.cargar(RUTA_ESTADO)
    if corrupto:
        LOG.critical(
            "estado.json ILEGIBLE: apartado como .corrupto-* y el acumulado arranca "
            "desde la lectura actual de cada módulo. Es un dato de facturación: "
            "restaurar de un backup del add-on si procede.")
    acums = {m.id: Acumulador(estado["modulos"].get(m.id)) for m in cfg.modulos}

    parada = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(s, parada.set)

    while not parada.is_set():
        try:
            async with aiomqtt.Client(
                hostname=os.environ.get("MQTT_HOST", "core-mosquitto"),
                port=int(os.environ.get("MQTT_PORT", "1883")),
                username=os.environ.get("MQTT_USER") or None,
                password=os.environ.get("MQTT_PASSWORD") or None,
                will=aiomqtt.Will(mqtt_pub.TOPIC_DISPONIBLE, "offline", retain=True),
            ) as cli:
                pub = mqtt_pub.Publicador(cli)
                await pub.descubrir(cfg)
                await pub.disponible("online")
                LOG.info("MQTT conectado y discovery publicado")
                await _correr_modulos(cfg, acums, pub, parada, estado)
                await pub.disponible("offline")
        except aiomqtt.MqttError as e:
            LOG.warning("MQTT caído (%s); reintento en 5 s", e)
            await _esperar(parada, 5)

    for m in cfg.modulos:
        estado["modulos"][m.id] = acums[m.id].a_dict()
    if cfg.modulos:
        estado_store.guardar(estado, RUTA_ESTADO)
    LOG.info("parada limpia")


if __name__ == "__main__":
    asyncio.run(principal())
