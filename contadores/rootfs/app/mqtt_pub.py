"""Descubrimiento y estados MQTT. Los payloads se construyen en funciones
puras (testadas); Publicador solo los empuja por aiomqtt.

unique_id deriva de los `id` de config (estables); `nombre` solo pinta.
object_id fija el entity_id al nombre a secas (sin el prefijo del device
que HA añade por defecto a las entidades MQTT con dispositivo).
"""
import json
import unicodedata
from datetime import datetime, timezone

from config import Config

PREFIJO = "llars_contadores"
TOPIC_DISPONIBLE = f"{PREFIJO}/estado"


def num_fmt(x: float) -> str:
    """Número compacto: 2 decimales máximo, sin relleno y sin notación
    científica (un total de millones de litros debe seguir siendo legible)."""
    texto = f"{x:.2f}".rstrip("0").rstrip(".")
    return texto or "0"


def _uid(mod_id: str, resto: str) -> str:
    return f"{PREFIJO}_{mod_id}_{resto}".lower()


def _slug(texto: str) -> str:
    """Nombre → object_id: minúsculas, sin acentos, no-alfanumérico a «_»."""
    plano = unicodedata.normalize("NFD", texto)
    plano = "".join(ch for ch in plano if not unicodedata.combining(ch))
    slug = "".join(ch if ch.isalnum() else "_" for ch in plano.lower())
    return "_".join(p for p in slug.split("_") if p)


def _dispositivo(mod) -> dict:
    return {
        "identifiers": [f"{PREFIJO}_{mod.id}"],
        "name": mod.nombre,
        "manufacturer": "Llars Sostenible",
        "model": "WJ69-485 via USR-DR134",
    }


def mensajes_descubrimiento(cfg: Config) -> list[tuple[str, str]]:
    """(topic, payload) de discovery; se publican todos con retain."""
    mensajes = []

    def sensor(dominio: str, uid: str, extra: dict) -> None:
        payload = {"unique_id": uid, "availability_topic": TOPIC_DISPONIBLE, **extra}
        mensajes.append((f"homeassistant/{dominio}/{uid}/config", json.dumps(payload, ensure_ascii=False)))

    for mod in cfg.modulos:
        dev = _dispositivo(mod)
        for c in mod.canales:
            base = f"{PREFIJO}/{mod.id}/{c.id}"
            sensor("sensor", _uid(mod.id, f"{c.id}_litros"), {
                "name": c.nombre, "object_id": _slug(c.nombre),
                "state_topic": f"{base}/litros",
                "device_class": "water", "state_class": "total_increasing",
                "unit_of_measurement": "L", "device": dev,
            })
            sensor("sensor", _uid(mod.id, f"{c.id}_pulsos"), {
                "name": f"{c.nombre} pulsos", "object_id": _slug(f"{c.nombre} pulsos"),
                "state_topic": f"{base}/pulsos",
                "state_class": "total_increasing", "icon": "mdi:counter",
                "entity_category": "diagnostic", "device": dev,
            })
            sensor("sensor", _uid(mod.id, f"{c.id}_caudal"), {
                "name": f"{c.nombre} caudal", "object_id": _slug(f"{c.nombre} caudal"),
                "state_topic": f"{base}/caudal",
                "unit_of_measurement": "L/min", "icon": "mdi:water-pump", "device": dev,
            })
        # Nombre corto en las de módulo: HA ya antepone el nombre del device
        # en el nombre visible; repetirlo aquí lo doblaba.
        sensor("binary_sensor", _uid(mod.id, "conexion"), {
            "name": "Conexión", "object_id": _slug(f"{mod.nombre} conexión"),
            "state_topic": f"{PREFIJO}/{mod.id}/conexion",
            "device_class": "connectivity", "entity_category": "diagnostic", "device": dev,
        })
        sensor("sensor", _uid(mod.id, "ultimo_corte"), {
            "name": "Último corte", "object_id": _slug(f"{mod.nombre} último corte"),
            "state_topic": f"{PREFIJO}/{mod.id}/ultimo_corte",
            "device_class": "timestamp", "entity_category": "diagnostic", "device": dev,
        })
    return mensajes


class Publicador:
    def __init__(self, cliente):
        self._c = cliente

    async def descubrir(self, cfg: Config) -> None:
        for topic, payload in mensajes_descubrimiento(cfg):
            await self._c.publish(topic, payload, retain=True)

    async def disponible(self, texto: str) -> None:
        await self._c.publish(TOPIC_DISPONIBLE, texto, retain=True)

    async def conexion(self, mod_id: str, ok: bool) -> None:
        await self._c.publish(f"{PREFIJO}/{mod_id}/conexion", "ON" if ok else "OFF", retain=True)

    async def ultimo_corte(self, mod_id: str, ts: int) -> None:
        iso = datetime.fromtimestamp(ts, timezone.utc).isoformat()
        await self._c.publish(f"{PREFIJO}/{mod_id}/ultimo_corte", iso, retain=True)

    async def canal(self, mod_id: str, canal_id: str, litros: float, pulsos: int, caudal: float) -> None:
        base = f"{PREFIJO}/{mod_id}/{canal_id}"
        await self._c.publish(f"{base}/litros", num_fmt(litros), retain=True)
        await self._c.publish(f"{base}/pulsos", str(pulsos), retain=True)
        await self._c.publish(f"{base}/caudal", num_fmt(caudal), retain=True)
