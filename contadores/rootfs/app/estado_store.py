"""Persistencia del acumulado en /data/estado.json (dato de facturación).

Escritura atómica (tmp + os.replace + fsync). Un fichero ilegible se aparta
como .corrupto-<ts> en vez de sobreescribirse: quien llama decide cómo avisar.
"""
import json
import os
import time

VERSION = 1
_VACIO = {"version": VERSION, "modulos": {}}


def cargar(ruta: str) -> tuple[dict, bool]:
    """Devuelve (estado, corrupto)."""
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or d.get("version") != VERSION or not isinstance(d.get("modulos"), dict):
            raise ValueError("formato desconocido")
        for mod in d["modulos"].values():
            if not isinstance(mod, dict) or not isinstance(mod.get("canales"), dict):
                raise ValueError("formato desconocido")
            for canal in mod["canales"].values():
                if not isinstance(canal, dict):
                    raise ValueError("formato desconocido")
                for campo in ("pulsos_acum", "ultima_lectura"):
                    v = canal.get(campo)
                    if not isinstance(v, int) or isinstance(v, bool):
                        raise ValueError("formato desconocido")
        return d, False
    except FileNotFoundError:
        return dict(_VACIO, modulos={}), False
    except (ValueError, OSError):
        try:
            os.replace(ruta, f"{ruta}.corrupto-{int(time.time())}")
        except OSError:
            pass
        return dict(_VACIO, modulos={}), True


def guardar(estado: dict, ruta: str) -> None:
    tmp = f"{ruta}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ruta)
