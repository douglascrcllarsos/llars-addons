"""Acumulado de pulsos de UN módulo WJ69. Puro: sin E/S ni reloj propio.

El firmware V1.50 del WJ69 pierde los contadores DI en cada corte de
alimentación. Aquí vive el total real: si una lectura baja respecto a la
anterior, el módulo se reinició y la lectura nueva entera es incremento.
Los fallos de lectura no pasan por aquí: solo se aplican lecturas buenas.
"""

# Índice del uint32 en la respuesta FC03 (regs 32..63) -> id de canal
ORDEN_CANALES = tuple(f"{'AB'[k % 2]}{k // 2}" for k in range(16))


class Acumulador:
    def __init__(self, estado: dict | None = None):
        e = estado or {}
        self.canales: dict[str, dict] = {c: dict(v) for c, v in e.get("canales", {}).items()}
        self.ultimo_corte_ts: int | None = e.get("ultimo_corte_ts")

    def aplicar(self, lecturas: dict[str, int], ts: int) -> dict:
        """Aplica una tanda de lecturas buenas (canal -> valor crudo)."""
        corte = False
        canales = {}
        for canal, lectura in lecturas.items():
            st = self.canales.get(canal)
            if st is None:
                # Alta del canal: el arrastre previo se corrige con offset_litros
                self.canales[canal] = {"pulsos_acum": lectura, "ultima_lectura": lectura}
                canales[canal] = {"delta": 0, "primera": True}
                continue
            if lectura >= st["ultima_lectura"]:
                delta = lectura - st["ultima_lectura"]
            else:
                delta = lectura  # módulo reiniciado: lo contado desde el arranque
                corte = True
            st["pulsos_acum"] += delta
            st["ultima_lectura"] = lectura
            canales[canal] = {"delta": delta, "primera": False}
        if corte:
            self.ultimo_corte_ts = ts
        return {"corte": corte, "canales": canales}

    def pulsos(self, canal: str) -> int:
        return self.canales[canal]["pulsos_acum"]

    def a_dict(self) -> dict:
        return {"ultimo_corte_ts": self.ultimo_corte_ts, "canales": self.canales}
