"""Caché con último valor conocido: responde rápido y sigue funcionando si la fuente se cae."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

from .fuentes import Tasa, obtener_bancos, obtener_bcv, obtener_p2p

TTL = {"bcv": 30 * 60, "p2p": 3 * 60, "bancos": 30 * 60}  # segundos


def _ruta_cache() -> Path:
    base = os.environ.get("TASAS_VE_CACHE") or os.path.join(Path.home(), ".cache", "tasas-ve", "ultimo.json")
    return Path(base)


class Servicio:
    def __init__(self, bcv: Callable[[], list[Tasa]] = obtener_bcv,
                 p2p: Callable[[str], Tasa] = lambda lado: obtener_p2p(lado),
                 bancos: Callable[[], dict] = obtener_bancos,
                 ruta: Path | None = None, reloj: Callable[[], float] = time.time):
        self._bcv, self._p2p, self._bancos, self._reloj = bcv, p2p, bancos, reloj
        self._ruta = ruta or _ruta_cache()
        self._mem: dict[str, tuple[float, list[dict]]] = {}
        self._cargar()

    # ---- disco
    def _cargar(self):
        try:
            self._mem = {k: (v["t"], v["tasas"]) for k, v in json.loads(self._ruta.read_text("utf-8")).items()}
        except Exception:
            self._mem = {}

    def _guardar(self):
        try:
            self._ruta.parent.mkdir(parents=True, exist_ok=True)
            self._ruta.write_text(json.dumps({k: {"t": t, "tasas": v} for k, (t, v) in self._mem.items()},
                                             ensure_ascii=False, indent=2), "utf-8")
        except Exception:
            pass  # la caché en disco es opcional

    # ---- lógica
    def _obtener(self, clave: str, ttl: int, fn: Callable[[], list], crudo: bool = False) -> dict:
        ahora = self._reloj()
        guardado = self._mem.get(clave)
        if guardado and ahora - guardado[0] < ttl:
            return {"tasas": guardado[1], "desde_cache": True, "aviso": ""}
        try:
            tasas = [t if crudo else t.dict() for t in fn()]
            self._mem[clave] = (ahora, tasas)
            self._guardar()
            return {"tasas": tasas, "desde_cache": False, "aviso": ""}
        except Exception as e:
            if guardado:
                return {"tasas": guardado[1], "desde_cache": True,
                        "aviso": f"La fuente no respondió ({type(e).__name__}); se muestra el último valor guardado."}
            raise RuntimeError(f"No se pudo obtener la tasa y no hay valor guardado: {e}") from e

    def bcv(self) -> dict:
        return self._obtener("bcv", TTL["bcv"], self._bcv)

    def p2p(self, lado: str = "SELL") -> dict:
        lado = lado.upper()
        return self._obtener(f"p2p_{lado}", TTL["p2p"], lambda: [self._p2p(lado)])

    def bancos(self) -> dict:
        """Tasas informativas por banco (compra y venta) y su promedio."""
        r = self._obtener("bancos", TTL["bancos"], lambda: [self._bancos()], crudo=True)
        datos = dict(r["tasas"][0])
        datos.update(desde_cache=r["desde_cache"], aviso=r["aviso"])
        return datos

    def tasa(self, moneda: str, fuente: str = "bcv") -> tuple[float, dict]:
        moneda, fuente = moneda.upper(), fuente.lower()
        if fuente == "p2p":
            r = self.p2p()
        elif fuente == "bcv":
            r = self.bcv()
        else:
            raise ValueError("fuente debe ser 'bcv' o 'p2p'")
        for t in r["tasas"]:
            if t["moneda"] == moneda or (moneda == "USD" and t["moneda"] == "USDT"):
                return t["bs"], r
        raise ValueError(f"La fuente {fuente} no publica {moneda}")

    def convertir(self, monto: float, de: str, a: str, fuente: str = "bcv") -> dict:
        de, a = de.upper(), a.upper()
        if de == a:
            return {"monto": monto, "de": de, "a": a, "resultado": round(monto, 2), "tasa_usada": 1.0, "fuente": fuente}
        if de == "VES":
            bs, r = self.tasa(a, fuente)
            res = monto / bs
        elif a == "VES":
            bs, r = self.tasa(de, fuente)
            res = monto * bs
        else:  # cruce entre divisas pasando por bolívares
            bs_de, r = self.tasa(de, fuente)
            bs_a, _ = self.tasa(a, fuente)
            bs, res = bs_de / bs_a, monto * bs_de / bs_a
        return {"monto": monto, "de": de, "a": a, "resultado": round(res, 2), "tasa_usada": round(bs, 6),
                "fuente": fuente, "obtenida": r["tasas"][0]["obtenida"], "aviso": r["aviso"]}

    def brecha(self) -> dict:
        oficial, _ = self.tasa("USD", "bcv")
        mercado, _ = self.tasa("USD", "p2p")
        return {"bcv_usd": oficial, "p2p_usdt": mercado,
                "brecha_pct": round((mercado - oficial) / oficial * 100, 2)}
