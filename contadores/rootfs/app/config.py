"""Carga y validación de /data/options.json.

El schema del Supervisor ya garantiza tipos y rangos; aquí se añaden las
reglas semánticas (unicidad de ids, factores con sentido). Los `id` son la
identidad estable de entidades y estado: renombrar `nombre` es gratis,
cambiar `id` arranca de cero.
"""
import json
from dataclasses import dataclass

from acumulador import ORDEN_CANALES


@dataclass(frozen=True)
class Canal:
    id: str
    nombre: str
    litros_por_pulso: float
    offset_litros: float


@dataclass(frozen=True)
class Modulo:
    id: str
    nombre: str
    host: str
    puerto: int
    direccion: int
    canales: tuple[Canal, ...]


@dataclass(frozen=True)
class Config:
    modulos: tuple[Modulo, ...]
    intervalo_s: int


def cargar(ruta: str = "/data/options.json") -> Config:
    with open(ruta, encoding="utf-8") as f:
        return validar(json.load(f))


def validar(crudo: dict) -> Config:
    modulos = []
    ids_mod = set()
    hosts_puertos = set()
    for m in crudo.get("modulos", []):
        if m["id"] in ids_mod:
            raise ValueError(f"id de módulo repetido: {m['id']}")
        ids_mod.add(m["id"])
        host, puerto = m["host"], int(m["puerto"])
        if (host, puerto) in hosts_puertos:
            raise ValueError(f"host:puerto repetido entre módulos: {host}:{puerto}")
        hosts_puertos.add((host, puerto))
        canales = []
        ids_can = set()
        for c in m.get("canales", []):
            if c["id"] not in ORDEN_CANALES:
                raise ValueError(f"canal desconocido en {m['id']}: {c['id']}")
            if c["id"] in ids_can:
                raise ValueError(f"canal repetido en {m['id']}: {c['id']}")
            ids_can.add(c["id"])
            lpp = float(c["litros_por_pulso"])
            off = float(c.get("offset_litros", 0.0))
            if lpp <= 0:
                raise ValueError(f"litros_por_pulso debe ser > 0 ({m['id']}/{c['id']})")
            if off < 0:
                raise ValueError(f"offset_litros no puede ser negativo ({m['id']}/{c['id']})")
            canales.append(Canal(c["id"], c["nombre"], lpp, off))
        modulos.append(
            Modulo(m["id"], m["nombre"], m["host"], int(m["puerto"]), int(m["direccion"]), tuple(canales))
        )
    return Config(tuple(modulos), int(crudo.get("intervalo_s", 30)))
