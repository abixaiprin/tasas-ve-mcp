"""Lectura de fuentes públicas de tasas.

- BCV: página pública https://www.bcv.org.ve/ (tasa oficial USD y EUR).
- USDT P2P: endpoint público de anuncios P2P de Binance. Es una referencia de
  mercado no oficial; este proyecto no está afiliado a Binance.
"""
from __future__ import annotations

import re
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


def _descargar(url: str, client: httpx.Client | None) -> tuple[bytes, str]:
    """GET con TLS verificado; si el certificado del BCV falla, reintenta sin verificar y lo indica."""
    propio = client is None
    c = client or httpx.Client(timeout=15, headers={"User-Agent": UA}, follow_redirects=True)
    try:
        try:
            r = c.get(url)
            nota = ""
        except httpx.ConnectError:
            if not propio:
                raise
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with httpx.Client(timeout=15, headers={"User-Agent": UA}, verify=False, follow_redirects=True) as inseguro:
                    r = inseguro.get(url)
            nota = " (certificado TLS del BCV no verificable)"
        r.raise_for_status()
        return r.content, nota
    finally:
        if propio:
            c.close()


def obtener_bcv(client: httpx.Client | None = None) -> list[Tasa]:
    """Tasa oficial publicada por el BCV (USD y EUR)."""
    html, nota = _descargar(BCV_URL, client)
    tasas = parsear_bcv(html)
    if nota:
        tasas = [Tasa(t.fuente, t.moneda, t.bs, t.obtenida, t.detalle + nota) for t in tasas]
    return tasas


# ---------- Tasas informativas del sistema bancario (Bs/USD) ----------
BANCOS_URL = "https://www.bcv.org.ve/tasas-informativas-sistema-bancario"
_FECHA = re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}$")


def _es_numero(t: str) -> bool:
    try:
        _numero(t)
        return True
    except ValueError:
        return False


def parsear_bancos(html: str | bytes) -> list[dict]:
    """Lee la tabla "Tasas Informativas del Sistema Bancario".

    Acepta la tabla de la portada (Banco | Compra | Venta) y la del histórico
    (Fecha | Banco | Compra | Venta). Si hay fechas, devuelve solo la más reciente.
    """
    sopa = BeautifulSoup(html, "html.parser")
    filas: list[dict] = []
    for tabla in sopa.find_all("table"):
        cab = tabla.get_text(" ", strip=True).lower()
        if "banco" not in cab or "compra" not in cab or "venta" not in cab:
            continue
        for tr in tabla.find_all("tr"):
            celdas = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(celdas) == 4 and _FECHA.match(celdas[0]) and _es_numero(celdas[2]) and _es_numero(celdas[3]):
                fecha, banco, compra, venta = celdas
            elif len(celdas) == 3 and _es_numero(celdas[1]) and _es_numero(celdas[2]):
                fecha, (banco, compra, venta) = "", celdas
            else:
                continue
            filas.append({"banco": banco, "compra": _numero(compra), "venta": _numero(venta), "fecha": fecha})
        if filas:
            break
    if not filas:
        raise ValueError("No se encontró la tabla de tasas informativas del sistema bancario")
    fechas = [f["fecha"] for f in filas if f["fecha"]]
    if fechas:
        def clave(f):
            d, m, a = re.split(r"[-/]", f)
            return (int(a), int(m), int(d))
        ultima = max(fechas, key=clave)
        filas = [f for f in filas if f["fecha"] == ultima]
    vistos, unicas = set(), []
    for f in filas:  # sin duplicados por banco
        if f["banco"] not in vistos:
            vistos.add(f["banco"])
            unicas.append(f)
    return unicas


def obtener_bancos(client: httpx.Client | None = None) -> dict:
    """Tasas Bs/USD que reportan los bancos al BCV. Primero la portada; si no está, la página del histórico."""
    ultimo_error: Exception | None = None
    for url in (BCV_URL, BANCOS_URL):
        try:
            html, nota = _descargar(url, client)
            filas = parsear_bancos(html)
            compras = [f["compra"] for f in filas]
            ventas = [f["venta"] for f in filas]
            return {
                "bancos": filas,
                "promedio_compra": round(statistics.mean(compras), 4),
                "promedio_venta": round(statistics.mean(ventas), 4),
                "obtenida": _ahora(),
                "detalle": "Tasas informativas del sistema bancario publicadas por el BCV (Bs por USD)" + nota,
            }
        except Exception as e:  # probar la siguiente fuente
            ultimo_error = e
    raise ValueError(f"No se pudieron leer las tasas bancarias: {ultimo_error}")


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
