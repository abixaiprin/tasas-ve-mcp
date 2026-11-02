"""Lectura de fuentes públicas de tasas.

- BCV: página pública https://www.bcv.org.ve/ (tasa oficial USD y EUR).
- USDT P2P: endpoint público de anuncios P2P de Binance. Es una referencia de
  mercado no oficial; este proyecto no está afiliado a Binance.
"""
from __future__ import annotations

import statistics
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import httpx2 as httpx
from bs4 import BeautifulSoup

BCV_URL = "https://www.bcv.org.ve/"
P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
UA = "tasas-ve-mcp/0.1 (+https://github.com/abixaiprin/tasas-ve-mcp)"


@dataclass(frozen=True)
class Tasa:
    fuente: str          # "bcv" | "p2p"
    moneda: str          # "USD" | "EUR" | "USDT"
    bs: float            # bolívares por 1 unidad de la moneda
    obtenida: str        # ISO 8601 UTC
    detalle: str = ""

    def dict(self) -> dict:
        return asdict(self)


def _ahora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _numero(texto: str) -> float:
    """'36,58740000' -> 36.5874 ; '1.234,56' -> 1234.56"""
    t = texto.strip().replace(" ", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    return float(t)


def parsear_bcv(html: str | bytes) -> list[Tasa]:
    sopa = BeautifulSoup(html, "html.parser")
    ahora = _ahora()
    tasas = []
    for id_, moneda in (("dolar", "USD"), ("euro", "EUR")):
        nodo = sopa.find(id=id_)
        fuerte = nodo.find("strong") if nodo else None
        if not fuerte:
            raise ValueError(f"No se encontró la tasa {moneda} en la página del BCV")
        tasas.append(Tasa("bcv", moneda, _numero(fuerte.get_text()), ahora, "Tasa oficial publicada por el BCV"))
    return tasas


def obtener_bcv(client: httpx.Client | None = None) -> list[Tasa]:
    """Descarga la tasa oficial. Primero intenta con TLS verificado.

    El sitio del BCV ha tenido históricamente una cadena de certificados
    incompleta. Si la verificación falla, se reintenta sin verificar y se
    indica en el detalle, para que quien use el dato lo sepa.
    """
    propio = client is None
    c = client or httpx.Client(timeout=15, headers={"User-Agent": UA}, follow_redirects=True)
    try:
        try:
            r = c.get(BCV_URL)
            nota = ""
        except httpx.ConnectError:
            if not propio:
                raise
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with httpx.Client(timeout=15, headers={"User-Agent": UA}, verify=False, follow_redirects=True) as inseguro:
                    r = inseguro.get(BCV_URL)
            nota = " (certificado TLS del BCV no verificable)"
        r.raise_for_status()
        tasas = parsear_bcv(r.content)
        if nota:
            tasas = [Tasa(t.fuente, t.moneda, t.bs, t.obtenida, t.detalle + nota) for t in tasas]
        return tasas
    finally:
        if propio:
            c.close()


def parsear_p2p(data: dict, lado: str) -> Tasa:
    anuncios = (data or {}).get("data") or []
    precios = [float(a["adv"]["price"]) for a in anuncios if a.get("adv", {}).get("price")]
    if not precios:
        raise ValueError("No hay anuncios P2P disponibles en este momento")
    mediana = round(statistics.median(precios), 4)
    return Tasa("p2p", "USDT", mediana, _ahora(),
                f"Mediana de {len(precios)} anuncios P2P ({'compra' if lado == 'BUY' else 'venta'}). Referencia de mercado, no oficial.")


def obtener_p2p(lado: str = "SELL", anuncios: int = 10, client: httpx.Client | None = None) -> Tasa:
    lado = lado.upper()
    if lado not in ("BUY", "SELL"):
        raise ValueError("lado debe ser BUY o SELL")
    cuerpo = {"asset": "USDT", "fiat": "VES", "merchantCheck": False, "page": 1,
              "rows": max(1, min(anuncios, 20)), "publisherType": None, "tradeType": lado}
    propio = client is None
    c = client or httpx.Client(timeout=15, headers={"User-Agent": UA})
    try:
        r = c.post(P2P_URL, json=cuerpo)
        r.raise_for_status()
        return parsear_p2p(r.json(), lado)
    finally:
        if propio:
            c.close()
